# Parallel Release Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each of the 19 `create_release.yml` package jobs finish in less than 15 minutes while preserving all public release assets.

**Architecture:** The producer creates gzip-compressed release-ready target archives for Linux, Windows, and macOS without changing the existing `dist-*` artifacts. The release fans gzip-to-Brotli conversion across 8 Linux target shards, 4 Windows target shards, 4 macOS target shards, and one Linux source job, then converts each target shard's deterministic assignment in parallel and merges the uniquely named partial artifacts for publication.

**Tech Stack:** GitHub Actions YAML, Bash, GNU/BSD tar, gzip, Brotli, `actions/upload-artifact@v4`, `actions/download-artifact@v4`, Python `unittest`, actionlint, GitHub CLI.

## Global Constraints

- Every `create_release.yml` package job must complete in less than 900 seconds; the publish job is outside this limit.
- Keep gzip level 9 and Brotli quality 11.
- Preserve every public `.tar.gz` and `.tar.br` asset name and archive member layout.
- Preserve existing `dist-linux`, `dist-windows`, and `dist-macos` artifacts unchanged.
- `release-linux` contains Linux target gzip archives, required `rust-src.tar.gz`, and optional `rustc-src.tar.gz`.
- `release-windows` and `release-macos` contain target gzip archives only.
- Use exactly 8 Linux target shards, 4 Windows target shards, 4 macOS target shards, one Linux source job, one rustc-bins job, and one llvm-bins job.
- Every Rust artifact used by the release must come from one new successful `job=all` producer run using `RUST_SOURCE_REF: cf327c2068549194a29160499c2ecafa9061e46e`.
- LLVM continues to come from the latest successful independent `build_llvm.yml` run.
- Do not add retries, archive digests, embedded compiler identity checks, or lower compression quality.
- Push and dispatch only `feat/browser-rust-std-artifacts`; do not modify or push `main`.
- If a producer or release run fails, record the diagnosis and stop without rerunning.

---

### Task 1: Produce Release-Ready Linux And macOS Archives

**Files:**
- Modify: `tests/test_release_rust_src_contract.py`
- Modify: `.github/workflows/rustc_llvm_with_lld.yml:600-618,722-740,860-902`

**Interfaces:**
- Consumes: producer directories `dist-artifacts/dist/lib/rustlib` populated by each OS build.
- Produces: `release-linux/*.tar.gz`, `release-windows/*.tar.gz`, and `release-macos/*.tar.gz`, uploaded with `compression-level: 0`.

- [ ] **Step 1: Replace the producer contract tests before workflow changes**

Replace `test_release_packages_library_relative_archive_without_reclone` and `test_windows_release_archives_are_prepared_in_the_producer` with tests that require producer-side archives for all platforms:

```python
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
```

Keep the source-ref and Linux checkout-copy tests unchanged. Update the explicit build-run mapping test later in Task 2; do not weaken it here.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
```

Expected: the new producer tests fail because `release-linux`, `release-macos`, and producer-side `rust-src.tar.gz` are absent.

- [ ] **Step 3: Add Linux release-ready archive generation**

In the Linux `prepare dist artifacts` step, immediately after `rm -rf dist-artifacts/dist/bin`, add:

```bash
          release_dir="${{ github.workspace }}/rust_wasm/release-linux"
          rustlib_dir="dist-artifacts/dist/lib/rustlib"
          library_dir="$rustlib_dir/src/rust/library"
          if [ ! -d "$library_dir" ]; then
            echo "dist-linux artifact is missing src/rust/library"
            exit 1
          fi
          mkdir -p "$release_dir"
          tar -cf - -C "$library_dir" . | gzip -9 > "$release_dir/rust-src.tar.gz"
          test -s "$release_dir/rust-src.tar.gz"

          if [ -d "$rustlib_dir/rustc-src" ]; then
            tar -cf - -C "$rustlib_dir" rustc-src | gzip -9 > "$release_dir/rustc-src.tar.gz"
            test -s "$release_dir/rustc-src.tar.gz"
          fi

          target_count=0
          for target_dir in dist-artifacts/dist/lib/rustlib/*; do
            if [ -d "$target_dir/lib" ]; then
              target=$(basename "$target_dir")
              (
                cd "$target_dir/lib"
                tar -chf - *
              ) | gzip -9 > "$release_dir/${target}.tar.gz"
              test -s "$release_dir/${target}.tar.gz"
              target_count=$((target_count + 1))
            fi
          done
          if [ "$target_count" -eq 0 ]; then
            echo "dist-linux artifact contains no target libraries"
            exit 1
          fi
```

Leave the existing `dist-linux.tar` creation and cleanup unchanged.

- [ ] **Step 4: Upload the Linux release-ready artifact**

Immediately after the existing `upload dist artifacts` step for Linux, add:

```yaml
      - name: upload release-ready linux artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-linux
          path: ${{ github.workspace }}/rust_wasm/release-linux/*.tar.gz
          if-no-files-found: error
          compression-level: 0
```

- [ ] **Step 5: Add macOS release-ready generation and upload**

In the macOS `prepare dist artifacts` step, immediately after `rm -rf dist-artifacts/dist/bin`, add:

```bash
          release_dir="${{ github.workspace }}/rust_wasm/release-macos"
          mkdir -p "$release_dir"
          target_count=0
          for target_dir in dist-artifacts/dist/lib/rustlib/*; do
            if [ -d "$target_dir/lib" ]; then
              target=$(basename "$target_dir")
              (
                cd "$target_dir/lib"
                tar -chf - *
              ) | gzip -9 > "$release_dir/${target}.tar.gz"
              test -s "$release_dir/${target}.tar.gz"
              target_count=$((target_count + 1))
            fi
          done
          if [ "$target_count" -eq 0 ]; then
            echo "dist-macos artifact contains no target libraries"
            exit 1
          fi
```

Immediately after the existing macOS `upload dist artifacts` step, add:

```yaml
      - name: upload release-ready macos artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-macos
          path: ${{ github.workspace }}/rust_wasm/release-macos/*.tar.gz
          if-no-files-found: error
          compression-level: 0
```

- [ ] **Step 6: Make Windows gzip level and validation explicit**

In the existing Windows release archive loop, replace the `tar -chzf` command with the same portable pipeline:

```bash
              (
                cd "$target_dir/lib"
                tar -chf - *
              ) | gzip -9 > "$release_dir/${target}.tar.gz"
              test -s "$release_dir/${target}.tar.gz"
```

Add `target_count=0` before the loop, increment it after each archive, and fail after the loop when it remains zero. Keep `WS_FORWARD`, `dist-windows.tar`, and both existing Windows uploads unchanged.

- [ ] **Step 7: Verify producer contracts and workflow syntax**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 .github/workflows/rustc_llvm_with_lld.yml
git diff --check
```

Expected: Python tests that do not depend on Task 2 pass. actionlint reports only the pre-existing `actions/setup-java@v3` diagnostic at line 436; no diagnostic points to a release-ready producer block. `git diff --check` is silent.

- [ ] **Step 8: Commit the producer change**

```bash
git add tests/test_release_rust_src_contract.py .github/workflows/rustc_llvm_with_lld.yml
git commit -m "feat: prepare release archives in producer"
```

---

### Task 2: Shard Release Packaging Across Nineteen Jobs

**Files:**
- Modify: `tests/test_release_rust_src_contract.py`
- Modify: `.github/workflows/create_release.yml:19-238`

**Interfaces:**
- Consumes: `release-linux`, `release-windows`, and `release-macos` from Task 1; `rustc-bins` from the same producer run; latest successful independent `llvm-bins`.
- Produces: 19 unique `release-assets-${{ matrix.task }}` artifacts merged by the existing publish job.

- [ ] **Step 1: Write failing matrix and sharding contracts**

In `test_release_uses_one_explicit_build_run`, replace the old `(task, artifact)` loop with:

```python
        for artifact in (
            "release-linux",
            "release-windows",
            "release-macos",
            "rustc-bins",
        ):
            self.assertIn(f"artifact: {artifact}", RELEASE)
        for artifact in ("dist-linux", "dist-windows", "dist-macos"):
            self.assertNotIn(f"artifact: {artifact}", RELEASE)
```

Keep its explicit `build_run_id` and independent LLVM lookup assertions. Add these tests:

```python
    def test_release_matrix_has_exact_parallel_shards(self):
        expected = []
        for platform, shard_count in (("linux", 8), ("windows", 4), ("macos", 4)):
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
        self.assertEqual(RELEASE.count("          - task:"), 19)

    def test_modulo_shards_cover_each_candidate_once(self):
        for candidate_count, shard_count in ((23, 8), (17, 4), (9, 4)):
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
        self.assertIn(
            'selected_manifest="${RUNNER_TEMP}/${{ matrix.task }}-selected.txt"',
            RELEASE,
        )
        self.assertIn('xargs -r -d \'\\n\' -P "$(nproc)" -n 1 bash -c \'', RELEASE)
        self.assertIn("bash -c '\n              set -o pipefail", RELEASE)
        self.assertIn('cp "$archive" "${{ github.workspace }}/x-tools/$name"', RELEASE)
        self.assertIn('gzip -dc "$archive" | brotli -q 11', RELEASE)
        self.assertNotIn("jlumbroso/free-disk-space", RELEASE)
        self.assertIn("compression-level: 0", RELEASE)
        self.assertIn("pattern: release-assets-*", RELEASE)
        self.assertIn("merge-multiple: true", RELEASE)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
```

Expected: matrix and sharding tests fail because the release still has five unsharded rows and release-side OS packaging.

- [ ] **Step 3: Replace the matrix with the exact 19 rows**

Replace `matrix.include` with:

```yaml
        include:
          - task: linux-target-0
            kind: target
            platform: linux
            artifact: release-linux
            shard: 0
            shard_count: 8
          - task: linux-target-1
            kind: target
            platform: linux
            artifact: release-linux
            shard: 1
            shard_count: 8
          - task: linux-target-2
            kind: target
            platform: linux
            artifact: release-linux
            shard: 2
            shard_count: 8
          - task: linux-target-3
            kind: target
            platform: linux
            artifact: release-linux
            shard: 3
            shard_count: 8
          - task: linux-target-4
            kind: target
            platform: linux
            artifact: release-linux
            shard: 4
            shard_count: 8
          - task: linux-target-5
            kind: target
            platform: linux
            artifact: release-linux
            shard: 5
            shard_count: 8
          - task: linux-target-6
            kind: target
            platform: linux
            artifact: release-linux
            shard: 6
            shard_count: 8
          - task: linux-target-7
            kind: target
            platform: linux
            artifact: release-linux
            shard: 7
            shard_count: 8
          - task: windows-target-0
            kind: target
            platform: windows
            artifact: release-windows
            shard: 0
            shard_count: 4
          - task: windows-target-1
            kind: target
            platform: windows
            artifact: release-windows
            shard: 1
            shard_count: 4
          - task: windows-target-2
            kind: target
            platform: windows
            artifact: release-windows
            shard: 2
            shard_count: 4
          - task: windows-target-3
            kind: target
            platform: windows
            artifact: release-windows
            shard: 3
            shard_count: 4
          - task: macos-target-0
            kind: target
            platform: macos
            artifact: release-macos
            shard: 0
            shard_count: 4
          - task: macos-target-1
            kind: target
            platform: macos
            artifact: release-macos
            shard: 1
            shard_count: 4
          - task: macos-target-2
            kind: target
            platform: macos
            artifact: release-macos
            shard: 2
            shard_count: 4
          - task: macos-target-3
            kind: target
            platform: macos
            artifact: release-macos
            shard: 3
            shard_count: 4
          - task: linux-source
            kind: source
            platform: linux
            artifact: release-linux
          - task: rustc-bins
            kind: rustc
            artifact: rustc-bins
          - task: llvm-bins
            kind: llvm
```

Delete the `free space` step. Change Rust artifact download to `if: ${{ matrix.kind != 'llvm' }}`, LLVM download to `if: ${{ matrix.kind == 'llvm' }}`, and plain tar extraction to `if: ${{ matrix.kind == 'rustc' || matrix.kind == 'llvm' }}` so both wrapped bin artifacts are unpacked.

- [ ] **Step 4: Replace OS packaging with deterministic target sharding**

At the start of `create release assets`, retain `mkdir -p x-tools` and replace the old Linux, Windows, and macOS branches with:

```bash
          if [ "${{ matrix.kind }}" = "target" ]; then
            release_dir="${{ github.workspace }}/artifacts/${{ matrix.artifact }}"
            if [ ! -d "$release_dir" ]; then
              echo "${{ matrix.artifact }} artifact is missing"
              exit 1
            fi

            raw_manifest="${RUNNER_TEMP}/${{ matrix.task }}-raw.tsv"
            manifest="${RUNNER_TEMP}/${{ matrix.task }}.tsv"
            selected_manifest="${RUNNER_TEMP}/${{ matrix.task }}-selected.txt"
            find "$release_dir" -maxdepth 1 -type f -name '*.tar.gz' \
              -printf '%s\t%f\n' > "$raw_manifest"
            if [ "${{ matrix.platform }}" = "linux" ]; then
              awk -F '\t' '$2 != "rust-src.tar.gz" && $2 != "rustc-src.tar.gz"' \
                "$raw_manifest" > "${raw_manifest}.targets"
              mv "${raw_manifest}.targets" "$raw_manifest"
            fi
            LC_ALL=C sort -t $'\t' -k1,1nr -k2,2 "$raw_manifest" > "$manifest"

            candidate_count=$(wc -l < "$manifest")
            shard=${{ matrix.shard }}
            shard_count=${{ matrix.shard_count }}
            if [ "$candidate_count" -lt "$shard_count" ]; then
              echo "${{ matrix.artifact }} has fewer targets than shards"
              exit 1
            fi

            index=0
            assigned=0
            : > "$selected_manifest"
            while IFS=$'\t' read -r size name; do
              if [ $((index % shard_count)) -eq "$shard" ]; then
                printf '%s\n' "$name" >> "$selected_manifest"
                assigned=$((assigned + 1))
              fi
              index=$((index + 1))
            done < "$manifest"
            if [ "$assigned" -eq 0 ]; then
              echo "${{ matrix.task }} received no target archives"
              exit 1
            fi

            xargs -r -d '\n' -P "$(nproc)" -n 1 bash -c '
              set -o pipefail
              set -e
              release_dir="$1"
              name="$2"
              archive="$release_dir/$name"
              cp "$archive" "${{ github.workspace }}/x-tools/$name"
              gzip -dc "$archive" | brotli -q 11 > \
                "${{ github.workspace }}/x-tools/${name%.tar.gz}.tar.br"
              echo "${name%.tar.gz} done"
            ' _ "$release_dir" < "$selected_manifest"
          fi
```

The tab-separated manifest is deterministic by descending byte size and ascending filename. Do not replace it with size-only sorting. Run `33234711624` showed that 6 Linux shards still handled 4-5 archives sequentially, each taking about 3-5.5 minutes, and 5 jobs exceeded 900 seconds. The 8-shard matrix reduces assigned work, while GNU xargs `-P "$(nproc)"` converts each shard's selected manifest concurrently. Every child enables `pipefail` and `-e`, so copy, gzip, or Brotli failures remain fatal.

- [ ] **Step 5: Add the dedicated Linux source branch**

Immediately after the target branch, add:

```bash
          if [ "${{ matrix.kind }}" = "source" ]; then
            release_dir="${{ github.workspace }}/artifacts/release-linux"
            archive="$release_dir/rust-src.tar.gz"
            if [ ! -f "$archive" ]; then
              echo "release-linux artifact is missing rust-src.tar.gz"
              exit 1
            fi
            cp "$archive" "${{ github.workspace }}/x-tools/rust-src.tar.gz"
            gzip -dc "$archive" | brotli -q 11 > \
              "${{ github.workspace }}/x-tools/rust-src.tar.br"

            archive="$release_dir/rustc-src.tar.gz"
            if [ -f "$archive" ]; then
              cp "$archive" "${{ github.workspace }}/x-tools/rustc-src.tar.gz"
              gzip -dc "$archive" | brotli -q 11 > \
                "${{ github.workspace }}/x-tools/rustc-src.tar.br"
            fi
            echo "rust sources done"
          fi
```

Keep the rustc-bins and llvm-bins branch bodies unchanged. Change their opening conditions to `if [ "${{ matrix.kind }}" = "rustc" ]; then` and `if [ "${{ matrix.kind }}" = "llvm" ]; then` respectively.

- [ ] **Step 6: Make partial artifacts unique and uncompressed**

Keep the partial artifact name `release-assets-${{ matrix.task }}`, change `if-no-files-found` to `error`, and add:

```yaml
          compression-level: 0
```

Do not change the publish job's `pattern`, `merge-multiple`, asset glob, tag, or prerelease settings.

- [ ] **Step 7: Verify GREEN and lint both workflows**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 .github/workflows/create_release.yml
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 .github/workflows/rustc_llvm_with_lld.yml .github/workflows/create_release.yml
git diff --check
```

Expected: all Python contracts pass; `create_release.yml` has no actionlint diagnostics; the combined lint reports only the pre-existing `actions/setup-java@v3` diagnostic; whitespace check is silent.

- [ ] **Step 8: Commit the release sharding change**

```bash
git add tests/test_release_rust_src_contract.py .github/workflows/create_release.yml
git commit -m "feat: shard release asset compression"
```

---

### Task 3: Build One Complete Producer Artifact Set

**Files:**
- Update without committing: `/home/oligami/projects/rust_wasm/.git/worktrees/browser-rust-std-artifacts/sdd/parallel-producer-report.md`

**Interfaces:**
- Consumes: tested Task 1 and Task 2 commits on `feat/browser-rust-std-artifacts`.
- Produces: one successful producer run containing all existing Rust artifacts plus `release-linux`, `release-windows`, and `release-macos`.

- [ ] **Step 1: Inspect and push only the feature branch**

Run:

```bash
git status --short --branch
git diff --check
git log --oneline -10
git push origin feat/browser-rust-std-artifacts
```

Expected: non-forced push succeeds, `origin/main` is unchanged, and `tests/__pycache__/` remains untracked and untouched.

- [ ] **Step 2: Dispatch exactly one complete producer run**

```bash
gh workflow run rustc_llvm_with_lld.yml \
  --ref feat/browser-rust-std-artifacts \
  -f job=all
```

Capture the newest run and verify its head SHA equals local HEAD. Record the ID before waiting.

- [ ] **Step 3: Wait for the exact producer run**

```bash
gh run watch "$PRODUCER_RUN_ID" --exit-status --interval 60
```

Expected: every producer job succeeds. On failure, record job ID, failed step, annotations, and URL in `parallel-producer-report.md`, then stop without rerun.

- [ ] **Step 4: Verify the artifact contract**

Use the exact run ID:

```bash
ARTIFACTS=$(gh api "repos/oligamiq/rust_wasm/actions/runs/$PRODUCER_RUN_ID/artifacts" \
  --paginate --jq '[.artifacts[] | select(.expired == false) | .name]')
jq -n --argjson actual "$ARTIFACTS" '
  ["dist-linux", "dist-macos", "dist-windows", "rustc-bins",
   "release-linux", "release-windows", "release-macos"] - $actual
  | if length == 0 then "parallel producer artifact contract passed"
    else error("missing artifacts: \(.)") end
'
```

Expected: `parallel producer artifact contract passed`.

- [ ] **Step 5: Record producer evidence**

Write run ID, head SHA, URL, all job conclusions, artifact names/sizes/expiry, and exact contract output to `sdd/parallel-producer-report.md`. Do not commit the report.

---

### Task 4: Publish v0.2.1 And Enforce The Fifteen-Minute Budget

**Files:**
- Update without committing: `/home/oligami/projects/rubrc/.git/worktrees/browser-rust-std/sdd/task-2-report.md`

**Interfaces:**
- Consumes: the exact successful producer run from Task 3.
- Produces: `v0.2.1-release`, 19 successful package jobs each under 900 seconds, successful Pages deployment, and public library-relative `rust-src.tar.br`.

- [ ] **Step 1: Dispatch one release from the exact producer run**

Read `parallel-producer-report.md`, verify the run contains all three `release-*` OS artifacts, then run:

```bash
gh workflow run create_release.yml \
  --ref feat/browser-rust-std-artifacts \
  -f version=v0.2.1 \
  -f build_run_id="$PRODUCER_RUN_ID"
```

Capture the new release run ID and confirm its head SHA is the Task 2 commit.

- [ ] **Step 2: Wait for the exact release run**

```bash
gh run watch "$RELEASE_RUN_ID" --exit-status --interval 30
```

Expected: all 19 package jobs and publish succeed. On failure, record diagnosis and stop without rerun.

- [ ] **Step 3: Enforce package job count and duration**

Run:

```bash
gh api "repos/oligamiq/rust_wasm/actions/runs/$RELEASE_RUN_ID/jobs" --paginate --jq '
  [.jobs[]
   | select(.name | startswith("package ("))
   | {name,
      duration_seconds: ((.completed_at | fromdateiso8601)
                         - (.started_at | fromdateiso8601))}]
  | if length != 19 then error("expected 19 package jobs, got \(length)")
    elif all(.duration_seconds < 900) then .
    else error("package duration budget failed: \([.[] | select(.duration_seconds >= 900)])")
    end
'
```

Expected: a 19-entry array and exit 0; every `duration_seconds` is below 900.

- [ ] **Step 4: Verify the public release asset contract**

```bash
OLD_TARGETS=$(gh release view v0.2.0-release --json assets \
  --jq '[.assets[].name | select(endswith(".tar.br") and (endswith(".wasm.tar.br") | not))]')
NEW_ASSETS=$(gh release view v0.2.1-release --json assets --jq '[.assets[].name]')
jq -n --argjson old_targets "$OLD_TARGETS" --argjson new "$NEW_ASSETS" '
  ($old_targets - $new) as $missing
  | if ($missing | length) == 0
    and ($new | index("rust-src.tar.br")) != null
    and ($new | index("rust-src.tar.gz")) != null
    and ($new | index("rustc_opt.wasm.br")) != null
    and ($new | index("llvm_opt.wasm.br")) != null
    then "release asset contract passed"
    else error("missing release assets: \($missing)")
    end
'
```

Expected: `release asset contract passed`.

- [ ] **Step 5: Verify Pages and the public source archive**

Wait for the Pages workflow triggered by this release, then run:

```bash
curl --fail --silent --show-error \
  "https://oligamiq.github.io/rust_wasm/v0.2.1/rust-src.tar.br" \
  | brotli --decompress \
  | tar --list --file - core/src/lib.rs alloc/src/lib.rs std/src/lib.rs
```

Expected:

```text
core/src/lib.rs
alloc/src/lib.rs
std/src/lib.rs
```

- [ ] **Step 6: Record final release evidence**

Update `/home/oligami/projects/rubrc/.git/worktrees/browser-rust-std/sdd/task-2-report.md` with producer, release, all 19 package durations, asset contract, Pages run, and public archive evidence. Do not commit the report. Confirm both worktrees have no unexpected tracked changes and do not touch `tests/__pycache__/`.
