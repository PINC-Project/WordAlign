import json
import os
import re
from copy import deepcopy
from pathlib import Path

import xlsxwriter as xlsxwriter
from flask import Flask, jsonify, render_template, abort, request, send_file, redirect
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
    if len(txt) == 0:
        txt = None

    mongo.db.files.update_one({'name': name}, {'$set': {f'phrases.{sent}.words.{lang}.{word}.corr': txt}})

    return jsonify(success=True)


@application.route('/merge/<name>')
def merge(name):
    a = int(request.args.get('a')) - 1
    b = int(request.args.get('b')) - 1
    dbfile = mongo.db.files.find_one({'name': name})
    if not dbfile:
        abort(404)

    from_lang = dbfile['direction'][0]
    to_lang = dbfile['direction'][1]

    newphrase = dbfile['phrases'][a]
    oldphrase = dbfile['phrases'].pop(b)

    offset_x = len(newphrase['words'][from_lang])
    offset_y = len(newphrase['words'][to_lang])

    newphrase['words']['en'].extend(oldphrase['words']['en'])
    newphrase['words']['pl'].extend(oldphrase['words']['pl'])
    newphrase['alignment'].extend([[x[0] + offset_x, x[1] + offset_y] for x in oldphrase['alignment']])
    dbfile['phrases'][a] = newphrase

    mongo.db.files.replace_one({'name': name}, dbfile)

    return redirect(f'/view/{name}')


@application.route('/split/<name>')
def split(name):
    phrase = int(request.args.get('phrase')) - 1
    word_from = int(request.args.get('word_from'))
    word_to = int(request.args.get('word_to'))
    dbfile = mongo.db.files.find_one({'name': name})
    if not dbfile:
        abort(404)

    from_lang = dbfile['direction'][0]
    to_lang = dbfile['direction'][1]

    phrase_a = dbfile['phrases'][phrase]
    phrase_b = deepcopy(phrase_a)

    phrase_a['words'][from_lang] = phrase_a['words'][from_lang][:word_from]
    phrase_a['words'][to_lang] = phrase_a['words'][to_lang][:word_to]
    phrase_b['words'][from_lang] = phrase_b['words'][from_lang][word_from:]
    phrase_b['words'][to_lang] = phrase_b['words'][to_lang][word_to:]

    newali = []
    for ali_el in phrase_a['alignment']:
        if ali_el[0] < word_from and ali_el[1] < word_to:
            newali.append(ali_el)
    phrase_a['alignment'] = newali

    newali = []
    len_x = len(phrase_b['words'][from_lang])
    len_y = len(phrase_b['words'][to_lang])
    for ali_el in phrase_b['alignment']:
        x = ali_el[0] - word_from
        y = ali_el[0] - word_to
        if 0 <= x < len_x and 0 <= y < len_y:
            newali.append([x, y])
    phrase_b['alignment'] = newali

    dbfile['phrases'][phrase] = phrase_a
    dbfile['phrases'].insert(phrase + 1, phrase_b)

    mongo.db.files.replace_one({'name': name}, dbfile)

    return redirect(f'/view/{name}')


@application.route('/export')
def export():
    times = None
    if Path('times.json').exists():
        with open('times.json') as f:
            times = json.load(f)

    wb = xlsxwriter.Workbook('/tmp/export.xlsx')
    fmt_head = wb.add_format()
    fmt_head.set_bold()
    fmt_head.set_align('center')
    sheet = wb.add_worksheet()
    sheet.write(0, 0, 'File name', fmt_head)
    sheet.write(0, 1, 'Sent num', fmt_head)
    sheet.write(0, 2, 'ST', fmt_head)
    sheet.write(0, 3, 'TT', fmt_head)
    sheet.write(0, 4, 'ST word num', fmt_head)
    sheet.write(0, 5, 'ST word', fmt_head)
    sheet.write(0, 6, 'ST status', fmt_head)
    sheet.write(0, 7, 'ST onset', fmt_head)
    sheet.write(0, 8, 'ST offset', fmt_head)
    sheet.write(0, 9, 'TT word num', fmt_head)
    sheet.write(0, 10, 'TT word ', fmt_head)
    sheet.write(0, 11, 'TT status', fmt_head)
    sheet.write(0, 12, 'TT onset', fmt_head)
    sheet.write(0, 13, 'TT offset', fmt_head)

    rn = 1
    for file in sorted(mongo.db.files.find({}), key=lambda x: x['name']):
        src = file['direction'][0]
        dest = file['direction'][1]

        src_time = times[file['name'] + '_' + src]
        dest_time = times[file['name'] + '_' + dest]

        src_time_pos = -1
        dest_time_pos = -1

        for sent_num, sent in enumerate(file['phrases']):
            src_sent = ' '.join([x['orig'] for x in sent['words'][src]])
            dest_sent = ' '.join([x['orig'] for x in sent['words'][dest]])

            dest_time_cache = {}
            for word_num, word in enumerate(sent['words'][dest]):
                cmp_text = re.sub(r'\W', '', word['orig'].lower())
                for x in range(dest_time_pos + 1, len(dest_time)):
                    if re.sub(r'\W', '', dest_time[x]['t'].lower()) == cmp_text:
                        dest_time_pos = x
                        dest_time_cache[word_num] = dest_time_pos
                        break

            for word_num, word in enumerate(sent['words'][src]):

                cmp_text = re.sub(r'\W', '', word['orig'].lower())
                for x in range(src_time_pos + 1, len(src_time)):
                    if re.sub(r'\W', '', src_time[x]['t'].lower()) == cmp_text:
                        src_time_pos = x
                        break

                if word['hl']:
                    to = []

                    if 'saved' in sent and sent['saved']:
                        ali = sent['saved']
                    else:
                        ali = sent['alignment']

                    dest_len = len(sent['words'][dest])
                    for f in ali:
                        if f[0] == word_num and f[1] < dest_len:
                            to.append(f[1])

                    if len(to) == 0:
                        sheet.write(rn, 0, file['name'])
                        sheet.write(rn, 1, sent_num + 1)
                        sheet.write(rn, 2, src_sent)
                        sheet.write(rn, 3, dest_sent)
                        sheet.write(rn, 4, word_num + 1)
                        sheet.write(rn, 5, word['orig'])
                        sheet.write(rn, 6, word['corr'])
                        sheet.write(rn, 7, src_time[src_time_pos]['s'])
                        sheet.write(rn, 8, src_time[src_time_pos]['s'] + src_time[src_time_pos]['d'])
                        rn += 1
                    else:

                        sheet.write(rn, 5, word['orig'])
                        sheet.write(rn, 6, word['corr'])

                        for t in to:
                            dest_word = sent['words'][dest][t]
                            sheet.write(rn, 0, file['name'])
                            sheet.write(rn, 1, sent_num + 1)
                            sheet.write(rn, 2, src_sent)
                            sheet.write(rn, 3, dest_sent)
                            sheet.write(rn, 4, word_num + 1)
                            sheet.write(rn, 7, src_time[src_time_pos]['s'])
                            sheet.write(rn, 8, src_time[src_time_pos]['s'] + src_time[src_time_pos]['d'])
                            sheet.write(rn, 9, t + 1)
                            sheet.write(rn, 10, dest_word['orig'])
                            sheet.write(rn, 11, dest_word['corr'])
                            if t in dest_time_cache:
                                dest_time_pos = dest_time_cache[t]
                                sheet.write(rn, 12, dest_time[dest_time_pos]['s'])
                                sheet.write(rn, 13, dest_time[dest_time_pos]['s'] + dest_time[dest_time_pos]['d'])
                            rn += 1

    wb.close()
    return send_file('/tmp/export.xlsx', as_attachment=True, cache_timeout=0)


if __name__ == '__main__':
    application.run()
