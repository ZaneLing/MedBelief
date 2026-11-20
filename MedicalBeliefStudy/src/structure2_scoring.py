"""Transparent surface-form sensitivity, never using the gold answer to parse.

Normalize case, Unicode width, punctuation, whitespace and leading articles.
Require a unique exact normalized match to one of ALL FOUR candidates. No
synonym model, fuzzy matching, or disease-specific correction is used.
"""
import re,unicodedata

def normalize_name(s):
    s=unicodedata.normalize('NFKC',s).casefold().strip();s=re.sub(r'^(?:a|an|the)\s+','',s)
    # Preserve medically meaningful signs/operators; only surface separators
    # and quotation/JSON punctuation disappear.
    return ''.join(ch for ch in s if ch.isalnum() or ch in '+-−/<>=%')

def surface_choice(c,r):
    value=r['generated_disease']
    if not isinstance(value,str):value=r['text'].split('}',1)[0]
    key=normalize_name(value);hits=[i for i,s in enumerate(c['candidates']) if normalize_name(s)==key]
    return hits[0] if len(hits)==1 else None
