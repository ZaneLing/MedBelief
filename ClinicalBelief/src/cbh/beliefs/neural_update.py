"""Research model B2: Neural Belief Updater (Ticket T07).

    Delta_t = g_phi(d, o_{t+1}, a_{t+1}, H_t)
    b_{t+1} = softmax( log(b_t + eps) + Delta_t )

The updater keeps an explicit running log-belief `l_t` (so `log(b_t)=l_t` up to
a constant) and adds a learned increment each turn. `g_phi` reads:
  * the *newly* revealed atoms this turn (delta mask),
  * a cumulative summary of the observed set (val + mask),
  * age/sex and the current belief `b_t`,
and emits one scalar increment per disease via a trainable disease embedding
matrix `U` (K x d_model). Reading the cumulative observed set is what lets the
model suppress double-counting of correlated evidence (section 4.4).

Numerical stability: log-beliefs are clipped, softmax is float32, eps/clip are
global constants. Trained end-to-end over full trajectories (BPTT) with
teacher-forced prefixes -- note this uses prefix *labels from the case
population*, NOT a claim about any single patient's true intermediate posterior.

We do NOT claim the learned Delta is a clinical log-likelihood; without a
generative constraint it is a disease-specific discriminative evidence
increment.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ..schemas import BeliefState, PublicObservation
from .base import AGE_NORM, BeliefModel

EPS = 1e-6
LOGIT_CLIP = 30.0


class UpdaterNet(nn.Module):
    def __init__(self, n_atoms: int, K: int, d_model: int = 128, hidden: int = 256):
        super().__init__()
        self.n_atoms = n_atoms
        self.K = K
        # input: new_val(n_atoms) + cum_val(n_atoms) + cum_mask(n_atoms) + age(1)+sex(3)+b_t(K)
        in_dim = 3 * n_atoms + 4 + K
        self.enc = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, d_model), nn.ReLU(),
        )
        self.U = nn.Parameter(torch.randn(K, d_model) * 0.01)
        self.b = nn.Parameter(torch.zeros(K))
        # initial log-belief head from the t=0 public state
        init_in = 2 * n_atoms + 4
        self.init_head = nn.Sequential(
            nn.Linear(init_in, hidden), nn.ReLU(),
            nn.Linear(hidden, K),
        )

    def init_logits(self, cum_val, cum_mask, age, sex) -> torch.Tensor:
        sex_oh = F.one_hot(sex.clamp(0, 2), 3).float()
        x = torch.cat([cum_val, cum_mask, (age / AGE_NORM).unsqueeze(1), sex_oh], dim=1)
        return self.init_head(x).clamp(-LOGIT_CLIP, LOGIT_CLIP)

    def delta(self, new_val, cum_val, cum_mask, age, sex, b_t) -> torch.Tensor:
        sex_oh = F.one_hot(sex.clamp(0, 2), 3).float()
        x = torch.cat([new_val, cum_val, cum_mask, (age / AGE_NORM).unsqueeze(1), sex_oh, b_t], dim=1)
        h = self.enc(x)                       # [B, d_model]
        d = h @ self.U.t() + self.b           # [B, K]
        return d.clamp(-LOGIT_CLIP, LOGIT_CLIP)


class BeliefNeuralUpdater(BeliefModel):
    version = "neural_v1"

    def __init__(self, diseases: List[str], n_atoms: int, d_model: int = 128,
                 hidden: int = 256, seed: int = 0, device: str = "cpu"):
        super().__init__(diseases)
        torch.manual_seed(seed)
        self.n_atoms = n_atoms
        self.device = torch.device(device)
        self.net = UpdaterNet(n_atoms, self.K, d_model, hidden).to(self.device)
        self.temperature = 1.0
        self._l: Optional[torch.Tensor] = None
        self._prev_mask: Optional[torch.Tensor] = None
        self._age: Optional[torch.Tensor] = None
        self._sex: Optional[torch.Tensor] = None

    # --- inference (single episode, sequential) -------------------------
    def _prep(self, obs: PublicObservation):
        val = torch.as_tensor(obs.info["atom_val"], dtype=torch.float32, device=self.device).unsqueeze(0)
        mask = torch.as_tensor(obs.info["atom_mask"], dtype=torch.float32, device=self.device).unsqueeze(0)
        age = torch.tensor([float(obs.age or 0)], dtype=torch.float32, device=self.device)
        sex = torch.tensor([int(obs.sex or 0)], dtype=torch.long, device=self.device)
        return val, mask, age, sex

    def reset(self, observation: PublicObservation) -> BeliefState:
        val, mask, age, sex = self._prep(observation)
        self.net.eval()
        with torch.no_grad():
            self._l = self.net.init_logits(val, mask, age, sex)
            self._prev_mask = mask
            self._age, self._sex = age, sex
            b = F.softmax(self._l / self.temperature, dim=1)
        return self._state(b[0].cpu().numpy())

    def update(self, prev: BeliefState, observation: PublicObservation) -> BeliefState:
        val, mask, age, sex = self._prep(observation)
        new_val = val * (mask - self._prev_mask).clamp(min=0)
        self.net.eval()
        with torch.no_grad():
            b_t = F.softmax(self._l, dim=1)
            d = self.net.delta(new_val, val, mask, age, sex, b_t)
            self._l = (torch.log(b_t + EPS) + d).clamp(-LOGIT_CLIP, LOGIT_CLIP)
            self._prev_mask = mask
            b = F.softmax(self._l / self.temperature, dim=1)
        return self._state(b[0].cpu().numpy())

    # --- training over prefixes (BPTT) ---------------------------------
    def fit_prefixes(self, seqs: Sequence[dict], val_seqs: Optional[Sequence[dict]] = None,
                     epochs: int = 8, lr: float = 1e-3, batch_size: int = 64,
                     verbose: bool = False, seed: int = 0) -> "BeliefNeuralUpdater":
        """Each item in `seqs` is a dict with:
             states: list of (val,mask) per turn t=0..T  (np.int8)
             age:int, sex:int, label:int
        The recurrence is unrolled over the whole trajectory and the per-turn
        cross-entropy against the (population) disease label is backpropagated
        end to end.
        """
        self.net.train()
        opt = torch.optim.Adam(self.net.parameters(), lr=lr, weight_decay=1e-6)
        g = torch.Generator().manual_seed(seed)
        n = len(seqs)
        order = np.arange(n)
        import copy
        best_val = float("inf")
        best_state = None
        best_epoch = -1
        for ep in range(epochs):
            perm = torch.randperm(n, generator=g).numpy()
            tot, cnt = 0.0, 0
            for bi in range(0, n, batch_size):
                batch = [seqs[perm[j]] for j in range(bi, min(bi + batch_size, n))]
                loss = self._batch_loss(batch)
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.net.parameters(), 5.0)
                opt.step()
                tot += float(loss.detach()) * len(batch)
                cnt += len(batch)
            if val_seqs is not None:
                v = self.eval_prefix_nll(val_seqs)
                # early stopping: keep the best-validation checkpoint (model
                # selection on validate, never on test)
                if v < best_val:
                    best_val = v
                    best_epoch = ep
                    best_state = copy.deepcopy(self.net.state_dict())
                if verbose:
                    print(f"  [neural] epoch {ep} loss {tot / max(cnt,1):.4f} val {v:.4f}"
                          + (" *" if ep == best_epoch else ""))
                self.net.train()
            elif verbose:
                print(f"  [neural] epoch {ep} loss {tot / max(cnt,1):.4f}")
        if best_state is not None:
            self.net.load_state_dict(best_state)
            if verbose:
                print(f"  [neural] restored best val checkpoint (epoch {best_epoch}, val {best_val:.4f})")
        if val_seqs is not None:
            self.calibrate_temperature(val_seqs)
        return self

    def _batch_loss(self, batch: List[dict]) -> torch.Tensor:
        dev = self.device
        B = len(batch)
        T = max(len(s["states"]) for s in batch)
        losses = []
        # per-sequence unroll (variable length); accumulate CE per turn
        for s in batch:
            states = s["states"]
            age = torch.tensor([float(s["age"])], device=dev)
            sex = torch.tensor([int(s["sex"])], device=dev)
            y = torch.tensor([int(s["label"])], device=dev)
            prev_mask = None
            l = None
            for t, (val_np, mask_np) in enumerate(states):
                val = torch.as_tensor(val_np, dtype=torch.float32, device=dev).unsqueeze(0)
                mask = torch.as_tensor(mask_np, dtype=torch.float32, device=dev).unsqueeze(0)
                if t == 0:
                    l = self.net.init_logits(val, mask, age, sex)
                else:
                    new_val = val * (mask - prev_mask).clamp(min=0)
                    b_t = F.softmax(l, dim=1)
                    d = self.net.delta(new_val, val, mask, age, sex, b_t)
                    l = (torch.log(b_t + EPS) + d).clamp(-LOGIT_CLIP, LOGIT_CLIP)
                prev_mask = mask
                logp = F.log_softmax(l / self.temperature, dim=1)
                losses.append(F.nll_loss(logp, y))
        return torch.stack(losses).mean()

    def eval_prefix_nll(self, seqs: Sequence[dict]) -> float:
        self.net.eval()
        dev = self.device
        tot, cnt = 0.0, 0
        with torch.no_grad():
            for s in seqs:
                age = torch.tensor([float(s["age"])], device=dev)
                sex = torch.tensor([int(s["sex"])], device=dev)
                y = int(s["label"])
                prev_mask = None
                l = None
                for t, (val_np, mask_np) in enumerate(s["states"]):
                    val = torch.as_tensor(val_np, dtype=torch.float32, device=dev).unsqueeze(0)
                    mask = torch.as_tensor(mask_np, dtype=torch.float32, device=dev).unsqueeze(0)
                    if t == 0:
                        l = self.net.init_logits(val, mask, age, sex)
                    else:
                        new_val = val * (mask - prev_mask).clamp(min=0)
                        b_t = F.softmax(l, dim=1)
                        d = self.net.delta(new_val, val, mask, age, sex, b_t)
                        l = (torch.log(b_t + EPS) + d).clamp(-LOGIT_CLIP, LOGIT_CLIP)
                    prev_mask = mask
                    logp = F.log_softmax(l / self.temperature, dim=1)
                    tot += float(-logp[0, y])
                    cnt += 1
        return tot / max(cnt, 1)

    def calibrate_temperature(self, seqs: Sequence[dict]) -> float:
        # collect per-turn logits, grid-search T on validation NLL
        logits_list, labels = self._collect_logits(seqs)
        best_T, best = 1.0, 1e18
        Z = logits_list.numpy()
        yv = np.asarray(labels)
        for T in np.linspace(0.5, 3.0, 26):
            z = Z / T
            z = z - z.max(1, keepdims=True)
            p = np.exp(z)
            p /= p.sum(1, keepdims=True)
            nll = -np.log(np.clip(p[np.arange(len(yv)), yv], 1e-12, 1)).mean()
            if nll < best:
                best, best_T = nll, float(T)
        self.temperature = best_T
        return best_T

    def _collect_logits(self, seqs):
        self.net.eval()
        dev = self.device
        outs, labels = [], []
        with torch.no_grad():
            for s in seqs:
                age = torch.tensor([float(s["age"])], device=dev)
                sex = torch.tensor([int(s["sex"])], device=dev)
                prev_mask = None
                l = None
                for t, (val_np, mask_np) in enumerate(s["states"]):
                    val = torch.as_tensor(val_np, dtype=torch.float32, device=dev).unsqueeze(0)
                    mask = torch.as_tensor(mask_np, dtype=torch.float32, device=dev).unsqueeze(0)
                    if t == 0:
                        l = self.net.init_logits(val, mask, age, sex)
                    else:
                        new_val = val * (mask - prev_mask).clamp(min=0)
                        b_t = F.softmax(l, dim=1)
                        d = self.net.delta(new_val, val, mask, age, sex, b_t)
                        l = (torch.log(b_t + EPS) + d).clamp(-LOGIT_CLIP, LOGIT_CLIP)
                    prev_mask = mask
                    outs.append(l[0].cpu())
                    labels.append(int(s["label"]))
        return torch.stack(outs), labels

    def save(self, path: str):
        torch.save({"state_dict": self.net.state_dict(), "temperature": self.temperature,
                    "n_atoms": self.n_atoms, "diseases": self.diseases,
                    "d_model": self.net.U.shape[1], "hidden": self.net.enc[0].out_features}, path)

    def load(self, path: str):
        ck = torch.load(path, map_location=self.device)
        self.net.load_state_dict(ck["state_dict"])
        self.temperature = ck.get("temperature", 1.0)
        return self
