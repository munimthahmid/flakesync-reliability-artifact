import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_release.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("release_verifier", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = load_verifier()

    def test_frozen_source_manifest(self):
        self.verifier.verify_source_manifest()

    def test_patch_manifests(self):
        self.verifier.verify_patch_manifests()

    def test_scientific_counts(self):
        self.verifier.verify_scientific_counts()

    def test_release_contains_no_private_paths_or_secret_shapes(self):
        self.verifier.verify_file_policy()

    def test_results_are_deterministic(self):
        self.verifier.verify_deterministic_results()


if __name__ == "__main__":
    unittest.main()
