from pathlib import Path

tmp_file = Path('/tmp/t')
for f in Path('../data/ali').glob('PL*SymGiza++.txt'):
    with open(str(f)) as fp, open(str(tmp_file), 'w') as tp:
        for l in fp:
            ret = []
            for p in l.strip().split():
                tok = p.split('-')
                ret.append(f'{tok[1]}-{tok[0]}')
            tp.write(' '.join(ret))
            tp.write('\n')
    tmp_file.rename(f)
