"""Repair explicit links to approved moves, without changing archived evidence."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT / 'migration_manifest.json').read_text(encoding='utf-8'))
dirty = {x['path'] for x in json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))['foreign_dirty_tracked']}
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().rstrip('\0').split('\0')
changes = []
for relative in tracked:
    p = ROOT / relative
    if relative in dirty or not p.is_file() or p.suffix != '.md' or relative.startswith(('junk/', 'workspace/')):
        continue
    raw = p.read_bytes()
    text = raw.decode('utf-8-sig')
    updated = text
    for entry in manifest['files']:
        if entry['action'] != 'MOVE':
            continue
        old, new = entry['source'], entry['destination']
        # Existing explicit parent links in docs, plus old workstation file URIs.
        if relative.startswith('docs/') and relative.count('/') == 1:
            updated = updated.replace(f'](../{old})', f'](../{new})')
        updated = updated.replace(f'](file:///c:/Users/lefpa/Downloads/QGIS-AI/{old})', f'](../{new})')
    if relative == 'docs/ARTIFACT_MANIFEST.md':
        updated = updated.replace('`KILO_CONFIGURATION_AUDIT.md`', '`junk/2026-10-18/root_reports/KILO_CONFIGURATION_AUDIT.md`')
    if relative == 'docs/PROJECT_PROGRESS.md':
        updated = ('> Historical progress log. For current status and actual local/remote Git differences, read '
                   '[PROJECT_STATE.md](PROJECT_STATE.md). Claims below retain their original date/context; '
                   'the 2026-10-18 audit does not confirm them as current.\n\n' + updated)
    if updated != text:
        # Keep the pre-existing file's newline convention and BOM.
        newline = '\r\n' if b'\r\n' in raw else '\n'
        normalized = updated.replace('\r\n', '\n').replace('\r', '\n').replace('\n', newline)
        p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + normalized.encode('utf-8'))
        changes.append(relative)
(OUT / 'link_updates.json').write_text(json.dumps({'changed_paths': changes, 'scope': 'Documentation only; old report bodies in junk remain byte-identical.'}, indent=2) + '\n', encoding='utf-8')
print(f'Repaired documentation links in {len(changes)} files.')
