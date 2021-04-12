import argparse
from pathlib import Path

import spacy
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('input', type=Path)
parser.add_argument('output', type=Path)

args = parser.parse_args()

nlp_pl = spacy.load('pl_spacy_model_morfeusz')
nlp_en = spacy.load('en_core_web_sm')

for inp in tqdm(list(args.input.glob('*.txt'))):
    out = args.output / inp.name
    if inp.stem[:-1] == 'en':
        nlp = nlp_en
    else:
        nlp = nlp_pl
    with open(inp) as f, open(out, 'w') as g:
        for l in f:
            doc = nlp(l.strip())
            ret = []
            n = False
            for w in doc:
                if not n:
                    ret.append(w.lemma_)
                else:
                    ret[-1] = ret[-1] + w.lemma_
                if w.whitespace_:
                    n = False
                else:
                    n = True
            assert len(ret) == len(l.strip().split())
            g.write(' '.join(ret))
            g.write('\n')
