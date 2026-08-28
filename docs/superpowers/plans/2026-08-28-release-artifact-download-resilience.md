# Release Artifact Download Resilience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the complete `v0.2.1` release by replacing the repeatedly failing large cross-run CLI artifact transfer with GitHub's official artifact action.

**Architecture:** Keep producer run `33114125096` and every release packaging branch unchanged. Map each Rust matrix task to its artifact declaratively and download it with `actions/download-artifact@v4` from the explicit producer run; keep the independent LLVM lookup in its existing shell path.

**Tech Stack:** GitHub Actions YAML, `actions/download-artifact@v4`, Python `unittest`, actionlint, GitHub CLI.

## Global Constraints

- Preserve all existing Linux, Windows, macOS, rustc-bins, and LLVM release assets.
- Linux, Windows, macOS, and rustc-bins must come from producer run `33114125096`.
- LLVM continues to come from the latest successful `build_llvm.yml` run.
- Reuse producer run `33114125096`; do not rebuild Rust artifacts.
- Keep `contents: write` and add only the `actions: read` permission required for explicit cross-run artifact access.
- Do not add commit-hash, archive-digest, or embedded-rustc identity verification.
- Do not change release archive names, archive layouts, release tag naming, or Pages URLs.
- Push only `feat/browser-rust-std-artifacts`; do not modify or push `main`.
- If the official action loses the Windows transfer at the same boundary, stop rather than adding another retry layer.

---

### Task 1: Replace Rust Artifact CLI Downloads

**Files:**
- Modify: `tests/test_release_rust_src_contract.py:28-31`
- Modify: `.github/workflows/create_release.yml:14-83`

**Interfaces:**
- Consumes: workflow input `${{ github.event.inputs.build_run_id }}` and the existing artifact names from `rustc_llvm_with_lld.yml`.
- Produces: matrix fields `matrix.task` and `matrix.artifact`; Rust artifacts extracted under `artifacts/${{ matrix.artifact }}` for the unchanged packaging step.

- [ ] **Step 1: Replace the explicit-run contract with a failing action contract**

Replace `test_release_uses_one_explicit_build_run` with:

```python
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
            ("windows", "dist-windows"),
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
```

- [ ] **Step 2: Run the contract to verify RED**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
```

Expected: FAIL in `test_release_uses_one_explicit_build_run` because the workflow does not contain `actions: read` or `run-id: ${{ github.event.inputs.build_run_id }}`.

- [ ] **Step 3: Grant explicit artifact read access**

Change the workflow permissions to:

```yaml
permissions:
  actions: read
  contents: write
```

- [ ] **Step 4: Make the matrix map tasks to producer artifacts**

Replace the scalar `matrix.task` list with:

```yaml
    strategy:
      fail-fast: false
      matrix:
        include:
          - task: linux
            artifact: dist-linux
          - task: windows
            artifact: dist-windows
          - task: macos
            artifact: dist-macos
          - task: rustc-bins
            artifact: rustc-bins
          - task: llvm-bins
```

- [ ] **Step 5: Replace only the Rust artifact transfer path**

Replace the existing `download artifacts` shell step with these three steps:

```yaml
      - name: download Rust artifact
        if: ${{ matrix.task != 'llvm-bins' }}
        uses: actions/download-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: artifacts/${{ matrix.artifact }}
          github-token: ${{ github.token }}
          repository: ${{ github.repository }}
          run-id: ${{ github.event.inputs.build_run_id }}

      - name: download LLVM artifacts
        if: ${{ matrix.task == 'llvm-bins' }}
        env:
          GITHUB_TOKEN: ${{ github.token }}
          GH_REPO: ${{ github.repository }}
        run: |
          mkdir -p artifacts
          RUN_ID_LLVM=$(gh run list --workflow build_llvm.yml --status success --limit 1 --json databaseId --jq '.[0].databaseId')
          if [ "$RUN_ID_LLVM" != "null" ] && [ -n "$RUN_ID_LLVM" ]; then
            gh run download "$RUN_ID_LLVM" --name llvm-bins --dir artifacts/llvm-bins || echo "llvm-bins not found"
          fi

      - name: extract downloaded artifacts
        run: |
          for f in artifacts/*/*.tar; do
            if [ -f "$f" ]; then
              dir=$(dirname "$f")
              tar -xf "$f" -C "$dir"
              rm "$f"
            fi
          done
```

Do not change the `create release assets`, `upload partial assets`, or `publish` steps.

- [ ] **Step 6: Run the focused contract and syntax checks**

Run:

```bash
python3 -m unittest tests.test_release_rust_src_contract -v
```

Expected: PASS, 4 tests and 0 failures.

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

- [ ] **Step 7: Confirm the known unrelated actionlint baseline remains isolated**

Run:

```bash
go run github.com/rhysd/actionlint/cmd/actionlint@v1.7.7 .github/workflows/rustc_llvm_with_lld.yml .github/workflows/create_release.yml
```

Expected: the only diagnostic is the pre-existing `.github/workflows/rustc_llvm_with_lld.yml:436:15` `actions/setup-java@v3` runner-age diagnostic. No diagnostic may reference `create_release.yml`.

- [ ] **Step 8: Commit the tested workflow fix**

```bash
git add tests/test_release_rust_src_contract.py .github/workflows/create_release.yml
git commit -m "fix: use resilient release artifact downloads"
```

---

### Task 2: Publish And Verify The Replacement Release Run

**Files:**
- No source files change.
- Update operational evidence outside the repository at `/home/oligami/projects/rubrc/.git/worktrees/browser-rust-std/sdd/task-2-report.md`.

**Interfaces:**
- Consumes: Task 1's committed workflow and producer run `33114125096`.
- Produces: release tag `v0.2.1-release`, successful GitHub Pages deployment, and reachable `v0.2.1/rust-src.tar.br`.

- [ ] **Step 1: Inspect and push only the feature branch**

Run:

```bash
git status --short --branch
git diff --check
git log --oneline -10
git push origin feat/browser-rust-std-artifacts
```

Expected: only the known untracked `tests/__pycache__/` may remain; the feature branch push succeeds; `main` is untouched.

- [ ] **Step 2: Dispatch a new release run using the existing producer**

Run:

```bash
gh workflow run create_release.yml \
  --ref feat/browser-rust-std-artifacts \
  -f version=v0.2.1 \
  -f build_run_id=33114125096
```

Then capture and inspect the latest run:

```bash
NEW_RUN_ID=""
for attempt in $(seq 1 30); do
  NEW_RUN_ID="$(gh run list \
    --workflow create_release.yml \
    --branch feat/browser-rust-std-artifacts \
    --event workflow_dispatch \
    --limit 1 \
    --json databaseId \
    --jq '.[0].databaseId')"
  if [ -n "$NEW_RUN_ID" ] && [ "$NEW_RUN_ID" != "33131839606" ]; then
    break
  fi
  sleep 2
done
test "$NEW_RUN_ID" != "33131839606"
gh run view "$NEW_RUN_ID" --json databaseId,status,conclusion,url,headSha,createdAt
```

Expected: a new run ID different from failed run `33131839606`, with the Task 1 workflow-fix commit as `headSha`.

- [ ] **Step 3: Wait for the exact replacement run**

Run:

```bash
NEW_RUN_ID="$(gh run list \
  --workflow create_release.yml \
  --branch feat/browser-rust-std-artifacts \
  --event workflow_dispatch \
  --limit 1 \
  --json databaseId \
  --jq '.[0].databaseId')"
gh run watch "$NEW_RUN_ID" --exit-status --interval 60
```

Expected: all five package jobs and `publish` succeed. If Windows again loses communication during `download Rust artifact`, record the evidence and stop; do not rerun or add another transfer retry.

- [ ] **Step 4: Verify the release retained prior assets and added rust-src**

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
    and ($new | index("rustc_opt.wasm.tar.gz")) != null
    and ($new | index("llvm_opt.wasm.br")) != null
    and ($new | index("llvm_opt.wasm.tar.gz")) != null
    then "release asset contract passed"
    else error("missing release assets: \($missing)")
    end
'
```

Expected: `release asset contract passed` and exit 0.

- [ ] **Step 5: Wait for the Pages deployment triggered by the successful release**

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
gh run view "$PAGES_RUN_ID" --json databaseId,status,conclusion,url,createdAt
gh run watch "$PAGES_RUN_ID" --exit-status --interval 30
```

Expected: the Pages run created after the replacement release succeeds.

- [ ] **Step 6: Verify the public library-relative rust-src archive**

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

- [ ] **Step 7: Record operational evidence and inspect repository state**

Record the replacement release run ID, Pages run ID, release asset contract output, archive structure output, and URLs in `/home/oligami/projects/rubrc/.git/worktrees/browser-rust-std/sdd/task-2-report.md`.

Run:

```bash
git status --short --branch
git diff --check
```

Expected: no tracked changes and no whitespace errors; do not stage or delete the known generated `tests/__pycache__/` path.
