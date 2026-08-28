# Windows Release-Ready Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate release-runner expansion of the monolithic Windows artifact by creating target archives in the Windows producer job.

**Architecture:** The Windows producer continues uploading `dist-windows` and additionally uploads precompressed per-target `.tar.gz` files as `release-windows`. The release consumes `release-windows`, copies each gzip archive unchanged, and streams its tar bytes through Brotli without expanding target members on disk.

**Tech Stack:** GitHub Actions YAML, GNU tar/gzip/Brotli, `actions/upload-artifact@v4`, `actions/download-artifact@v4`, Python `unittest`, actionlint, GitHub CLI.

## Global Constraints

- Preserve the existing `dist-windows` artifact and all public Windows target `.tar.gz` and `.tar.br` names and member layouts.
- Preserve Linux, macOS, rustc-bins, LLVM, and rust-src packaging behavior.
- Every Rust artifact used by the release must come from one new successful `job=all` producer run using `RUST_SOURCE_REF: cf327c2068549194a29160499c2ecafa9061e46e`.
- Do not mix `release-windows` from a new run with Linux, macOS, or rustc-bins from producer run `33114125096`.
- Do not add commit-hash, archive-digest, or embedded-rustc identity verification.
- Do not add another retry layer around download or extraction.
- Push and dispatch only `feat/browser-rust-std-artifacts`; do not modify or push `main`.
- Stop if the producer or replacement release fails; do not rerun a failed workflow without a new diagnosis.

---

### Task 1: Produce And Consume Release-Ready Windows Archives

**Files:**
- Modify: `tests/test_release_rust_src_contract.py`
- Modify: `.github/workflows/rustc_llvm_with_lld.yml:860-882`
- Modify: `.github/workflows/create_release.yml:26-35,131-145`

**Interfaces:**
- Consumes: Windows producer directory `dist-artifacts/dist/lib/rustlib/${target}/lib`.
- Produces: producer artifact `release-windows` containing `${target}.tar.gz`; release assets `${target}.tar.gz` and `${target}.tar.br` with target library members at archive root.

- [ ] **Step 1: Write failing producer and release contracts**

In `test_release_uses_one_explicit_build_run`, change the Windows mapping from `dist-windows` to `release-windows`:

```python
            ("windows", "release-windows"),
```

Add this test before `test_release_uses_one_explicit_build_run`:

```python
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
```

- [ ] **Step 2: Run the contract to verify RED**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
```

Expected: 5 tests run and at least `test_windows_release_archives_are_prepared_in_the_producer` fails because `release-windows` is absent.

- [ ] **Step 3: Create per-target gzip archives in the Windows producer**

In the Windows `prepare dist artifacts` step, insert this block after `mv ../rust/dist dist-artifacts/dist` and `rm -rf dist-artifacts/dist/bin`, before creating `dist-windows.tar`:

```bash
          release_dir="${WS_FORWARD}/rust_wasm/release-windows"
          mkdir -p "$release_dir"
          for target_dir in dist-artifacts/dist/lib/rustlib/*; do
            if [ -d "$target_dir/lib" ]; then
              target=$(basename "$target_dir")
              (
                cd "$target_dir/lib"
                tar --force-local --ignore-failed-read -chzf "$release_dir/${target}.tar.gz" *
              )
              echo "$target release archive done"
            fi
          done
```

Keep the existing creation and upload of `dist-windows.tar` unchanged.

- [ ] **Step 4: Upload the small release-ready file set without recompression**

Add this step immediately after the existing Windows `upload dist artifacts` step:

```yaml
      - name: upload release-ready windows artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-windows
          path: ${{ github.workspace }}/rust_wasm/release-windows/*.tar.gz
          if-no-files-found: error
          compression-level: 0
```

- [ ] **Step 5: Make the release download the prepared Windows artifact**

Change only the Windows matrix entry in `create_release.yml`:

```yaml
          - task: windows
            artifact: release-windows
```

- [ ] **Step 6: Replace release-side Windows expansion and repackaging**

Replace the entire `matrix.task == windows` branch under `create release assets` with:

```bash
          if [ "${{ matrix.task }}" = "windows" ]; then
            release_dir="${{ github.workspace }}/artifacts/release-windows"
            if [ ! -d "$release_dir" ]; then
              echo "release-windows artifact is missing"
              exit 1
            fi
            for archive in "$release_dir"/*.tar.gz; do
              if [ ! -f "$archive" ]; then
                echo "release-windows artifact contains no target archives"
                exit 1
              fi
              name=$(basename "$archive")
              cp "$archive" "${{ github.workspace }}/x-tools/$name"
              gzip -dc "$archive" | brotli -q 11 > "${{ github.workspace }}/x-tools/${name%.tar.gz}.tar.br"
              echo "${name%.tar.gz} done"
            done
          fi
```

- [ ] **Step 7: Run focused verification**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
```

Expected: PASS, 5 tests and 0 failures.

Run:

```bash
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 .github/workflows/create_release.yml
```

Expected: exit 0 with no diagnostics.

Run:

```bash
git diff --check
```

Expected: exit 0 with no output.

- [ ] **Step 8: Confirm the unrelated actionlint baseline**

Run:

```bash
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 .github/workflows/rustc_llvm_with_lld.yml .github/workflows/create_release.yml
```

Expected: the only diagnostic is `.github/workflows/rustc_llvm_with_lld.yml:436:15` for pre-existing `actions/setup-java@v3`; no diagnostic references the changed Windows producer or release blocks.

- [ ] **Step 9: Commit the tested fallback**

```bash
git add tests/test_release_rust_src_contract.py .github/workflows/rustc_llvm_with_lld.yml .github/workflows/create_release.yml
git commit -m "fix: prepackage windows release artifacts"
```

---

### Task 2: Build A New Complete Producer Artifact Set

**Files:**
- No source files change.
- Record evidence in `/home/oligami/projects/rust_wasm/.git/worktrees/browser-rust-std-artifacts/sdd/windows-producer-report.md`.

**Interfaces:**
- Consumes: Task 1 workflow commit on `feat/browser-rust-std-artifacts`.
- Produces: one successful `rustc_llvm_with_lld.yml` run containing `dist-linux`, `dist-macos`, `dist-windows`, `rustc-bins`, and `release-windows`.

- [ ] **Step 1: Inspect and push the feature branch**

Run:

```bash
git status --short --branch
git diff --check
git log --oneline -10
git push origin feat/browser-rust-std-artifacts
```

Expected: push succeeds without force and `origin/main` is untouched. Do not stage or delete `tests/__pycache__/`.

- [ ] **Step 2: Dispatch exactly one complete producer run**

Run:

```bash
gh workflow run rustc_llvm_with_lld.yml \
  --ref feat/browser-rust-std-artifacts \
  -f job=all
```

Capture the new run deterministically:

```bash
PRODUCER_RUN_ID=""
for attempt in $(seq 1 30); do
  PRODUCER_RUN_ID="$(gh run list \
    --workflow rustc_llvm_with_lld.yml \
    --branch feat/browser-rust-std-artifacts \
    --event workflow_dispatch \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId')"
  if [ -n "$PRODUCER_RUN_ID" ] && [ "$PRODUCER_RUN_ID" != "33114125096" ]; then
    break
  fi
  sleep 2
done
test -n "$PRODUCER_RUN_ID"
test "$PRODUCER_RUN_ID" != "33114125096"
gh run view "$PRODUCER_RUN_ID" --json databaseId,status,conclusion,url,headSha,createdAt
```

Expected: the run head SHA is Task 1's fallback commit and status is queued or in progress.

- [ ] **Step 3: Wait for that exact producer run**

Run:

```bash
PRODUCER_RUN_ID="$(gh run list \
  --workflow rustc_llvm_with_lld.yml \
  --branch feat/browser-rust-std-artifacts \
  --event workflow_dispatch \
  --limit 1 \
  --json databaseId \
  --jq '.[0].databaseId')"
gh run watch "$PRODUCER_RUN_ID" --exit-status --interval 60
```

Expected: all producer jobs succeed. If any job fails, record its job ID, failed step, annotation, and URL, then stop without rerun.

- [ ] **Step 4: Verify the complete artifact set**

Run:

```bash
PRODUCER_RUN_ID="$(gh run list \
  --workflow rustc_llvm_with_lld.yml \
  --branch feat/browser-rust-std-artifacts \
  --event workflow_dispatch \
  --limit 1 \
  --json databaseId \
  --jq '.[0].databaseId')"
ARTIFACTS=$(gh api "repos/oligamiq/rust_wasm/actions/runs/$PRODUCER_RUN_ID/artifacts" --paginate --jq '[.artifacts[].name]')
jq -n --argjson actual "$ARTIFACTS" '
  ["dist-linux", "dist-macos", "dist-windows", "rustc-bins", "release-windows"] - $actual
  | if length == 0 then "producer artifact contract passed" else error("missing artifacts: \(.)") end
'
```

Expected: `producer artifact contract passed` and exit 0.

- [ ] **Step 5: Record producer evidence**

Write the producer run ID, head SHA, URL, job conclusions, and artifact contract output to `sdd/windows-producer-report.md`. Do not commit this report.

---

### Task 3: Publish And Verify v0.2.1 From The New Producer

**Files:**
- No source files change.
- Update `/home/oligami/projects/rubrc/.git/worktrees/browser-rust-std/sdd/task-2-report.md`.

**Interfaces:**
- Consumes: Task 2's exact successful producer run ID.
- Produces: `v0.2.1-release`, successful Pages deployment, and public library-relative `rust-src.tar.br`.

- [ ] **Step 1: Dispatch the release from the exact new producer run**

Read `sdd/windows-producer-report.md`, then resolve the latest successful complete producer run and confirm it contains `release-windows` before dispatch:

```bash
PRODUCER_RUN_ID="$(gh run list \
  --workflow rustc_llvm_with_lld.yml \
  --branch feat/browser-rust-std-artifacts \
  --event workflow_dispatch \
  --status success \
  --limit 1 \
  --json databaseId \
  --jq '.[0].databaseId')"
test -n "$PRODUCER_RUN_ID"
test "$(gh api "repos/oligamiq/rust_wasm/actions/runs/$PRODUCER_RUN_ID/artifacts" \
  --paginate \
  --jq '[.artifacts[].name | select(. == "release-windows")] | length')" = "1"
gh workflow run create_release.yml \
  --ref feat/browser-rust-std-artifacts \
  -f version=v0.2.1 \
  -f build_run_id="$PRODUCER_RUN_ID"
```

Expected: `PRODUCER_RUN_ID` equals the ID recorded in Task 2's report and the dispatch succeeds.

- [ ] **Step 2: Capture and wait for the replacement release**

Run:

```bash
RELEASE_RUN_ID=""
for attempt in $(seq 1 30); do
  RELEASE_RUN_ID="$(gh run list \
    --workflow create_release.yml \
    --branch feat/browser-rust-std-artifacts \
    --event workflow_dispatch \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId')"
  if [ -n "$RELEASE_RUN_ID" ] && [ "$RELEASE_RUN_ID" != "33146231174" ]; then
    break
  fi
  sleep 2
done
test -n "$RELEASE_RUN_ID"
test "$RELEASE_RUN_ID" != "33146231174"
gh run watch "$RELEASE_RUN_ID" --exit-status --interval 60
```

Expected: all package jobs and `publish` succeed. Windows downloads `release-windows`, skips monolithic tar extraction, and creates both gzip and Brotli assets.

- [ ] **Step 3: Verify release assets**

Run:

```bash
OLD_TARGETS=$(gh release view v0.2.0-release --json assets --jq '[.assets[].name | select(endswith(".tar.br") and (endswith(".wasm.tar.br") | not))]')
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

Expected: `release asset contract passed` and exit 0.

- [ ] **Step 4: Wait for GitHub Pages**

Run:

```bash
PAGES_RUN_ID=""
for attempt in $(seq 1 60); do
  PAGES_RUN_ID="$(gh run list \
    --workflow deploy_pages.yml \
    --event workflow_run \
    --branch feat/browser-rust-std-artifacts \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId')"
  if [ -n "$PAGES_RUN_ID" ]; then
    break
  fi
  sleep 5
done
test -n "$PAGES_RUN_ID"
gh run watch "$PAGES_RUN_ID" --exit-status --interval 30
```

Expected: Pages deployment succeeds.

- [ ] **Step 5: Verify the public rust-src archive**

Run:

```bash
curl --fail --silent --show-error "https://oligamiq.github.io/rust_wasm/v0.2.1/rust-src.tar.br" \
  | brotli --decompress \
  | tar --list --file - core/src/lib.rs alloc/src/lib.rs std/src/lib.rs
```

Expected output:

```text
core/src/lib.rs
alloc/src/lib.rs
std/src/lib.rs
```

- [ ] **Step 6: Record evidence and inspect state**

Record producer, release, Pages, release asset, and public archive evidence in `/home/oligami/projects/rubrc/.git/worktrees/browser-rust-std/sdd/task-2-report.md`.

Run:

```bash
git status --short --branch
git diff --check
```

Expected: no tracked changes and no whitespace errors; do not stage or delete `tests/__pycache__/`.
