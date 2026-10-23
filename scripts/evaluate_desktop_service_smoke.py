"""Grade controlled desktop QA separately from HTTP transport success."""
import argparse
import json
from pathlib import Path


def evaluate_runtime_health(core_reachable, renderer_alive, frame_sequences):
    """Do not infer service or renderer health from an existing UI process."""
    core = 'reachable' if core_reachable is True else 'unreachable' if core_reachable is False else 'unknown'
    if not renderer_alive:
        renderer = 'not-running'
    elif len(frame_sequences) < 2:
        renderer = 'unobserved'
    elif any(b > a for a, b in zip(frame_sequences, frame_sequences[1:])):
        renderer = 'advancing'
    else:
        renderer = 'stalled'
    return {'core': core, 'renderer': renderer,
            'healthy': core == 'reachable' and renderer == 'advancing',
            'organicTrafficValidated': False}


def evaluate(samples):
    if not samples:
        return {'status': 'inconclusive-no-traffic', 'samples': 0, 'failures': []}
    failures = []
    for index, sample in enumerate(samples):
        if sample.get('error'):
            failures.append({'sample': index, 'reason': 'transport-error'})
        checks = {c['name']: c for c in sample.get('checks', [])}
        for name, limit in [('tts', 3), ('stt-synthetic-roundtrip', 5), ('conversation', 10)]:
            check = checks.get(name)
            if not check:
                failures.append({'sample': index, 'reason': 'missing-' + name})
            elif check['seconds'] > limit:
                failures.append({'sample': index, 'reason': name + '-latency', 'seconds': check['seconds'], 'limitSeconds': limit})
        # This fixture says "안녕하세요. 가현입니다."; this is an entity-preservation test,
        # not an automatic replacement rule for arbitrary user speech.
        if '가현' not in sample.get('transcription', {}).get('transcript', ''):
            failures.append({'sample': index, 'reason': 'fixture-name-not-preserved'})
        if not sample.get('conversation', {}).get('content', '').strip():
            failures.append({'sample': index, 'reason': 'empty-conversation'})
    return {'status': 'failed' if failures else 'synthetic-smoke-passed', 'samples': len(samples),
            'organicTrafficValidated': False, 'failures': failures}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('samples', nargs='+', type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate([json.loads(p.read_text()) for p in args.samples]), ensure_ascii=False, indent=2))
