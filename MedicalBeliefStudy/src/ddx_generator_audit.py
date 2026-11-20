"""Training-free audit of published DDXPlus generator support.

This is a simulator-specific support rule, not a clinical exclusion rule.
Exploration: official test. Frozen replication: official validation, with overlap audits.
"""
import ast
import collections
import csv
import functools
import hashlib
import itertools
import json
import time
from pathlib import Path

import numpy as np

from ddx_classifier_expansion import DATA, DISEASES, META, RAW, ROOT, dump, sha, wilson

OUT = ROOT/'results/23_ddx_generator_audit'
COND = json.loads((RAW/'release_conditions.json').read_text())
ALLOW = {v['condition_name']: set(v['symptoms']) | set(v['antecedents']) for v in COND.values()}
ALL = (1 << len(DISEASES)) - 1
DMAP = {d:i for i,d in enumerate(DISEASES)}
SUPPORT = {k:sum(1<<i for i,d in enumerate(DISEASES) if k in ALLOW[d]) for k in META}
MODES = ['all','binary_only','symptoms_only','history_only','without_literal_disease_names']
MASKED = set(json.loads((ROOT/'results/22_ddx_classifier_expansion/literal_name_ablation.json').read_text()))


def compatible(keys):
    bits = ALL
    for k in keys:
        bits &= SUPPORT[k]
    return bits


def labels(bits):
    return [d for i,d in enumerate(DISEASES) if bits & (1<<i)]


def signature(tokens):
    return hashlib.sha256('\n'.join(sorted(set(tokens))).encode()).digest()


@functools.lru_cache(maxsize=None)
def certificate(keys):
    target = compatible(keys)
    if target.bit_count() != 1:
        return None
    # Remove redundant supersets of another evidence's allowed disease set.
    representatives = {}
    for k in keys:
        representatives.setdefault(SUPPORT[k], k)
    masks = [(m,k) for m,k in representatives.items()
             if not any(other != m and (other & m) == other for other in representatives)]
    masks.sort(key=lambda x:(x[0].bit_count(), x[1]))
    for n in [1,2,3]:
        for combo in itertools.combinations(masks,n):
            bits = ALL
            for m,_ in combo:
                bits &= m
            if bits == target:
                witness = [k for _,k in combo]
                assert compatible(witness)==target
                return dict(exact_minimum=n, witness=witness, upper_bound=n)
    # Above three, only claim a greedy upper bound, not an exact minimum.
    chosen=[]
    remaining=list(masks)
    bits=ALL
    while bits!=target:
        m,k=min(remaining,key=lambda x:((bits & x[0]).bit_count(),x[1]))
        bits &= m
        chosen.append(k)
        remaining.remove((m,k))
    return dict(exact_minimum=None, witness=chosen, upper_bound=len(chosen))


def parse(row):
    tokens=ast.literal_eval(row['EVIDENCES'])
    keys=tuple(sorted({t.partition('_@_')[0] for t in tokens}))
    assert set(keys)<=META.keys()
    return tokens,keys


def subsetkeys(keys, mode):
    if mode=='binary_only':return [k for k in keys if META[k]['data_type']=='B']
    if mode=='symptoms_only':return [k for k in keys if not META[k]['is_antecedent']]
    if mode=='history_only':return [k for k in keys if META[k]['is_antecedent']]
    if mode=='without_literal_disease_names':return [k for k in keys if k not in MASKED]
    return keys


def describe(values):
    a=np.asarray(values,dtype=float)
    return dict(n=len(a),mean=float(a.mean()),median=float(np.median(a)),p05=float(np.quantile(a,.05)),p95=float(np.quantile(a,.95)))


def split_audit(split, excluded_facts, prior_ids):
    counter=collections.Counter()
    modes={m:collections.Counter() for m in MODES}
    cert=collections.Counter()
    perclass=collections.defaultdict(collections.Counter)
    cand_hist=collections.Counter()
    masses=[]; unique_masses=[]; gold_probs=[]; unique_probs=[]
    rows=[]; examples=[];facts=set();new_inventories=collections.Counter()
    rng=np.random.default_rng(20261119)
    binary=sorted(k for k in META if META[k]['data_type']=='B')
    with (RAW/f'{split}.csv').open() as f:
        for i,row in enumerate(csv.DictReader(f)):
            tokens,keys=parse(row)
            cid=f'ddx_{split}_{i:07d}'
            d=row['PATHOLOGY'];gold=1<<DMAP[d]
            bits=compatible(keys);n=bits.bit_count();contains=bool(bits&gold)
            unique=n==1
            sig=signature(tokens);facts.add(sig)
            counter['cases']+=1;counter['true_compatible']+=contains
            counter['unique']+=unique;counter['unique_correct']+=unique and contains
            cand_hist[n]+=1
            pc=perclass[d];pc['n']+=1;pc['unique']+=unique;pc['unique_correct']+=unique and contains
            unseen=sig not in excluded_facts
            counter['fresh_fact_n']+=unseen;counter['fresh_fact_unique']+=unseen and unique
            counter['fresh_fact_unique_correct']+=unseen and unique and contains
            counter['prior_case_n']+=cid in prior_ids
            counter['new_case_n']+=cid not in prior_ids
            counter['new_case_unique']+=(cid not in prior_ids) and unique
            for mode in MODES:
                b=compatible(subsetkeys(keys,mode))
                modes[mode]['unique']+=b.bit_count()==1
                modes[mode]['unique_correct']+=(b.bit_count()==1) and bool(b&gold)
                modes[mode]['true_compatible']+=bool(b&gold)
            c=certificate(keys)
            cert[str(c['exact_minimum']) if c else 'ambiguous']+=1
            if c and c['exact_minimum'] is not None:
                counter['at_most_3']+=1
            ref=dict(ast.literal_eval(row['DIFFERENTIAL_DIAGNOSIS']))
            assert set(ref)<=set(DISEASES) and abs(sum(ref.values())-1)<1e-6
            top=max(ref,key=ref.get)
            good={rd:p for rd,p in ref.items() if bits & (1<<DMAP[rd])}
            assert good, 'Underlying disease should be in both support and differential'
            projected=max(good,key=good.get)
            mass=sum(p for rd,p in ref.items() if not(bits & (1<<DMAP[rd])))
            masses.append(mass);gold_probs.append(ref.get(d,0))
            counter['reference_top_correct']+=top==d
            counter['projected_top_correct']+=projected==d
            counter['reference_top_incompatible']+=not bool(bits & (1<<DMAP[top]))
            counter['reference_has_incompatible_candidate']+=mass>1e-12
            if unique:
                unique_masses.append(mass);unique_probs.append(ref[d])
                counter['unique_reference_top_correct']+=top==d
            # Deliberately artificial support violation stress, not clinically validated label preservation.
            added=binary[int(rng.integers(len(binary)))]
            while added in keys:
                added=binary[int(rng.integers(len(binary)))]
            noisybits=bits & SUPPORT[added]
            counter['one_added_binary_retains_true']+=bool(noisybits&gold)
            counter['one_added_binary_empty']+=noisybits==0
            certkeys=c['witness'] if c else []
            rows.append(dict(case_id=cid,gold=d,candidates=';'.join(labels(bits)),candidate_count=n,
                unique_correct=int(unique and contains),minimum_certificate_le3=c['exact_minimum'] if c else '',
                certificate=';'.join(certkeys),reference_top=top,reference_true_probability=ref[d],
                reference_outside_support_mass=mass,projected_reference_top=projected,
                novel_fact=int(unseen),previously_analyzed_id=int(cid in prior_ids)))
            if split=='test' and unique and c['exact_minimum'] in [1,2,3] and top!=d and len(examples)<80:
                examples.append(dict(case_id=cid,gold=d,keys=list(keys),tokens=tokens,
                    certificate=c,certificate_questions=[META[k]['question_en'] for k in certkeys],
                    disease_sets_per_certificate={k:labels(SUPPORT[k]) for k in certkeys},
                    reference_differential=ref,reference_outside_support_mass=mass))
    n=counter['cases']
    result=dict(counts=dict(counter),unique_coverage=counter['unique']/n,
                coverage_wilson95=wilson(counter['unique'],n),
                selective_accuracy=counter['unique_correct']/counter['unique'],
                selective_accuracy_wilson95=wilson(counter['unique_correct'],counter['unique']),
                at_most_three_coverage=counter['at_most_3']/n,
                fresh_fact_coverage=counter['fresh_fact_unique']/counter['fresh_fact_n'],
                certificate_count_histogram=dict(cert),candidate_count_histogram=dict(cand_hist),
                ablations={m:dict(**v,coverage=v['unique']/n,selective_accuracy=v['unique_correct']/v['unique'] if v['unique'] else None) for m,v in modes.items()},
                reference_outside_support_mass=describe(masses),unique_reference_outside_support_mass=describe(unique_masses),
                reference_true_probability=describe(gold_probs),unique_reference_true_probability=describe(unique_probs),
                reference_top_accuracy=counter['reference_top_correct']/n,
                reference_projected_top_accuracy=counter['projected_top_correct']/n,
                per_disease={d:dict(**v,coverage=v['unique']/v['n']) for d,v in perclass.items()})
    dump(OUT/f'{split}_summary.json',result)
    with (OUT/f'{split}_cases.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    if examples:dump(OUT/'support_certificate_examples.json',examples)
    print(split, json.dumps({k:result[k] for k in ['counts','unique_coverage','selective_accuracy','at_most_three_coverage','fresh_fact_coverage','reference_outside_support_mass','reference_top_accuracy','reference_projected_top_accuracy']}),flush=True)
    return result,facts


def main():
    started=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
    trainfacts={signature(c['tokens']) for c in map(json.loads,(DATA/'train_cases.jsonl').read_text().splitlines())}
    prior=set()
    for cohort in ['full49_v1','belief_v2']:
        prior.update(c['case_id'] for c in map(json.loads,(ROOT/f'data/{cohort}/cases.private.jsonl').read_text().splitlines()))
    test,testfacts=split_audit('test',trainfacts,prior)
    validation,_=split_audit('validate',trainfacts|testfacts,prior)
    print('Auditing all official training records for support violations...',flush=True)
    train=collections.Counter()
    violations=[]
    with (RAW/'train.csv').open() as f:
        for i,row in enumerate(csv.DictReader(f)):
            _,keys=parse(row)
            bits=compatible(keys)
            true=bool(bits & (1<<DMAP[row['PATHOLOGY']]))
            train['n']+=1;train['true_compatible']+=true
            train['unique']+=bits.bit_count()==1
            if not true:violations.append(dict(row=i,gold=row['PATHOLOGY'],keys=list(keys)))
    dump(OUT/'training_support_violations.json',violations)
    result=dict(test=test,validation=validation,training_support_audit=dict(train),
        method='Candidate support intersection; no patient training; abstain on non-singleton set.',
        patient_training_cases_used=0,known_disease_evidence_relations=sum(len(s) for s in ALLOW.values()),
        reference_probability_caveat='Normalized rule-based scores; not established as the posterior of the synthetic generator.',
        elapsed_seconds=time.perf_counter()-started,
        hashes={str(p.relative_to(ROOT.parent)):sha(p) for p in [RAW/'train.csv',RAW/'test.csv',RAW/'validate.csv',RAW/'release_conditions.json',RAW/'release_evidences.json',Path(__file__),ROOT/'protocol/DDX_GENERATOR_AUDIT.json']})
    dump(OUT/'summary.json',result)
    dump(OUT/'codebook.json',dict(diseases=DISEASES,allowed_evidence={d:sorted(ks) for d,ks in ALLOW.items()},
                                 support_by_evidence={k:labels(m) for k,m in SUPPORT.items()}))
    print('COMPLETE',OUT,'seconds',result['elapsed_seconds'],flush=True)


if __name__=='__main__':main()
