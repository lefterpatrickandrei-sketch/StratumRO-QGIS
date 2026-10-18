"""Check the approved documentation migration and protected shared work.

No product imports, inference, QGIS writes, secret reads, or application tests.
Pass --git-archives after staging/commit to verify archived bytes in Git too.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ENTRY_DOCS = ['README.md', 'AGENTS.md', 'CLAUDE.md', 'GEMINI.md',
              'docs/README.md', 'docs/PROJECT_STATE.md', 'docs/REPOSITORY_GUIDE.md',
              'docs/SYSTEM_MAP.md', 'docs/AGENT_HANDOFF.md', 'junk/README.md',
              'workspace/repository_cleanup_20261018/README.md']


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--git-archives', action='store_true')
    parser.add_argument('--approved-test-changes', type=Path,
                        help='Explicit owner-approved CI checkpoint; permits only its test paths in the product diff.')
    args = parser.parse_args()
    baseline = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))
    migration = json.loads((OUT / 'migration_applied.json').read_text(encoding='utf-8'))
    kilo = json.loads((OUT / 'agent_entries_approval.json').read_text(encoding='utf-8'))
    errors, checked = [], []
    for row in [*migration['files'], kilo]:
        dest = ROOT / row['destination']
        if not dest.is_file() or sha(dest) != row['sha256']:
            errors.append(f"Archive hash mismatch: {row['destination']}")
        if row['action'] == 'MOVE' and (ROOT / row['source']).exists():
            errors.append(f"Old report path still present: {row['source']}")
        if args.git_archives:
            archived_blob = git('show', ':' + row['destination'])
            if hashlib.sha256(archived_blob).hexdigest() != row['sha256']:
                errors.append(f"Git archive bytes differ: {row['destination']}")
        checked.append(row['destination'])

    for row in baseline['foreign_dirty_tracked']:
        p = ROOT / row['path']
        current = sha(p) if p.is_file() else None
        if current != row['sha256']:
            errors.append(f"Pre-existing dirty file changed since baseline: {row['path']}")
    original_untracked = json.loads((OUT / 'file_inventory.json').read_text(encoding='utf-8'))['untracked_paths_excluding_this_audit']
    missing_untracked = [p for p in original_untracked if not (ROOT / p).exists()]
    if missing_untracked:
        errors.append(f'{len(missing_untracked)} pre-existing untracked paths disappeared')

    # Native project stays at its tracked version. Pre-existing dirty GIS files
    # are already checked byte-for-byte above.
    project = 'workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs'
    project_changed = git('diff', '--name-only', baseline['head'], '--', project).strip()
    if project_changed:
        errors.append('Shared QGIS project differs from baseline HEAD')
    changed_product = git('diff', '--name-only', baseline['head'], '--', 'stratum_ro', 'tools', 'scripts', 'engine', 'start_platform.py').decode().splitlines()
    expected_product = {r['path'] for r in baseline['foreign_dirty_tracked'] if r['path'].startswith(('stratum_ro/', 'tools/', 'scripts/', 'engine/'))}
    approved_tests = set()
    if args.approved_test_changes:
        approval = json.loads(args.approved_test_changes.read_text(encoding='utf-8'))
        if approval.get('stage') != 'CI_REPAIR' or approval.get('owner_authorized') is not True:
            raise ValueError('An explicit owner-approved CI checkpoint is required')
        approved_tests = {p for p in approval['paths'] if p.startswith('stratum_ro/test/') and p.endswith('.py')}
    authorized_product = expected_product | approved_tests
    if set(changed_product) != authorized_product:
        errors.append('Product diff contains changes outside the pre-existing dirty files')

    # Check new navigation using exact case against tracked + explicitly created
    # paths, so Windows does not hide a GitHub case-sensitive link error.
    tracked = set(git('ls-files', '-z').decode().rstrip('\0').split('\0'))
    task_files = {p.relative_to(ROOT).as_posix() for p in OUT.iterdir() if p.is_file()}
    candidates = tracked | set(ENTRY_DOCS) | set(checked) | task_files
    links = []
    for relative in ENTRY_DOCS:
        source = ROOT / relative
        text = source.read_text(encoding='utf-8')
        no_code = re.sub(r'```.*?```', '', text, flags=re.S)
        for target in re.findall(r'\]\(([^)]+)\)', no_code):
            target = target.strip().strip('<>')
            if not target or target.startswith('#') or urlsplit(target).scheme:
                continue
            decoded = unquote(target.split('#', 1)[0])
            resolved = (source.parent / decoded).resolve()
            try:
                repo_path = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                errors.append(f'Link outside repository: {relative} -> {target}')
                continue
            if not resolved.exists():
                errors.append(f'Broken link: {relative} -> {target}')
            elif resolved.is_file() and repo_path not in candidates:
                errors.append(f'Link case/untracked dependency: {relative} -> {repo_path}')
            links.append({'source': relative, 'target': repo_path})
    result = {'status': 'PASS' if not errors else 'FAIL', 'errors': errors,
              'archive_files_sha_verified': len(checked), 'git_archive_bytes_verified': args.git_archives,
              'foreign_dirty_paths_sha_verified': len(baseline['foreign_dirty_tracked']),
              'preexisting_untracked_paths_present': len(original_untracked) - len(missing_untracked),
              'shared_qgis_project_unchanged_from_baseline_head': not bool(project_changed),
              'product_diff_contains_only_preexisting_or_approved_test_work': set(changed_product) == authorized_product,
              'explicitly_approved_ci_test_changes': sorted(approved_tests),
              'navigation_links_checked': len(links), 'links': links,
              'publication_snapshot_available': (OUT / 'publication_result.json').is_file(),
              'not_executed_by_this_check': ['product tests', 'model inference', 'QGIS session mutations', 'provider calls', 'GitHub publication']}
    name = 'verification_staged.json' if args.git_archives else 'verification_worktree.json'
    (OUT / name).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'links'}, ensure_ascii=True))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
