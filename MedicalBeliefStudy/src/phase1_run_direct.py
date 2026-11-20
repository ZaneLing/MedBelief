"""Phase 1: actual Qwen3-1.7B frozen forward passes, MLX GPU."""
from pathlib import Path
import argparse, hashlib, importlib.metadata, json, os, platform, re, time
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import numpy as np
import mlx.core as mx
from mlx.utils import tree_map
from mlx_lm import load
from mlx_lm.models.base import create_attention_mask
from mlx_lm.models.cache import make_prompt_cache

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = 'You are analyzing a synthetic patient record for research. Compare the six listed diagnoses using only the cumulative findings shown. Distinguish past medical history from the current presentation. Missing information is unknown.'
STUB = 'Diagnosis code:'
CHECK_CASES = ['ddx_train_0857360', 'ddx_train_0875644', 'ddx_train_0868644']

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def write_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)

def render(row, rotation=0):
    diseases = row['candidate_diseases']
    offset = (row['mapping_offset'] + rotation) % 6
    mapping = {code: diseases[(i + offset) % 6] for i, code in enumerate('ABCDEF')}
    lines = [f"Patient: age {row['age']} years; sex {row['sex']}.", 'Cumulative findings:']
    for i, group in enumerate(row['revealed_groups']):
        lines.append(f'[Evidence group {i}]')
        lines.extend(x['question_en'] + ' Answer: ' + x['answer_en'] + '.' for x in group['items'])
    lines += ['Candidate diagnoses:'] + [f'{code}: {d}' for code, d in mapping.items()]
    lines += ['Select the best-supported candidate for the current presentation at this point. Choose among these six even if the evidence is incomplete. After the prefix "Diagnosis code:", output exactly one space followed by one capital letter A, B, C, D, E, or F. Do not output a numerical probability.']
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': '\n'.join(lines)}], mapping

def output_head(model, h):
    h = model.model.norm(h)
    return model.model.embed_tokens.as_linear(h) if model.args.tie_word_embeddings else model.lm_head(h)

def capture_forward(model, ids):
    cache = make_prompt_cache(model)
    h = model.model.embed_tokens(mx.array([ids]))
    mask = create_attention_mask(h, cache[0])
    states = []
    for block, c in zip(model.model.layers, cache):
        pre = h
        attention = block.self_attn(block.input_layernorm(pre), mask, c)
        mid = pre + attention
        mlp = block.mlp(block.post_attention_layernorm(mid))
        h = mid + mlp
        states.append(mx.stack([a[0, -1] for a in [pre, attention, mid, mlp, h]]))
    stages = mx.stack(states)
    logits = output_head(model, h[:, -1:, :])[0, 0].astype(mx.float32)
    mx.eval(stages, logits)
    arr = np.array(stages)
    assert np.isfinite(arr).all()
    assert np.array_equal((arr[:, 0] + arr[:, 1]).astype(arr.dtype), arr[:, 2])
    assert np.array_equal((arr[:, 2] + arr[:, 3]).astype(arr.dtype), arr[:, 4])
    return stages, logits, cache

def scores(logits, candidate_ids):
    z = logits.astype(mx.float32)
    cz = z[..., mx.array(candidate_ids)]
    # Stable full-vocabulary softmax avoids cancellation in z - logsumexp(z)
    # when one answer has nearly unit probability. Do not clip probabilities.
    cp = mx.softmax(z, axis=-1)[..., mx.array(candidate_ids)]
    q = mx.softmax(cz, axis=-1)
    mx.eval(cz, cp, q)
    cz, cp, q = map(np.array, [cz, cp, q])
    assert np.isfinite(q).all() and np.isfinite(cp).all()
    assert np.allclose(q.sum(-1), 1, atol=1e-6)
    assert np.all(cp >= 0) and np.all(cp.sum(-1) <= 1.000001)
    return cz, cp, q

def greedy_answer(model, tok, first_logits, cache, limit=32):
    ids = []
    logits = first_logits
    eos = set(tok.eos_token_ids)
    for _ in range(limit):
        token = int(mx.argmax(logits).item())
        if token in eos: return ids, tok.decode(ids), 'eos'
        ids.append(token)
        logits = model(mx.array([[token]]), cache=cache)[0, -1].astype(mx.float32)
        mx.eval(logits)
    return ids, tok.decode(ids), 'max_tokens'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-dir', default=str(ROOT.parent / 'MedicalBeliefMechanisms/.models/Qwen3-1.7B'))
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--limit', type=int, default=0, help='Stop after N observations; same manifest allows resume.')
    args = parser.parse_args()
    model_dir = Path(args.model_dir).resolve()
    run = ROOT / 'runs' / args.run_id
    for d in ['observations', 'states', 'prompts']: (run / d).mkdir(parents=True, exist_ok=True)
    rows = [json.loads(s) for s in (ROOT / 'data/pilot_prefixes.public.jsonl').read_text().splitlines()]
    check_points = set()
    for cid in CHECK_CASES:
        last = max(r['round'] for r in rows if r['case_id'] == cid)
        check_points.update((cid, t) for t in [0, last // 2, last])
    jobs = [(r, 0) for r in rows] + [(r, rot) for r in rows if (r['case_id'], r['round']) in check_points for rot in range(1, 6)]
    model_config = json.loads((model_dir / 'config.json').read_text())
    files = list(model_dir.glob('*.safetensors')) + [model_dir / f for f in ['config.json', 'tokenizer.json', 'tokenizer_config.json']]
    hashes = {f.name: sha(f) for f in files}
    manifest = {'run_id': args.run_id, 'model': json.loads((ROOT/'protocol/model_snapshot.json').read_text()),
                'model_config': model_config, 'model_files_sha256': hashes, 'model_dir': str(model_dir),
                'hardware': mx.device_info(), 'device': str(mx.default_device()), 'platform': platform.platform(),
                'packages': {p: importlib.metadata.version(p) for p in ['mlx', 'mlx-lm', 'transformers', 'numpy']},
                'dtype': 'FP16; cast once from original BF16 checkpoint; no quantization or training',
                'mode': 'D; independent cumulative evidence; no previous answers', 'total_jobs': len(jobs),
                'source_sha256': sha(__file__), 'public_input_sha256': sha(ROOT/'data/pilot_prefixes.public.jsonl'),
                'protocol_sha256': sha(ROOT/'protocol/PHASE1.md'), 'api_cost_usd': 0,
                'stage_order': ['r_pre', 'attn_delta', 'r_mid', 'mlp_delta', 'r_post'],
                'readout_stage_order': ['r_pre', 'r_mid', 'r_post'], 'disease_order': rows[0]['candidate_diseases']}
    mp = run / 'manifest.json'
    if mp.exists(): assert json.loads(mp.read_text()) == manifest, 'Configuration changed; choose a new run ID.'
    else:
        write_json(mp, manifest)
        (run/'source_snapshot.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'loading': str(model_dir), 'jobs': len(jobs), 'device': str(mx.default_device())}), flush=True)
    model, tok = load(str(model_dir))
    model.update(tree_map(lambda a: a.astype(mx.float16) if mx.issubdtype(a.dtype, mx.floating) else a, model.parameters()))
    model.eval()
    mx.eval(model.parameters())
    code_ids = {c: tok.encode(' ' + c, add_special_tokens=False) for c in 'ABCDEF'}
    assert all(len(v) == 1 for v in code_ids.values())
    start = time.time()
    completed_now = 0
    for job_index, (row, rotation) in enumerate(jobs):
        oid = f"{row['case_id']}_t{row['round']:02d}_m{rotation}"
        path = run/'observations'/f'{oid}.json'
        if path.exists(): continue
        tick = time.time()
        messages, mapping = render(row, rotation)
        prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False) + STUB
        ids = tok.encode(prompt, add_special_tokens=False)
        for c in 'ABCDEF': assert tok.encode(prompt+' '+c, add_special_tokens=False) == ids + code_ids[c]
        # Reorder everything to the fixed disease order, never to the current letters.
        reverse = {d: c for c, d in mapping.items()}
        candidate_ids = [code_ids[reverse[d]][0] for d in row['candidate_diseases']]
        stages, logits, cache = capture_forward(model, ids)
        z, p, q = scores(logits, candidate_ids)
        layer_scores, layer_probs, layer_support = [], [], []
        # Keep intermediate full-vocabulary matrices transient.
        for si in [0, 2, 4]:
            layer_logits = output_head(model, stages[:, si]).astype(mx.float32)
            lz, lp, lq = scores(layer_logits, candidate_ids)
            layer_scores.append(lz); layer_probs.append(lp); layer_support.append(lq)
        lz, lp, lq = [np.stack(a, axis=1) for a in [layer_scores, layer_probs, layer_support]]
        final_error = float(np.max(np.abs(lz[-1, -1] - z)))
        assert np.allclose(lz[-1, -1], z, atol=1e-3, rtol=1e-3)
        native_check = None
        if rotation == 0 and (row['case_id'], row['round']) in check_points:
            native = model(mx.array([ids]))[0, -1].astype(mx.float32)
            mx.eval(native)
            a, b = np.array(native), np.array(logits)
            native_check = {'max_abs_error': float(np.max(np.abs(a-b))), 'allclose': bool(np.allclose(a,b,atol=1e-3,rtol=1e-3)), 'argmax_same': bool(a.argmax()==b.argmax())}
            assert native_check['allclose'] and native_check['argmax_same'], native_check
        generated_ids, answer, finish = greedy_answer(model, tok, logits, cache)
        letter = answer.strip() if re.fullmatch('[ABCDEF]', answer.strip()) and finish=='eos' else None
        state_path = run/'states'/f'{oid}.npz'
        tmp = state_path.with_suffix('.tmp.npz')
        np.savez_compressed(tmp, residual_stages=np.array(stages), input_ids=np.array(ids, dtype=np.int32),
                            anchor_index=len(ids)-1, terminal_logits=np.array(logits), candidate_ids=candidate_ids,
                            stage_candidate_logits=lz, stage_code_probabilities=lp, stage_candidate_support=lq,
                            stage_candidate_mass=lp.sum(-1))
        tmp.replace(state_path)
        (run/'prompts'/f'{oid}.txt').write_text(prompt)
        record = {'observation_id': oid, 'case_id': row['case_id'], 'round': row['round'], 'rotation': rotation,
                  'new_question_group': row['new_question_group'], 'mode': 'D', 'code_to_disease': mapping,
                  'prompt_tokens': len(ids), 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                  'candidate_logits': z.tolist(), 'code_probabilities': p.tolist(), 'candidate_support': q.tolist(),
                  'candidate_mass': float(p.sum()), 'conditional_top_disease': row['candidate_diseases'][int(q.argmax())],
                  'generated_ids': generated_ids, 'generated_text': answer, 'finish_reason': finish,
                  'generated_disease': mapping.get(letter), 'format_valid': letter is not None,
                  'native_check': native_check, 'last_layer_readout_max_error': final_error,
                  'states_file': str(state_path.relative_to(run)), 'states_sha256': sha(state_path),
                  'elapsed_sec': time.time()-tick, 'status': 'complete'}
        write_json(path, record)
        completed_now += 1
        print(json.dumps({'job': job_index+1, 'total': len(jobs), 'id': oid, 'sec': round(time.time()-tick,2),
                          'top': record['conditional_top_disease'], 'mass': round(record['candidate_mass'],4),
                          'native': native_check}), flush=True)
        del stages, cache, layer_logits
        mx.clear_cache()
        if args.limit and completed_now >= args.limit: break
    completed = len(list((run/'observations').glob('*.json')))
    if completed == len(jobs):
        after = {f.name: sha(f) for f in files}
        assert after == hashes
        write_json(run/'completion.json', {'complete': True, 'observations': completed, 'primary_observations': len(rows),
                   'mapping_control_additional_observations': len(jobs)-len(rows), 'weights_unchanged': True,
                   'elapsed_this_invocation_sec': time.time()-start, 'api_cost_usd': 0})
    print(json.dumps({'completed': completed, 'expected': len(jobs), 'elapsed_sec': time.time()-start}), flush=True)

if __name__ == '__main__': main()
