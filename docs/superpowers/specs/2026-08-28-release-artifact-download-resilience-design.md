# Release Artifact Download Resilience Design

## Context

The `v0.2.1` release workflow consumes the complete artifact set from producer run `33114125096`. The producer succeeded and uploaded all required artifacts from Rust source ref `cf327c2068549194a29160499c2ecafa9061e46e`.

Release run `33131839606` failed twice while `gh run download` fetched the 6.5 GB `dist-windows` artifact. Both attempts used different hosted runners and ended after about one hour with the GitHub annotation `The hosted runner lost communication with the server.` Linux, macOS, rustc-bins, and LLVM packaging succeeded. The repeated failure isolates the problem to the large cross-run Windows artifact transfer rather than producer completeness or release packaging commands.

## Requirements

- Preserve all existing Linux, Windows, macOS, rustc-bins, and LLVM release assets.
- Continue consuming Linux, Windows, macOS, and rustc-bins from one explicit successful `rustc_llvm_with_lld.yml` run.
- Continue using the independent latest successful `build_llvm.yml` run for LLVM assets.
- Grant the release workflow `actions: read` permission for explicit cross-run artifact access while retaining `contents: write` for release publication.
- Reuse producer run `33114125096`; do not rebuild Rust artifacts for this fix.
- Do not add commit-hash, archive-digest, or embedded-rustc identity verification.
- Do not change release asset layouts or downstream Pages URLs.

## Approaches Considered

### Official Cross-Run Artifact Action

Use `actions/download-artifact@v4` with `run-id`, `repository`, `name`, `path`, and `github-token` for the four Rust producer artifacts. This retains the explicit-run contract while replacing the failing CLI transfer with GitHub's supported artifact action. It is the smallest change and is the selected approach.

### Custom Resumable REST Download

Resolve artifact IDs through the GitHub REST API and download with `curl` retries and resume support. This offers transfer control but introduces signed redirect URL expiry, range handling, and partial-file integrity concerns into the workflow.

### Producer-Side Release-Ready Artifacts

Create target-specific release archives in each producer job and upload them separately. This avoids monolithic downstream transfers but requires substantial producer changes and another multi-hour complete build. It remains the fallback if the official action fails at the same boundary.

## Design

Split the current `download artifacts` shell step into two paths:

- Linux, Windows, macOS, and rustc-bins use `actions/download-artifact@v4` directly.
- LLVM retains its existing shell lookup and `gh run download` because it intentionally comes from a separate workflow run.

The Rust artifact action receives:

- `run-id: ${{ github.event.inputs.build_run_id }}`
- `name`: the matrix task's existing artifact name
- `path`: the existing `artifacts/<artifact-name>` destination
- `github-token: ${{ github.token }}`
- `repository: ${{ github.repository }}`

The workflow permissions explicitly include `actions: read` and retain `contents: write`.

Replace the scalar task list with matrix include entries that map `linux` to `dist-linux`, `windows` to `dist-windows`, `macos` to `dist-macos`, and `rustc-bins` to `rustc-bins`; the LLVM entry has no Rust artifact name. The action runs only when `matrix.task != 'llvm-bins'`. The existing extraction loop and every packaging branch remain unchanged, so downstream archive names and layouts do not change.

## Error Handling

The official action must fail the matrix job if the named artifact cannot be downloaded. No `continue-on-error`, fallback URL, alternate producer run, or silent skip is permitted for Rust artifacts. This preserves the complete-release requirement.

If a release run using the official action again loses the Windows transfer at the same boundary, stop retrying and design the producer-side release-ready artifact approach. Do not add layers of shell retries around the action.

## Testing

Extend `tests/test_release_rust_src_contract.py` before changing the workflow. The contract must prove that:

- Rust artifact downloads use `actions/download-artifact@v4`.
- The action receives the explicit `build_run_id` as `run-id`.
- The action receives `github.token` for cross-run access.
- The action explicitly receives `github.repository` as its source repository.
- The workflow explicitly grants `actions: read` without removing `contents: write`.
- Linux, Windows, macOS, and rustc-bins map to their existing artifact names.
- The old Rust-path `gh run download` command is absent.
- The independent LLVM lookup remains present.

Run the Python contract test and actionlint after implementation. The pre-existing `actions/setup-java@v3` actionlint diagnostic is recorded separately and is outside this transfer fix.

## Rollout And Verification

Commit and push the workflow fix only to `feat/browser-rust-std-artifacts`. Dispatch a new `create_release.yml` run on that branch with `version=v0.2.1` and `build_run_id=33114125096`. Do not reuse failed release run `33131839606`, because reruns use its original workflow definition.

After success, wait for Pages deployment and verify that the public `rust-src.tar.br` lists `core/src/lib.rs`, `alloc/src/lib.rs`, and `std/src/lib.rs`. Then resume Rubrc asset preparation and browser acceptance testing.

## Producer-Side Windows Fallback

The official action fixed the original transfer boundary: replacement release run `33140915641` downloaded `dist-windows` successfully in about nine minutes. The hosted runner then lost communication while expanding the monolithic Windows tar for about 55 minutes. A second run reached the same extraction step. The remaining failure is therefore the monolithic archive expansion, not cross-run transfer.

The fallback removes that expansion from the release workflow:

- The Windows producer job keeps uploading `dist-windows` so the complete producer artifact set remains available.
- Before deleting `dist-artifacts`, the Windows producer creates one `${target}.tar.gz` per `dist/lib/rustlib/${target}/lib` directory. It runs `tar` from inside each `lib` directory with the existing `*` member selection, preserving the current archive-root layout.
- A new `release-windows` artifact uploads only those precompressed archives with `compression-level: 0`. The artifact contains a small number of files rather than the expanded rustlib tree.
- The release matrix maps its Windows task to `release-windows` instead of `dist-windows`.
- The release job copies each producer-created `.tar.gz` unchanged and streams its decompressed tar bytes through `brotli -q 11` to create the matching `.tar.br`. It never expands target members onto the release runner filesystem.
- Linux, macOS, rustc-bins, LLVM, rust-src packaging, archive names, and public layouts remain unchanged.

Because `release-windows` is a new producer artifact, the fallback requires one new `job=all` producer run from the feature branch. The subsequent release must use that exact successful run ID for all four Rust artifact families. Mixing the new Windows artifact with the old producer run is prohibited.

Contract tests must fail before implementation and then prove that the producer creates and uploads `release-windows`, the release consumes it, the streaming conversion is present, and the old release-side `dist-windows` directory traversal is absent. After tests and actionlint, push the feature branch, dispatch one new `job=all` producer run, then dispatch one release run from its exact ID.
