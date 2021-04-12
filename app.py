import json
import os
from pathlib import Path
from typing import List

from flask import Flask, jsonify, render_template, abort, request
from flask_pymongo import PyMongo

application = Flask(__name__)

application.config[
    'MONGO_URI'] = f'mongodb://{os.getenv("DB_HOST", "localhost")}:{os.getenv("DB_PORT", "27017")}/wordalign'

mongo = PyMongo(application)

data_dir = Path(__file__).parent / 'data'


@application.route('/')
def index():
    list = [x['name'] for x in mongo.db.files.find({}, {'name': 1, '_id': 0})]
    return render_template('index.html', list=sorted(list))


@application.route('/highlight', methods=['GET', 'POST'])
def highlight():
    texts = []
    pl_wl = ''
    en_wl = ''

    wl = mongo.db.settings.find_one({'name': 'wordlists'})
    if wl:
        en_wl = wl['en']
        pl_wl = wl['pl']

    if request.method == 'POST':
        en_wl = request.form['wordlist_en']
        pl_wl = request.form['wordlist_pl']

        mongo.db.settings.update_one({'name': 'wordlists'}, {'$set': {'en': en_wl, 'pl': pl_wl}}, upsert=True)

        en_words = set()
        for w in en_wl.splitlines():
            en_words.add(w.strip().lower())

        pl_words = set()
        for w in pl_wl.splitlines():
            pl_words.add(w.strip().lower())

        texts = []

        for lang, wordlist in [('en', en_words), ('pl', pl_words)]:
            for file in mongo.db.files.find({}):
                for utt in file['phrases']:
                    for word in utt['words'][lang]:
                        word['hl'] = False
                        for wl in wordlist:
                            if wl in word['lemma'].lower():
                                word['hl'] = True
                                break
                    tt = []
                    for word in utt['words'][lang]:
                        tt.append([word['orig'], word['hl']])
                    texts.append(tt)
                mongo.db.files.replace_one({'_id': file['_id']}, file)

    return render_template('highlight.html', wordlist_en=en_wl, wordlist_pl=pl_wl, texts=texts)


@application.route('/view/<name>')
def view(name):
    dbfile = mongo.db.files.find_one({'name': name})
    if not dbfile:
        abort(404)
    alignments = [x['alignment'] for x in dbfile['phrases']]
    return render_template('view.html', file=dbfile, alignments=alignments)


@application.route('/save/<name>/<int:sent>', methods=['POST'])
def save(name, sent):
    ali = json.loads(request.form['ali'])

    mongo.db.files.update_one({'name': name}, {'$set': {f'phrases.{sent}.saved': ali}})

    return jsonify(success=True)


@application.route('/unsave/<name>/<int:sent>', methods=['POST'])
def unsave(name, sent):
    mongo.db.files.update_one({'name': name}, {'$set': {f'phrases.{sent}.saved': None}})

    return jsonify(success=True)


@application.route('/edit/<name>/<lang>/<int:sent>/<int:word>', methods=['POST'])
def edit(name, lang, sent, word):
    txt = request.form['word']
    if len(txt)==0:
        txt=None

    mongo.db.files.update_one({'name': name}, {'$set': {f'phrases.{sent}.words.{lang}.{word}.corr': txt}})

    return jsonify(success=True)


if __name__ == '__main__':
    application.run()
