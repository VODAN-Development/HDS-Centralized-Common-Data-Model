"""Exercise the actual command-line entry point, including its exit status."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ValidatorCommandTests(unittest.TestCase):
    def run_validator(self, *args):
        # Also supports running tests with locally supplied dependency paths.
        env = os.environ.copy()
        env['PYTHONPATH'] = os.pathsep.join(str(Path(p).resolve()) for p in sys.path if p)
        with tempfile.TemporaryDirectory() as cwd:
            return subprocess.run([sys.executable, '-B', str(ROOT / 'validate.py'), *map(str, args)],
                                  cwd=cwd, env=env, capture_output=True, text=True, timeout=30)

    def test_model_validation_succeeds_outside_repository_directory(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Conforms: True', result.stdout)

    def test_all_bundled_examples_validate(self):
        examples = sorted((ROOT / 'examples').glob('*.ttl'))
        self.assertTrue(examples)
        for example in examples:
            with self.subTest(example=example.name):
                result = self.run_validator(example)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('Instance data:', result.stdout)

    def test_invalid_instance_returns_failure_and_validation_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'invalid.ttl'
            path.write_text('''@prefix hds: <https://vodan-development.github.io/HDS-Centralized-Common-Data-Model/hds-cdm.ttl#> .
<https://example.org/incident> a hds:Incident ; hds:victimCount "many" .
''', encoding='utf-8')
            result = self.run_validator(path)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Conforms: False', result.stdout)
        self.assertIn('victimCount', result.stdout)
