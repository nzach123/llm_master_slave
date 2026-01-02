
import unittest
from tools.fuzzy_match import fuzzy_patch
from tools.patcher import apply_patch
import tempfile
import os
from pathlib import Path

class TestFuzzyPatcher(unittest.TestCase):
    def test_exact_match(self):
        original = "def foo():\n    return 1\n"
        search = "def foo():\n    return 1\n"
        replace = "def foo():\n    return 2\n"
        result, success = fuzzy_patch(original, search, replace)
        self.assertTrue(success)
        self.assertEqual(result, replace)

    def test_fuzzy_match_whitespace(self):
        original = "def foo():\n      return 1\n" # Extra spaces
        search = "def foo():\n    return 1\n"     # Standard spaces
        replace = "def foo():\n    return 2\n"

        result, success = fuzzy_patch(original, search, replace)
        self.assertTrue(success)
        # Should contain the replacement
        self.assertIn("return 2", result)

    def test_fuzzy_match_fail(self):
        original = "def bar():\n    return 1\n"
        search = "def foo():\n    return 1\n"
        replace = "def foo():\n    return 2\n"

        result, success = fuzzy_patch(original, search, replace)
        self.assertFalse(success)
        self.assertEqual(result, original)

    def test_apply_patch_integration(self):
        # Create a temp directory inside the current working directory to satisfy PathSecurityError
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as tmp_dir:
            tmp_path = os.path.join(tmp_dir, 'test_file.py')
            with open(tmp_path, 'w') as f:
                f.write("def foo():\n      return 1\n") # mismatch whitespace

            search = "def foo():\n    return 1\n"
            replace = "def foo():\n    return 2\n"

            # Should succeed via fuzzy fallback
            success = apply_patch(tmp_path, search, replace)
            self.assertTrue(success)

            with open(tmp_path, 'r') as f:
                content = f.read()
                self.assertIn("return 2", content)

if __name__ == '__main__':
    unittest.main()
