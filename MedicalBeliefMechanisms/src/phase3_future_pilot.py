"""Phase 3 development pilot: same current answer, different surviving evidence."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def main():
    data=ROOT/'data/phase2c_answer_control.jsonl';inputs=list(map(json.loads,data.read_text().splitlines()));predfile=ROOT/'runs/phase2c_answer_control_4b/predictions.jsonl';actual={r['id']:r for r in map(json.loads,predfile.read_text().splitlines())};assert len(actual)==64
    rows=[]
    corrections=[
      'A later identity audit assigns the entire R2 report to a different patient. R2 must now be excluded. This correction makes no change to R1 or its previously stated status. There is no replacement report or other new evidence.',
      'The reporting service now withdraws all of R2 because it was filed under the wrong patient. None of R2 can support this patient. The information and source status previously given for R1 are unchanged. No replacement evidence has arrived.',
      'Update: R2 has been reallocated to someone else and is unavailable as evidence for the current patient. R1 has not been amended; retain its previous source status. No additional report is available.',
      'A source correction invalidates R2 for this patient: it belongs to another person. This update concerns R2 only, with no change to the previously stated R1 record. There is no replacement or additional evidence.'
    ]
    for r in inputs:
        if not r['backup_available']:continue
        obs=actual[r['id']];assert obs['prediction'] is not None
        tail=obs['generated_text'].rsplit('</think>',1)[-1].strip();future=corrections[r['family_index']-8]+" Apply the same supplied medical rule and the same A/B/C answer options to the evidence justified now. End with 'Final answer: X'."
        rows.append({k:v for k,v in {**r,'id':r['id']+'_after_r2_withdrawal','current_id':r['id'],'current_prediction':obs['prediction'],'current_response':tail,
            'gold':r['current_sign'] if r['target_usable'] else 'unknown','phase':'future_update','rng_key':r['family_id']+':'+r['current_sign']+':future',
            'messages':[{'role':'user','content':r['prompt']},{'role':'assistant','content':tail},{'role':'user','content':future}], 'prompt':future}.items() if k!='record'})
    assert len(rows)==32
    path=ROOT/'data/phase3_future_pilot.jsonl';assert not path.exists();path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    proto={'date':'2026-11-18','role':'Small phase3 development pilot, not completion of the full future-prediction stage','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'data_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'prior_predictions_sha256':hashlib.sha256(predfile.read_bytes()).hexdigest(),
        'future_outputs_seen':False,'records':32,'families':8,'current_records':'The 32 phase2C backup-present records; actual current answers are retained, no desired initial response substituted.',
        'manipulation':'Same current semantic answer within each family/sign pair; withdraw only R2, without restating whether R1 is usable. Expected answer stays if R1 is usable and becomes insufficient otherwise.',
        'forecast_target':'Whether the actual future model answer changes from its actual current semantic answer; separately report future correctness and type of change.',
        'predictor_inputs':'Only pre-current-generation phase2C state, visible current input, and actual current semantic answer; future prompt/response never included as predictor features.',
        'split':'Train on family indices 8,9 (4 numerical families,16 trajectories); test 10,11 (4 other families,16 trajectories). Entire trajectories stay together.',
        'comparisons':['current answer + domain only','current visible text + actual current answer, word/character TFIDF with C selected only inside training families','hidden state + current answer + domain, fixed C=1, all layers; layers36 primary and26 secondary selected previously from2B'],
        'limits':'Current-answer confidence/log-probabilities not controlled; small numerical-family split, not broad template independence. No causal intervention. A predictive advantage, if any, is pilot evidence only; no advantage is reported honestly.',
        'sampling':{'seed':20261118,'max_tokens':2048,'batch_size':16,'paired_random_streams':True},'capture':False,'api_cost_usd':0,'clinical_review_required':False}
    p=ROOT/'protocol/phase3_future_pilot.json';assert not p.exists();p.write_text(json.dumps(proto,indent=2)+'\n');print(json.dumps(proto,indent=2))
if __name__=='__main__':main()
