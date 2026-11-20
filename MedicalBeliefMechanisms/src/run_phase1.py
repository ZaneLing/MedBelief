"""Local inference + decoder-block activation capture, with resumable artifacts.

No training and no paid API. Candidate probabilities are conditional on A/B/C;
their total vocabulary mass and unconstrained token choice are separately saved.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import platform
import time

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]


def span_last_token(offsets, text, substring):
    if not substring:
        return -1
    start = text.index(substring)
    end = start + len(substring)
    matches = [i for i, (a, b) in enumerate(offsets) if a < end and b > start]
    if not matches:
        raise ValueError("Cannot map clinical evidence to tokens")
    return matches[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--device", choices=["mps", "cpu"], default="mps")
    ap.add_argument("--run-id", default="phase1_qwen3_1p7b")
    args = ap.parse_args()
    run = ROOT / "runs" / args.run_id
    states = run / "states"
    states.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(s) for s in (ROOT / "data/phase1_cases.jsonl").read_text().splitlines()]
    if args.limit:
        rows = rows[:args.limit]
    snap = json.loads((ROOT / "protocol/model_snapshot.json").read_text())
    verified = json.loads((ROOT / "protocol/weight_checksums.json").read_text())
    expected = {f['rfilename']: f['lfs']['sha256'] for f in snap['weight_files']}
    assert {f['file']: f['sha256'] for f in verified} == expected, "Weights must be fully verified before inference"
    config = json.loads((ROOT / "protocol/phase1.json").read_text())
    torch.manual_seed(config["seed"])
    np.random.seed(config["seed"])
    torch.set_num_threads(4)
    if args.device == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS is not available; choose CPU explicitly")
    dtype = torch.float16 if args.device == "mps" else torch.float32
    model_path = ROOT / ".models/Qwen3-1.7B"
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True,
        torch_dtype=dtype, attn_implementation="eager").to(args.device).eval()
    blocks = model.model.layers
    candidate_ids = {c: tokenizer.encode(c, add_special_tokens=False) for c in "ABC"}
    assert all(len(v) == 1 for v in candidate_ids.values()), candidate_ids
    candidate_ids = {k: v[0] for k, v in candidate_ids.items()}
    metadata = {"model": snap["id"], "revision": snap["sha"], "device": args.device,
        "dtype": str(dtype), "layers": len(blocks), "hidden_size": model.config.hidden_size,
        "parameters": sum(p.numel() for p in model.parameters()), "seed": config["seed"],
        "thinking": False, "attention": "eager", "sampled_generation": False,
        "activation_location": "output of each decoder block, before final model norm",
        "positions": ["readout_last_token", "evidence_last_token", "latest_source_last_token"],
        "model_config": model.config.to_dict(), "candidate_token_ids": candidate_ids,
        "packages": {p: importlib.metadata.version(p) for p in ["torch", "transformers", "numpy"]},
        "platform": platform.platform(), "data_sha256": hashlib.sha256((ROOT/"data/phase1_cases.jsonl").read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((ROOT/"protocol/phase1.json").read_bytes()).hexdigest(),
        "cost_usd": 0, "billing": "local inference; electricity not metered"}
    (run/"metadata.json").write_text(json.dumps(metadata, indent=2)+"\n")
    cache = {}
    cachepath = run / "unique_predictions.jsonl"
    if cachepath.exists():
        for line in cachepath.read_text().splitlines():
            r = json.loads(line)
            if (states/(r["prompt_sha256"]+".npz")).exists():
                cache[r["prompt_sha256"]] = r
    captured = []
    positions = []

    def capture_hook(_module, _inputs, output):
        h = output[0] if isinstance(output, tuple) else output
        # Keep only the selected tokens, then transfer all layers in one batch.
        # Per-layer CPU transfers would repeatedly synchronize the GPU.
        captured.append(h[0, positions].detach())

    start = time.time()
    instrument_checks = []
    checks_left = 3
    with cachepath.open("a", buffering=1) as fp:
        for j, row in enumerate(rows):
            key = row["prompt_sha256"]
            if key in cache:
                continue
            text = tokenizer.apply_chat_template([{"role": "user", "content": row["prompt"]}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False)
            enc = tokenizer(text, return_tensors="pt", return_offsets_mapping=True, add_special_tokens=False)
            offsets = enc.pop("offset_mapping")[0].tolist()
            inputs = {k: v.to(args.device) for k, v in enc.items()}
            positions = [len(offsets)-1, span_last_token(offsets, text, row["evidence_text"]),
                         span_last_token(offsets, text, row["source_text"])]
            exists = np.array([p >= 0 for p in positions])
            positions = [p if p >= 0 else len(offsets)-1 for p in positions]
            captured.clear()
            handles = [block.register_forward_hook(capture_hook) for block in blocks]
            tick = time.time()
            try:
                with torch.inference_mode():
                    output = model(**inputs, use_cache=False, logits_to_keep=1)
                    logits = output.logits[0, -1].float()
            finally:
                for h in handles:
                    h.remove()
            if args.device == "mps":
                torch.mps.synchronize()
            hidden = torch.stack(captured).to("cpu", dtype=torch.float32).numpy()
            elapsed = time.time()-tick
            assert hidden.shape == (len(blocks), 3, model.config.hidden_size)
            assert np.isfinite(hidden).all()
            if checks_left:
                with torch.inference_mode():
                    plain = model(**inputs, use_cache=False, logits_to_keep=1).logits[0, -1].float()
                error = float(torch.max(torch.abs(plain-logits)))
                assert error < 1e-5, error
                instrument_checks.append({"record_id": row["record_id"], "capture_vs_plain_max_logit_difference": error})
                checks_left -= 1
                (run/"instrument_checks.json").write_text(json.dumps(instrument_checks, indent=2)+"\n")
            lp = torch.log_softmax(logits, dim=-1)
            semantic_lp = {s: float(lp[candidate_ids[t]]) for s, t in row["label_tokens"].items()}
            mass = float(sum(np.exp(list(semantic_lp.values()))))
            probs = {s: float(np.exp(v)/max(mass, 1e-30)) for s, v in semantic_lp.items()}
            winner = max(probs, key=probs.get)
            top_ids = torch.topk(logits, 5).indices.tolist()
            top_text = [tokenizer.decode([i]) for i in top_ids]
            semantic_top = {v:k for k,v in row["label_tokens"].items()}.get(top_text[0].strip())
            np.savez_compressed(states/(key+".npz"), activations=hidden.astype(np.float16),
                position_exists=exists, token_positions=np.array(positions),
                input_ids=enc["input_ids"][0].numpy(), prompt_sha256=key)
            pred = {"prompt_sha256": key, "semantic_probs": probs, "semantic_log_probs": semantic_lp,
                "candidate_mass": mass, "prediction": winner, "unconstrained_top_token_semantic": semantic_top,
                "top_tokens": top_text, "tokens": len(offsets), "seconds": elapsed,
                "activation_file": "states/"+key+".npz", "positions": positions,
                "position_exists": exists.tolist(), "chat_template_sha256": hashlib.sha256(text.encode()).hexdigest()}
            fp.write(json.dumps(pred)+"\n")
            cache[key] = pred
            if len(cache) % 12 == 0:
                print(json.dumps({"unique_done":len(cache), "record_index":j+1, "elapsed_sec":round(time.time()-start,1),
                                  "last_forward_sec":round(elapsed,2)}), flush=True)
    combined = [{**{k:v for k,v in row.items() if k not in ["prompt","evidence_text","source_text"]}, **cache[row["prompt_sha256"]]} for row in rows]
    (run/"predictions.jsonl").write_text("".join(json.dumps(x)+"\n" for x in combined))
    (run/"completion.json").write_text(json.dumps({"complete":True, "records":len(combined),
        "unique_predictions":len(cache), "elapsed_this_invocation_sec":time.time()-start},indent=2)+"\n")
    print("PHASE1_INFERENCE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
