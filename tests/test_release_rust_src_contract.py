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

    def test_release_ready_archives_are_prepared_in_the_producer(self):
        for platform in ("linux", "windows", "macos"):
            self.assertIn(f'name: release-{platform}', BUILD)
            self.assertIn(
                f'path: ${{{{ github.workspace }}}}/rust_wasm/release-{platform}/*.tar.gz',
                BUILD,
            )

        self.assertEqual(BUILD.count("compression-level: 0"), 3)
        self.assertGreaterEqual(
            BUILD.count("for target_dir in dist-artifacts/dist/lib/rustlib/*; do"),
            3,
        )
        self.assertGreaterEqual(BUILD.count("| gzip -9 >"), 3)

    def test_rust_src_is_packaged_once_with_library_relative_paths(self):
        self.assertNotIn("git clone --depth 1 -b compile_rustc_for_wasm17", RELEASE)
        self.assertIn('library_dir="$rustlib_dir/src/rust/library"', BUILD)
        self.assertIn(
            'tar -cf - -C "$library_dir" . | gzip -9 > "$release_dir/rust-src.tar.gz"',
            BUILD,
        )
        self.assertEqual(BUILD.count('> "$release_dir/rust-src.tar.gz"'), 1)
        self.assertNotIn("--directory src/rust/library .", RELEASE)

    def test_release_uses_one_explicit_build_run(self):
        self.assertIn("build_run_id:", RELEASE)
        self.assertIn("actions: read", RELEASE)
        self.assertIn("uses: actions/download-artifact@v4", RELEASE)
        self.assertIn(
            "run-id: ${{ github.event.inputs.build_run_id }}",
            RELEASE,
        )
        self.assertIn("github-token: ${{ github.token }}", RELEASE)
        self.assertIn("repository: ${{ github.repository }}", RELEASE)
        for task, artifact in (
            ("linux", "dist-linux"),
            ("windows", "release-windows"),
            ("macos", "dist-macos"),
            ("rustc-bins", "rustc-bins"),
        ):
            self.assertIn(
                f"- task: {task}\n            artifact: {artifact}",
                RELEASE,
            )
        self.assertNotIn(
            'gh run download "${{ github.event.inputs.build_run_id }}"',
            RELEASE,
        )
        self.assertIn("gh run list --workflow build_llvm.yml", RELEASE)


if __name__ == "__main__":
    unittest.main()
