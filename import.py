import argparse
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('list', type=Path)
    parser.add_argument('txtdir', type=Path)
    parser.add_argument('alifile', type=Path)
    parser.add_argument('name', type=str)
    parser.add_argument('datadir', type=Path)
    parser.add_argument('--from', '-f', default='en')
    parser.add_argument('--to', '-t', default='pl')

    args = parser.parse_args()

    with open(args.list) as f:
        list = f.read().splitlines()

    ln = {}
    for file in list:
        with open(str(args.txtdir / f'{file}_en.txt')) as f:
            ln[file] = len(f.readlines())

    with open(args.alifile) as f:
        for file in list:
            with open(str(args.datadir / 'ali' / f'{file}_{args.name}.txt'), 'w') as g:
                for l in range(ln[file]):
                    g.write(f.readline())
