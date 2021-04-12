import argparse
import json
from collections import OrderedDict
from pathlib import Path
from xml.etree.ElementTree import parse

import spacy
from simalign import SentenceAligner
from tqdm import tqdm

myaligner = SentenceAligner(model="bert", token_type="bpe", matching_methods="mai")


def load_ali(file: Path):
    root = parse(file).getroot()
    fromdoc = root.attrib['fromDoc']
    todoc = root.attrib['toDoc']
    links = []
    for link in root:
        lstr = link.attrib['xtargets']
        t = lstr.split(';')
        assert len(t) == 2
        links.append((t[0].split(), t[1].split()))
    return fromdoc, todoc, links


def load_text(file: Path):
    root = parse(file).getroot()
    ret = OrderedDict()
    for sent in root:
        ret[sent.attrib['id']] = sent.text.strip()
    return ret


nlp = {'pl': spacy.load('pl_spacy_model_morfeusz'), 'en': spacy.load('en_core_web_sm')}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('alidir', type=Path)
    parser.add_argument('outfile', type=Path)

    args = parser.parse_args()

    alidir = args.alidir

    ret = []
    for ali in tqdm(list(alidir.glob('*.alignment.xml'))):
    # for ali in tqdm([alidir/'EN0001.en.pl.alignment.xml',alidir/'PL0001.en.pl.alignment.xml']):
        tok = ali.name.split('.')
        assert len(tok) == 5
        name = tok[0]
        # from_lang = tok[1]
        # to_lang = tok[2]
        from_file, to_file, ali_links = load_ali(ali)
        from_doc = load_text(alidir / from_file)
        to_doc = load_text(alidir / to_file)
        from_lang = from_file.split('.')[-2]
        to_lang = to_file.split('.')[-2]

        phrases = []
        for link in ali_links:
            from_txt = []
            for l in link[1]:
                from_txt.append(from_doc[l].strip())
            from_txt = ' '.join(from_txt)
            if len(from_txt) == 0:
                from_txt = '**blank**'

            doc = nlp[from_lang](from_txt)
            from_lemma = []
            n = False
            for token in doc:
                if not n:
                    from_lemma.append(token.lemma_)
                else:
                    from_lemma[-1] = from_lemma[-1] + token.lemma_
                if token.whitespace_:
                    n = False
                else:
                    n = True

            to_txt = []
            for l in link[0]:
                to_txt.append(to_doc[l].strip())
            to_txt = ' '.join(to_txt)
            if len(to_txt) == 0:
                to_txt = '**blank**'

            doc = nlp[to_lang](to_txt)
            to_lemma = []
            n = False
            for token in doc:
                if not n:
                    to_lemma.append(token.lemma_)
                else:
                    to_lemma[-1] = to_lemma[-1] + token.lemma_
                if token.whitespace_:
                    n = False
                else:
                    n = True

            alignment = myaligner.get_word_aligns(from_txt, to_txt)

            phrases.append({
                'words': {
                    from_lang: [{'orig': x[0], 'lemma': x[1], 'corr': None, 'hl': False} for x in
                                zip(from_txt.split(), from_lemma)],
                    to_lang: [{'orig': x[0], 'lemma': x[1], 'corr': None, 'hl': False} for x in
                              zip(to_txt.split(), to_lemma)]
                },
                'alignment': alignment['inter']
            })

        ret.append({
            'name': name,
            'direction': [from_lang, to_lang],
            'phrases': phrases
        })

    with open(args.outfile, 'w') as f:
        json.dump(ret, f, indent=4)
