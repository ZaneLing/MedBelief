"""Development-only actual diagnosis generation for predeclared structures."""
from structure2_core import *
def main():
    assert read(RUN/'calibration/completion.json')['complete']
    for cfg in read(RUN/'structural_candidates.json'):run_cases(cfg,'development',folder='structure_development')
    write(RUN/'structure_development/completion.json',dict(complete=True,configurations=13,cases=80,actual_generations=2080))
if __name__=='__main__':main()
