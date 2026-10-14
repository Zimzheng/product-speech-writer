import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('installer', ROOT / 'scripts/install_local.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InstallTests(unittest.TestCase):
    def test_explicit_destination_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'skills' / 'product-talk-script'
            command = [sys.executable, str(ROOT / 'scripts/install_local.py'),
                       '--destination', str(target)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual((target / 'SKILL.md').read_bytes(), (ROOT / 'SKILL.md').read_bytes())
            sentinel = target / 'keep.txt'
            sentinel.write_text('user content')
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'user content')

    def test_all_project_directories(self):
        with tempfile.TemporaryDirectory() as td:
            for tool, relative in MODULE.PROJECT_ROOTS.items():
                project = Path(td) / tool
                project.mkdir()
                command = [sys.executable, str(ROOT / 'scripts/install_local.py'),
                           '--tool', tool, '--scope', 'project', '--project', str(project)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((project / relative / 'product-talk-script' / 'SKILL.md').is_file())


if __name__ == '__main__':
    unittest.main()
