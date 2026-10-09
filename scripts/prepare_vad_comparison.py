#!/usr/bin/env python3
"""Build reproducible non-private VAD fixtures from explicitly supplied synthetic WAVs."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import wave

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
fixtures = []
rate = 48000


def write(name, samples, category, expected, source=None):
    pcm = array.array('h')
    for value in samples:
        value = max(-32768, min(32767, round(value)))
        pcm.extend((value, value))
    if sys.byteorder != 'little':
        pcm.byteswap()
    path = args.output / (name + '.wav')
    with wave.open(str(path), 'wb') as out:
        out.setparams((2, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(pcm.tobytes())
    fixtures.append(dict(file=path.name, category=category, speechExpected=expected,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(), source=source))


for name in ['silence', 'white-quiet', 'white-loud', 'hum', 'clicks', 'tone', 'fan']:
    rng = random.Random(20261009)
    low = 0
    samples = []
    for i in range(rate * 8):
        white = rng.gauss(0, 1)
        low = .995 * low + .005 * white
        value = {'silence': 0, 'white-quiet': white * 25, 'white-loud': white * 2000,
                 'hum': 700 * math.sin(2 * math.pi * 60 * i / rate),
                 'clicks': 12000 * math.exp(-(i % (rate // 2)) / 120) * white,
                 'tone': 3000 * math.sin(2 * math.pi * 1000 * i / rate),
                 'fan': low * 10000 + white * 100}[name]
        samples.append(value)
    write(name, samples, 'non-speech', False)

for path in sorted(args.source.glob('*.wav')):
    # All supplied inputs must be known synthetic/public fixtures, never user recordings.
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 's16le',
                                   '-ar', str(rate), '-ac', '1', '-'])
    source = array.array('h', raw)
    if sys.byteorder != 'little':
        source.byteswap()
    for variation, gain, noise in [('clean', 1, 0), ('quiet', .08, 0), ('noisy', 1, 600)]:
        rng = random.Random(20261009)
        # Known 1s leading and 3s trailing non-speech; same noise continues through pauses.
        audio = [0] * rate + list(source) + [0] * (rate * 3)
        samples = [x * gain + rng.gauss(0, noise) for x in audio]
        write(path.stem + '-' + variation, samples, 'speech-' + variation, True,
              dict(name=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   speechContainerStartMs=1000, speechContainerEndMs=1000 + len(source) / 48))

(args.output / 'fixtures.json').write_text(json.dumps(dict(
    seed=20261009, sampleRate=rate, channels=2, syntheticOnly=True,
    annotation='Speech presence only; TTS container boundaries are not human frame labels',
    fixtures=fixtures), ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'fixtures': len(fixtures), 'output': str(args.output)}))
