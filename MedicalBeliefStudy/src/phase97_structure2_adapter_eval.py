"""Complete development generation for trained adapters and a depth bridge."""
from structure2_decode import *
def main():
    cfgs=read(RUN/'trained_adapters.json')+[read(RUN/'bridge/completion.json')['configuration']]+grammar_configs()
    write(RUN/'added_candidates.json',cfgs)
    for cfg in cfgs:run_config(cfg,'development',folder='adapter_development')
    write(RUN/'adapter_development/completion.json',dict(complete=True,configurations=len(cfgs),cases=80,actual_generations=80*2*len(cfgs)))
if __name__=='__main__':main()
