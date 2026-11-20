"""Preserve frozen prompts; repair BPE merges across a forced JSON prefix.

The old renderer assumes tokenizing prompt+answer retains the exact prompt
tokens. A leading apostrophe in one source candidate violates that assumption.
Only that invalid assumption is repaired: prompt IDs and safe suffix IDs remain
identical; exceptional suffixes are tokenized as a continuation after the fixed
prompt IDs. No candidate text, diagnosis label, or selected method is changed.
"""
import structure2_core as core
from structure2_decode import *

_original_render=core.render

class PrefixSafeTokenizer:
    def __init__(self,tok):self.tok=tok;self.prompt=None;self.ids=None;self.repairs=[]
    def __getattr__(self,name):return getattr(self.tok,name)
    def _tokenizer(self,text,**kwargs):
        result=self.tok._tokenizer(text,**kwargs)
        if kwargs.get('return_offsets_mapping'):self.prompt=text;self.ids=result['input_ids']
        return result
    def encode(self,text,**kwargs):
        full=self.tok.encode(text,**kwargs)
        if self.prompt is not None and text.startswith(self.prompt) and full[:len(self.ids)]!=self.ids:
            tail=text[len(self.prompt):];suffix=self.tok.encode(tail,**kwargs);assert self.tok.decode(suffix)==tail;self.repairs.append(tail);return self.ids+suffix
        return full

def prefix_safe_render(c,row,tok):
    wrapped=PrefixSafeTokenizer(tok);e=_original_render(c,row,wrapped);e['suffix_boundary_repairs']=wrapped.repairs;return e

core.render=prefix_safe_render

def verify_amendment():
    z=read(DOC/'TOKENIZATION_AMENDMENT.json');assert z['compat_sha256']==sha(ROOT/'src/structure2_compat.py');assert z['selection_sha256']==sha(RUN/'confirmation_selection.json');assert z['original_renderer_sha256']==sha(ROOT/'src/belief_v4_core.py')
