"""Compare a migrated prototype replay against the preserved confirmation record."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('file',type=Path);a=ap.parse_args();z=json.loads(a.file.read_text());cfg=z['configuration'];folder='output_matched_control' if cfg['name']=='baseline_constrained' else 'confirmation';p=ROOT/'MedicalBeliefStudy/runs/structural_v2'/folder/cfg['name']/(z['case_id']+'.json');ref=json.loads(p.read_text());r=next(x for x in ref['conditions'] if x['condition']==z['condition']);bad=[k for k in ['text','generated_disease','tokens','stop','prompt_sha256'] if z[k]!=r[k]]
 if z['parameter_stats']!=ref['parameter_stats']:bad.append('parameter_stats')
 print(json.dumps(dict(matches_frozen_confirmation=not bad,case_id=z['case_id'],condition=z['condition'],mismatched_fields=bad),ensure_ascii=False));raise SystemExit(bool(bad))
if __name__=='__main__':main()
