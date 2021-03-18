from pathlib import Path

from flask import Flask, jsonify, render_template, abort, request

application = Flask(__name__)

data_dir = Path(__file__).parent / 'data'


@application.route('/')
def index():
    return render_template('index.html')


@application.route('/highlight')
def highlight():
    return render_template('highlight.html')


@application.route('/list')
def list():
    ret = []
    for f in (data_dir / 'text').glob('*_en.txt'):
        ret.append(f.name[:-7])
    return jsonify(sorted(ret))


@application.route('/view/<name>')
def view(name):
    return render_template('view.html', name=name)


@application.route('/text/<file>')
def text(file):
    ret = {}
    for lang in ['en', 'pl']:
        with open(str(data_dir / 'text' / f'{file}_{lang}.txt')) as f:
            ret[lang] = []
            for l in f:
                ret[lang].append(l.strip())
    return jsonify(ret)


@application.route('/methods/<file>')
def methods(file):
    ret = []
    for f in (data_dir / 'ali').glob(file + '*'):
        ret.append(f.stem[len(file) + 1:])
    return jsonify(sorted(ret))


@application.route('/ali/<file>/<method>')
def ali(file, method):
    path = data_dir / 'ali' / f'{file}_{method}.txt'
    if not path.exists():
        return abort(404)
    ret = []
    with open(path) as f:
        for l in f:
            r = []
            for p in l.strip().split():
                r.append(p.split('-'))
            ret.append(r)
    return jsonify(ret)


@application.route('/save/<name>', methods=['POST'])
def save(name):
    with open(str(data_dir / 'ali' / f'{name}_Saved.txt'), 'w') as f:
        for s in request.json:
            sl = True
            for p in s:
                if sl:
                    sl = False
                else:
                    f.write(' ')
                f.write(f'{p[0]}-{p[1]}')
            f.write('\n')

    return jsonify(success=True)


if __name__ == '__main__':
    application.run()
