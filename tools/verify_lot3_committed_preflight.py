"""Verify repair regressions against committed preflight, without replacing files."""
from pathlib import Path
import subprocess
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for name, path in [
    ('stratum_ro.evaluation_preflight', 'stratum_ro/evaluation_preflight.py'),
    ('stratum_ro.test.test_evaluation_preflight', 'stratum_ro/test/test_evaluation_preflight.py'),
]:
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / path)
    sys.modules[name] = module
    source = subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT,
                                     text=True, encoding='utf-8')
    exec(compile(source, module.__file__, 'exec'), module.__dict__)

names = [
    'test_roof_mask_fidelity', 'test_roof_masked_preflight',
    'test_cadastral_roof_workflow', 'test_roof_gap_edges',
    'test_fusion_refinement', 'test_fusion_guidance', 'test_roof_simple_geometry',
    'test_roof_body_partition', 'test_roof_body_recovery_partition',
    'test_roof_revision_review',
]
suite = unittest.defaultTestLoader.loadTestsFromNames(['stratum_ro.test.' + n for n in names])
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
