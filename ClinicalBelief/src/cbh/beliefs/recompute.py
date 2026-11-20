"""Baseline B1: Recompute classifiers (Ticket T06).

LightGBM/MLP-style predictors that are *recomputed from scratch* on the current
observation mask every turn (they do NOT recurse on their own previous output).
This is the key control against a recursive updater that accumulates/amplifies
its own errors (section 4.3).

Implemented with PyTorch so no extra native deps are needed:
  * `RecomputeLogReg` -- multinomial logistic regression (linear recompute)
  * `RecomputeMLP`    -- 2-hidden-layer MLP

Temperature `T` is calibrated on a held-out subset (never on test).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import torch
import torch.nn as nn

from ..schemas import BeliefState, PublicObservation
from .base import AGE_NORM, BeliefModel, public_features


def features_from_arrays(val: np.ndarray, mask: np.ndarray, age: int, sex: int) -> np.ndarray:
    sex_oh = np.zeros(3, dtype=np.float32)
    sex_oh[min(int(sex), 2)] = 1.0
    return np.concatenate([
        val.astype(np.float32), mask.astype(np.float32),
        np.array([float(age) / AGE_NORM], dtype=np.float32), sex_oh,
    ]).astype(np.float32)


class _TorchRecompute(BeliefModel):
    def __init__(self, diseases: List[str], n_features: int, hidden: int = 256,
                 seed: int = 0, lr: float = 1e-3, epochs: int = 12,
                 batch_size: int = 512, weight_decay: float = 1e-5, arch: str = "mlp"):
        super().__init__(diseases)
        torch.manual_seed(seed)
        self.n_features = n_features
        self.seed = seed
        self.temperature = 1.0
        if arch == "logreg":
            self.net = nn.Linear(n_features, self.K)
        else:
            self.net = nn.Sequential(
                nn.Linear(n_features, hidden), nn.ReLU(), nn.Dropout(0.1),
                nn.Linear(hidden, hidden), nn.ReLU(), nn.Dropout(0.1),
                nn.Linear(hidden, self.K),
            )
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.weight_decay = weight_decay
        self.device = torch.device("cpu")

    def _logits(self, X: np.ndarray) -> np.ndarray:
        self.net.eval()
        with torch.no_grad():
            xt = torch.as_tensor(X, dtype=torch.float32, device=self.device)
            return self.net(xt).cpu().numpy()

    def fit(self, X: np.ndarray, y: np.ndarray, X_val: Optional[np.ndarray] = None,
            y_val: Optional[np.ndarray] = None, verbose: bool = False) -> "_TorchRecompute":
        self.net.train()
        opt = torch.optim.Adam(self.net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        lossf = nn.CrossEntropyLoss()
        Xt = torch.as_tensor(X, dtype=torch.float32)
        yt = torch.as_tensor(y, dtype=torch.long)
        N = len(yt)
        g = torch.Generator().manual_seed(self.seed)
        for ep in range(self.epochs):
            perm = torch.randperm(N, generator=g)
            tot = 0.0
            for i in range(0, N, self.batch_size):
                idx = perm[i:i + self.batch_size]
                opt.zero_grad()
                loss = lossf(self.net(Xt[idx]), yt[idx])
                loss.backward()
                opt.step()
                tot += float(loss.detach()) * len(idx)
            if verbose:
                print(f"  [{self.version}] epoch {ep} loss {tot / N:.4f}")
        if X_val is not None and y_val is not None:
            self.calibrate_temperature(X_val, y_val)
        return self

    def calibrate_temperature(self, X_val: np.ndarray, y_val: np.ndarray) -> float:
        logits = self._logits(X_val)
        best_T, best_nll = 1.0, 1e18
        for T in np.concatenate([np.linspace(0.5, 3.0, 26)]):
            z = logits / T
            z = z - z.max(1, keepdims=True)
            p = np.exp(z)
            p /= p.sum(1, keepdims=True)
            nll = -np.log(np.clip(p[np.arange(len(y_val)), y_val], 1e-12, 1)).mean()
            if nll < best_nll:
                best_nll, best_T = nll, float(T)
        self.temperature = best_T
        return best_T

    def predict_obs(self, observation: PublicObservation) -> np.ndarray:
        x = public_features(observation)[None, :]
        z = self._logits(x)[0] / self.temperature
        z = z - z.max()
        p = np.exp(z)
        return p / p.sum()

    def predict_features(self, X: np.ndarray) -> np.ndarray:
        z = self._logits(X) / self.temperature
        z = z - z.max(1, keepdims=True)
        p = np.exp(z)
        return p / p.sum(1, keepdims=True)

    def reset(self, observation: PublicObservation) -> BeliefState:
        return self._state(self.predict_obs(observation))

    def update(self, prev: BeliefState, observation: PublicObservation) -> BeliefState:
        return self._state(self.predict_obs(observation))

    def save(self, path: str):
        torch.save({"state_dict": self.net.state_dict(), "temperature": self.temperature,
                    "n_features": self.n_features, "diseases": self.diseases,
                    "arch": "logreg" if isinstance(self.net, nn.Linear) else "mlp",
                    "hidden": (self.net[0].out_features if not isinstance(self.net, nn.Linear) else 0),
                    "seed": self.seed}, path)

    @classmethod
    def load(cls, path: str, klass=None):
        ck = torch.load(path, map_location="cpu")
        arch = ck["arch"]
        K = len(ck["diseases"])
        obj = _TorchRecompute(ck["diseases"], ck["n_features"], hidden=ck.get("hidden", 256) or 256,
                              seed=ck.get("seed", 0), arch=arch)
        obj.net.load_state_dict(ck["state_dict"])
        obj.temperature = ck.get("temperature", 1.0)
        obj.version = "logreg_v1" if arch == "logreg" else "mlp_v1"
        return obj


class RecomputeLogReg(_TorchRecompute):
    version = "logreg_v1"

    def __init__(self, diseases, n_features, **kw):
        kw.setdefault("epochs", 20)
        super().__init__(diseases, n_features, arch="logreg", **kw)


class RecomputeMLP(_TorchRecompute):
    version = "mlp_v1"

    def __init__(self, diseases, n_features, **kw):
        super().__init__(diseases, n_features, arch="mlp", **kw)
