import json
from pathlib import Path

sample_rate = 16000.0

word_times = {}
for f in Path('/home/guest/Desktop/PINC/pinc').glob('*_ses/*_bndl/*.json'):
    with open(f) as fp:
        times = []
        data = json.load(fp)
        for word in data['levels'][0]['items']:
            start = word['sampleStart'] / sample_rate
            dur = word['sampleDur'] / sample_rate
            text = word['labels'][0]['value']
            if text:
                times.append({'t': text, 's': start, 'd': dur})
        word_times[f.stem[:-6]] = times

with open('../times.json', 'w') as f:
    json.dump(word_times, f, indent=4)

print('Done')
