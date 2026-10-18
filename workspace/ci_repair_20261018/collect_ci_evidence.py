"""Save completed public GitHub CI evidence without changing jobs or repository state."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

REPOSITORY = 'lefterpatrickandrei-sketch/StratumRO-QGIS'
OUT = Path(__file__).resolve().parent


def api(path):
    return subprocess.check_output(['gh', 'api', f'repos/{REPOSITORY}/{path}'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run_id', type=int)
    args = parser.parse_args()
    run = json.loads(api(f'actions/runs/{args.run_id}'))
    if run['status'] != 'completed':
        raise SystemExit('Run is not completed; no final-result files written.')
    jobs = json.loads(api(f'actions/runs/{args.run_id}/jobs'))['jobs']
    results = []
    for job in jobs:
        log = api(f'actions/jobs/{job["id"]}/logs')
        filename = f'github_job_{job["id"]}.txt'
        destination = OUT / filename
        if destination.exists() and destination.read_bytes() != log:
            raise ValueError(f'Existing evidence differs: {filename}')
        destination.write_bytes(log)
        text = log.decode('utf-8', errors='replace')
        counts = re.findall(r'Ran (\d+) tests? in ([\d.]+)s', text)
        results.append({'name': job['name'], 'id': job['id'], 'status': job['status'],
                        'conclusion': job['conclusion'], 'url': job['html_url'],
                        'test_suites': [{'tests_run': int(count), 'seconds': float(seconds)} for count, seconds in counts],
                        'steps': [{'name': step['name'], 'conclusion': step['conclusion']} for step in job['steps']],
                        'log_file': filename, 'log_sha256': hashlib.sha256(log).hexdigest()})
    record = {'run_id': run['id'], 'attempt': run['run_attempt'],
              'head_sha': run['head_sha'], 'url': run['html_url'],
              'status': run['status'], 'conclusion': run['conclusion'], 'jobs': results,
              'scope': 'Software and integrity checks on GitHub runners; not real-model inference or independent cadastral accuracy.'}
    filename = f'run_{run["id"]}_attempt{run["run_attempt"]}.json'
    (OUT / filename).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'file': filename, 'head': record['head_sha'], 'conclusion': record['conclusion'],
                      'jobs': [{'name': j['name'], 'conclusion': j['conclusion'], 'test_suites': j['test_suites']} for j in results]}))
    if record['conclusion'] != 'success':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
