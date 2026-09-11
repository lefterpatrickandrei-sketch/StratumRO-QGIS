# -*- coding: utf-8 -*-
"""
Convert absolute file:/// links to proper GitHub relative markdown links.
"""
import os
import re

root_dir = os.path.abspath('.')

md_files = []
for r, d, files in os.walk('.'):
    if 'venv' in r or '.git' in r:
        continue
    for f in files:
        if f.endswith('.md'):
            md_files.append(os.path.join(r, f))

print(f"Found {len(md_files)} markdown files")
total_replaced = 0

for md_path in md_files:
    with open(md_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    pattern = re.compile(r'file:///[cC]:/Users/lefpa/Downloads/QGIS-AI/([^\)\s\"\'\>]+)')
    if pattern.search(content):
        rel_dir = os.path.dirname(os.path.abspath(md_path))
        def repl(match):
            target = match.group(1)
            abs_target = os.path.join(root_dir, target.replace('/', os.sep))
            rel = os.path.relpath(abs_target, rel_dir).replace(os.sep, '/')
            return rel

        new_content = pattern.sub(repl, content)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        total_replaced += 1
        print(f"Updated links in: {md_path}")

print(f"Total markdown files updated: {total_replaced}")
