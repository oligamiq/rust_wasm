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

    def test_windows_release_archives_are_prepared_in_the_producer(self):
        self.assertIn(
            'release_dir="${WS_FORWARD}/rust_wasm/release-windows"',
            BUILD,
        )
        self.assertIn(
            "for target_dir in dist-artifacts/dist/lib/rustlib/*; do",
            BUILD,
        )
        self.assertIn(
            'tar --force-local --ignore-failed-read -chzf "$release_dir/${target}.tar.gz" *',
            BUILD,
        )
        self.assertIn("name: release-windows", BUILD)
        self.assertIn("compression-level: 0", BUILD)
        self.assertIn(
            'gzip -dc "$archive" | brotli -q 11 > "${{ github.workspace }}/x-tools/${name%.tar.gz}.tar.br"',
            RELEASE,
        )
        self.assertNotIn(
            '${{ github.workspace }}/artifacts/dist-windows/dist/lib/rustlib',
            RELEASE,
        )

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
