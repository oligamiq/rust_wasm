from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD = (ROOT / ".github/workflows/rustc_llvm_with_lld.yml").read_text()
RELEASE = (ROOT / ".github/workflows/create_release.yml").read_text()


class RustSrcReleaseContractTest(unittest.TestCase):
    def test_all_rust_checkouts_use_one_source_ref(self):
        self.assertIn("RUST_SOURCE_REF: cf327c2068549194a29160499c2ecafa9061e46e", BUILD)
        self.assertEqual(BUILD.count("ref: ${{ env.RUST_SOURCE_REF }}"), 5)
        self.assertNotIn("git checkout cf327c2068549194a29160499c2ecafa9061e46e", BUILD)
        self.assertIn("- all", BUILD)
        self.assertEqual(BUILD.count("github.event.inputs.job == 'all'"), 6)

    def test_linux_artifact_contains_real_source_from_its_checkout(self):
        self.assertIn("rm -rf dist/lib/rustlib/src", BUILD)
        self.assertIn("mkdir -p dist/lib/rustlib/src/rust", BUILD)
        self.assertIn("cp -a library dist/lib/rustlib/src/rust/library", BUILD)

    def test_release_packages_library_relative_archive_without_reclone(self):
        self.assertNotIn("git clone --depth 1 -b compile_rustc_for_wasm17", RELEASE)
        self.assertIn('if [ ! -d "src/rust/library" ]; then', RELEASE)
        self.assertIn('--directory src/rust/library .', RELEASE)

    def test_release_uses_one_explicit_build_run(self):
        self.assertIn("build_run_id:", RELEASE)
        self.assertNotIn("gh run list --workflow rustc_llvm_with_lld.yml", RELEASE)
        self.assertIn('gh run download "${{ github.event.inputs.build_run_id }}"', RELEASE)


if __name__ == "__main__":
    unittest.main()
