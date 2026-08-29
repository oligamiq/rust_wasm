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

    def test_macos_owns_cross_platform_wasi_release_archives(self):
        ownership_filter = (
            '              if [ "$target" = "wasm32-wasip1" ] || '
            '[ "$target" = "wasm32-wasip1-threads" ]; then\n'
            "                continue\n"
            "              fi"
        )
        jobs = {
            "linux": BUILD.split("\n  dist-linux:\n", 1)[1].split(
                "\n  dist-macos:\n", 1
            )[0],
            "macos": BUILD.split("\n  dist-macos:\n", 1)[1].split(
                "\n  dist-windows:\n", 1
            )[0],
            "windows": BUILD.split("\n  dist-windows:\n", 1)[1],
        }
        prepares = {
            platform: job.split("\n      - name: prepare dist artifacts\n", 1)[1].split(
                "\n      - name: upload dist artifacts\n", 1
            )[0]
            for platform, job in jobs.items()
        }

        self.assertIn(ownership_filter, prepares["linux"])
        self.assertIn(ownership_filter, prepares["windows"])
        self.assertNotIn(ownership_filter, prepares["macos"])
        self.assertEqual(BUILD.count(ownership_filter), 2)
        for platform, prepare in prepares.items():
            with self.subTest(platform=platform):
                self.assertIn(
                    "for target_dir in dist-artifacts/dist/lib/rustlib/*; do",
                    prepare,
                )
                self.assertIn(f"dist-{platform}.tar", prepare)

    def test_unix_release_archive_pipelines_enable_pipefail(self):
        for platform, next_platform in (("linux", "macos"), ("macos", "windows")):
            job = BUILD.split(f"\n  dist-{platform}:\n", 1)[1].split(
                f"\n  dist-{next_platform}:\n", 1
            )[0]
            prepare = job.split("\n      - name: prepare dist artifacts\n", 1)[1].split(
                "\n      - name: upload dist artifacts\n", 1
            )[0]
            with self.subTest(platform=platform):
                self.assertIn("        run: |\n          set -o pipefail\n", prepare)

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
        for artifact in (
            "release-linux",
            "release-windows",
            "release-macos",
            "rustc-bins",
        ):
            self.assertIn(f"artifact: {artifact}", RELEASE)
        for artifact in ("dist-linux", "dist-windows", "dist-macos"):
            self.assertNotIn(f"artifact: {artifact}", RELEASE)
        self.assertNotIn(
            'gh run download "${{ github.event.inputs.build_run_id }}"',
            RELEASE,
        )
        self.assertIn("gh run list --workflow build_llvm.yml", RELEASE)

    def test_release_matrix_has_exact_parallel_shards(self):
        expected = []
        for platform, shard_count in (("linux", 6), ("windows", 4), ("macos", 4)):
            for shard in range(shard_count):
                expected.append(
                    f"- task: {platform}-target-{shard}\n"
                    "            kind: target\n"
                    f"            platform: {platform}\n"
                    f"            artifact: release-{platform}\n"
                    f"            shard: {shard}\n"
                    f"            shard_count: {shard_count}"
                )
        expected.extend(
            (
                "- task: linux-source\n            kind: source\n"
                "            platform: linux\n            artifact: release-linux",
                "- task: rustc-bins\n            kind: rustc\n"
                "            artifact: rustc-bins",
                "- task: llvm-bins\n            kind: llvm",
            )
        )
        for row in expected:
            self.assertIn(row, RELEASE)
        self.assertEqual(RELEASE.count("          - task:"), 17)

    def test_modulo_shards_cover_each_candidate_once(self):
        for candidate_count, shard_count in ((23, 6), (17, 4), (9, 4)):
            assignments = [
                index
                for shard in range(shard_count)
                for index in range(candidate_count)
                if index % shard_count == shard
            ]
            self.assertEqual(sorted(assignments), list(range(candidate_count)))

    def test_release_shards_copy_gzip_and_create_brotli(self):
        self.assertIn("LC_ALL=C sort", RELEASE)
        self.assertIn("index % shard_count", RELEASE)
        self.assertIn('name != "rust-src.tar.gz"', RELEASE)
        self.assertIn('name != "rustc-src.tar.gz"', RELEASE)
        self.assertIn('cp "$archive" "${{ github.workspace }}/x-tools/$name"', RELEASE)
        self.assertIn('gzip -dc "$archive" | brotli -q 11', RELEASE)
        self.assertNotIn("jlumbroso/free-disk-space", RELEASE)
        self.assertIn("compression-level: 0", RELEASE)
        self.assertIn("pattern: release-assets-*", RELEASE)
        self.assertIn("merge-multiple: true", RELEASE)

    def test_publish_rejects_duplicate_basenames_before_merged_download(self):
        validation_download = (
            "      - name: download assets for duplicate validation\n"
            "        uses: actions/download-artifact@v4\n"
            "        with:\n"
            "          path: validation-assets\n"
            "          pattern: release-assets-*"
        )
        merged_download = (
            "      - name: download assets\n"
            "        uses: actions/download-artifact@v4\n"
            "        with:\n"
            "          path: x-tools\n"
            "          pattern: release-assets-*\n"
            "          merge-multiple: true"
        )
        self.assertIn(validation_download, RELEASE)
        validation_download_step = RELEASE.split(
            "\n      - name: download assets for duplicate validation\n", 1
        )[1].split("\n      - name: reject duplicate release asset basenames\n", 1)[0]
        self.assertNotIn("merge-multiple", validation_download_step)
        validation = RELEASE.split(
            "\n      - name: reject duplicate release asset basenames\n", 1
        )[1].split("\n      - name: download assets\n", 1)[0]
        self.assertIn("set -o pipefail", validation)
        self.assertIn('find validation-assets -type f -printf \'%f\\n\'', validation)
        self.assertIn("uniq -d", validation)
        self.assertIn('if [ -n "$duplicate_names" ]; then', validation)
        self.assertIn("exit 1", validation)
        self.assertIn(merged_download, RELEASE)
        self.assertLess(RELEASE.index(validation_download), RELEASE.index(merged_download))

    def test_release_asset_pipelines_enable_pipefail(self):
        create_assets = RELEASE.split("\n      - name: create release assets\n", 1)[
            1
        ].split("\n      - name: upload partial assets\n", 1)[0]
        self.assertIn(
            '        run: |\n          set -o pipefail\n'
            '          mkdir -p "${{ github.workspace }}/x-tools"',
            create_assets,
        )


if __name__ == "__main__":
    unittest.main()
