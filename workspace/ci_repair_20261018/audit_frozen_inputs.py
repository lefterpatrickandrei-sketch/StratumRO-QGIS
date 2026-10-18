"""Read-only provenance investigation; never regenerates a frozen manifest."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def variants(data):
    lf = data.replace(b'\r\n', b'\n')
    return {'raw': digest(data), 'lf': digest(lf),
            'crlf': digest(lf.replace(b'\n', b'\r\n'))}


def git_blob(revision, path):
    result = subprocess.run(['git', 'show', f'{revision}:{path}'], cwd=ROOT,
                            capture_output=True)
    return result.stdout if result.returncode == 0 else None


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    rows = []
    for name in ('manifest_ground_truth.json', 'manifest_critical_modules.json'):
        manifest = json.loads((ROOT / 'workspace/baseline' / name).read_text(encoding='utf-8'))
        for original, expected in manifest.items():
            target = {'stratum_ro/volumetric_3d.py': 'stratum_ro/domain/city_3d/builder.py'}.get(original, original)
            p = ROOT / target
            committed = git_blob(head, target)
            worktree = p.read_bytes() if p.is_file() else None
            row = {'manifest': name, 'original_path': original, 'target_path': target,
                   'expected_sha256': expected['sha256'],
                   'worktree_hashes': variants(worktree) if worktree is not None else None,
                   'head_hashes': variants(committed) if committed is not None else None}
            row['head_expected_match_variants'] = [k for k, value in (row['head_hashes'] or {}).items() if value == expected['sha256']]
            if not row['head_expected_match_variants']:
                history = subprocess.check_output(['git', 'log', '--format=%H', '--', target, original], cwd=ROOT).decode().splitlines()
                matches = []
                for rev in history:
                    for candidate in dict.fromkeys((target, original)):
                        data = git_blob(rev, candidate)
                        if data is not None:
                            match = [k for k, value in variants(data).items() if value == expected['sha256']]
                            if match:
                                matches.append({'revision': rev, 'path': candidate, 'newline_variants': match})
                row['historical_expected_matches'] = matches
            rows.append(row)
    record = {'head': head, 'method': 'Compare raw/LF/CRLF bytes from working tree, Git HEAD and historical blobs. No manifest or source modified.', 'files': rows}
    (OUT / 'frozen_input_provenance.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    for row in rows:
        print(json.dumps({'path': row['target_path'], 'matches_head': row['head_expected_match_variants'], 'history_matches': len(row.get('historical_expected_matches', [])), 'working_matches': [k for k, value in (row['worktree_hashes'] or {}).items() if value == row['expected_sha256']]}))


if __name__ == '__main__':
    main()
