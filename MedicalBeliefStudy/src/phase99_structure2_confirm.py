"""One frozen independent confirmation matrix, no adaptive followups."""
from structure2_compat import *
def main():
    verify_amendment()
    write(RUN/'confirmation/execution_amendment.json',read(DOC/'TOKENIZATION_AMENDMENT.json'))
    spec=read(RUN/'confirmation_selection.json');assert spec['core_sha256']==sha(ROOT/'src/structure2_core.py') and spec['decoder_sha256']==sha(ROOT/'src/structure2_decode.py') and spec['ranking_sha256']==sha(RUN/'calibration/ranking.json')
    for cfg in spec['configurations']:run_config(cfg,'confirmation')
    run_config(dict(name='baseline_no_history'),'confirmation',conditions=('none',))
    write(RUN/'confirmation/completion.json',dict(complete=True,cases=400,configurations=len(spec['configurations']),actual_generations=400*(2*len(spec['configurations'])+1),selection_sha256=sha(RUN/'confirmation_selection.json'),api_cost_usd=0))
if __name__=='__main__':main()
