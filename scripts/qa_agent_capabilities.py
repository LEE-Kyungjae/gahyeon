#!/usr/bin/env python3
"""Opt-in live probes through the real desktop conversation endpoint.

Uses synthetic content and an isolated QA installation/session. Stores no token.
HTTP success is transport evidence only, never task-completion verification.
"""
import argparse
import json
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=Path('quality/agent-capability-cases.json'))
    args = parser.parse_args()
    from macos_production_core import connect_production_core
    url, token, speech = connect_production_core()
    args.output.mkdir(parents=True, exist_ok=True)
    installation = 'qa-capabilities-' + uuid.uuid4().hex
    report = {'schemaVersion': 1, 'startedAt': time.time(), 'speechStatus': speech,
              'syntheticTraffic': True, 'productionValidated': False, 'cases': []}
    for case in json.loads(args.cases.read_text())['cases']:
        session = 'qa-capability-' + uuid.uuid4().hex
        body = {'requestId': 'qa:' + uuid.uuid4().hex, 'installationId': installation,
                'displayName': 'QA synthetic tester', 'characterId': 'gahyeon',
                'message': case['prompt']}
        request = urllib.request.Request(
            url + '/gahyeon/desktop/conversations/' + session + '/messages',
            data=json.dumps(body).encode(),
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        start = time.monotonic()
        result = {'id': case['id'], 'category': case['category'], 'acceptance': case['acceptance'],
                  'completionVerified': False}
        try:
            with urllib.request.urlopen(request, timeout=100) as response:
                result['httpStatus'] = response.status
                result['response'] = json.loads(response.read(256_000))
        except urllib.error.HTTPError as exc:
            result['httpStatus'] = exc.code
            result['error'] = 'http_error'
        except (TimeoutError, OSError, ValueError):
            result['error'] = 'timeout_or_transport_error'
        result['elapsedSeconds'] = round(time.monotonic() - start, 3)
        report['cases'].append(result)
        (args.output / 'live-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({k: result[k] for k in ('id', 'httpStatus', 'error', 'elapsedSeconds') if k in result}), flush=True)
        if result.get('httpStatus') in (401, 403):
            break  # Never bypass an identity/ownership denial.


if __name__ == '__main__':
    main()
