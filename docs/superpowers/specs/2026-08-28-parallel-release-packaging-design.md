# Parallel Release Packaging Design

## Goal

Make every `create_release.yml` package job complete in less than 15 minutes while preserving every public release asset name, archive layout, and compression setting.

The time limit applies individually to Linux, Windows, macOS, rustc-bins, and llvm-bins package work. The publish job is outside this limit.

## Evidence

Run `30205684422` showed that the existing top-level package matrix was already parallel: all five package jobs started at `2026-07-26T14:14:54Z`. The Linux job nevertheless took about 60 minutes, including about 55 minutes in `create release assets`.

Run `33163288955` used the release-ready Windows gzip artifact but still had Linux, Windows, and macOS package jobs running after 18 minutes. Linux and Windows were compressing release assets, while macOS had only recently finished downloading and extracting its 9.5 GB distribution artifact. Increasing only the in-job `xargs -P` value cannot reliably meet the target because each hosted runner has limited CPU and macOS still expands a large intermediate archive.

## Architecture

Move gzip archive creation for all target libraries into the producer workflow, then shard only the CPU-intensive gzip-to-Brotli conversion across release jobs.

The producer creates three release-ready artifacts:

- `release-linux`: Linux target `${target}.tar.gz` files plus `rust-src.tar.gz` and optional `rustc-src.tar.gz`.
- `release-windows`: Windows target `${target}.tar.gz` files.
- `release-macos`: macOS target `${target}.tar.gz` files.

Each target gzip archive contains the target library directory members at archive root, matching the current public release layout. `rust-src.tar.gz` contains the contents of `src/rust/library` at archive root, preserving paths such as `core/src/lib.rs`, `alloc/src/lib.rs`, and `std/src/lib.rs`.

The existing `dist-linux`, `dist-windows`, and `dist-macos` artifacts remain unchanged. The new release-ready artifacts are additional producer outputs and use `compression-level: 0` because their members are already compressed.

## Package Matrix

Replace the three OS-level release jobs with deterministic shards:

- Linux target archives: 6 jobs.
- Windows target archives: 4 jobs.
- macOS target archives: 4 jobs.
- Linux source archives: 1 job.
- rustc-bins: 1 job.
- llvm-bins: 1 job.

This creates 17 package jobs. The release workflow continues to use `fail-fast: false` so one failed shard does not hide evidence from the other shards.

Each target shard downloads its platform's release-ready artifact, sorts target gzip archives by descending byte size, and assigns archive number `n` to shard `n % shard_count`. Sorting by size before round-robin assignment reduces load skew while ensuring every archive is assigned to exactly one shard. Linux target shards exclude `rust-src.tar.gz` and `rustc-src.tar.gz`.

For each assigned archive, the shard:

1. Copies the gzip archive unchanged into `x-tools`.
2. Streams `gzip -dc` into `brotli -q 11` to create the matching `.tar.br` file.
3. Fails if it receives no archive, because an empty shard indicates an invalid shard count or missing producer content.

The Linux source job requires `rust-src.tar.gz`, copies it unchanged, and creates `rust-src.tar.br` through the same stream. It handles `rustc-src.tar.gz` when present.

Every shard uploads a uniquely named `release-assets-*` artifact with `compression-level: 0`. The publish job retains the existing `release-assets-*` pattern with `merge-multiple: true`, so its input and public release action remain unchanged.

## Runtime Changes

OS package jobs no longer download or expand `dist-*` artifacts. They consume only precompressed `release-*` artifacts.

Remove `jlumbroso/free-disk-space` from the release workflow. Release-ready OS shards no longer require space for expanded toolchains. The latest rustc-bins package job completed in 11 minutes 36 seconds including more than three minutes of disk cleanup, so removing that setup also gives rustc-bins sufficient margin under the 15-minute requirement. llvm-bins already completes well under the limit.

Keep Brotli quality 11, public `.tar.gz` and `.tar.br` names, and all archive member layouts unchanged.

## Provenance

All artifacts used by a release must come from one complete successful producer run using `RUST_SOURCE_REF: cf327c2068549194a29160499c2ecafa9061e46e`.

After changing the producer, dispatch one new `job=all` run. Do not combine its release-ready artifacts with `dist-*` or rustc-bins from an older producer run. Dispatch `create_release.yml` only with the exact successful producer run ID recorded by verification.

## Error Handling

Producer jobs fail when a required source directory, target library directory, or generated gzip archive is missing. Release shards fail when their artifact directory is missing, when no target archive is assigned, or when gzip or Brotli conversion fails.

Do not add retry layers. If the producer or release fails, record the failed job, step, annotation, and URL, diagnose the new failure, and stop before dispatching another run.

If any successful package job takes 15 minutes or longer, treat the performance requirement as failed. Record per-step timings and revise shard counts or artifact boundaries before another release attempt.

## Verification

Contract tests must prove:

- The producer creates and uploads `release-linux`, `release-windows`, and `release-macos` without artifact recompression.
- Linux source archives are generated only once and retain library-relative paths.
- The release matrix contains exactly 6 Linux target shards, 4 Windows target shards, 4 macOS target shards, one Linux source job, one rustc-bins job, and one llvm-bins job.
- Target assignment is deterministic, excludes Linux source archives, and covers each target exactly once.
- OS package jobs consume `release-*`, do not expand `dist-*`, and retain Brotli quality 11.
- Partial release artifacts use unique names and `compression-level: 0`.
- The publish job still merges all `release-assets-*` artifacts.
- Existing public asset contract tests continue to pass.

Run focused Python contracts, actionlint, and `git diff --check` before pushing.

After the new complete producer run, verify all required producer artifacts are present and unexpired. After the release run, calculate each package job duration from GitHub's `started_at` and `completed_at`; every package job must be less than 900 seconds. Finally verify the full release asset set, Pages deployment, and public `rust-src.tar.br` entries.

## Out Of Scope

- Changing public archive names or member layouts.
- Lowering Brotli quality.
- Removing existing `dist-*` producer artifacts.
- Adding archive digests, embedded compiler identity checks, or retry loops.
- Optimizing the producer workflow's total duration.
