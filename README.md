# rust_wasm
Storage of rust compiler made of wasm

## Overview
This project builds and distributes the Rust compiler and LLVM tools compiled to WebAssembly.

## Release Process
The release process has been modernized to avoid repository bloat by using GitHub Actions Artifacts and GitHub Releases instead of Git branches for binary storage.

### 1. Build Artifacts
Run the following workflows via `workflow_dispatch` (Actions tab) to generate the necessary build artifacts:
- **Build LLVM**: Builds LLVM/Clang tools.
- **rustc_llvm_with_lld**: Builds the Rust compiler (runs `install`, `dist-linux`, `dist-macos`, and `dist-windows` jobs).

Build outputs are temporarily stored as Actions Artifacts.

### 2. Create a Release
Once the build workflows have completed successfully:
1. Go to the **Actions** tab.
2. Select the **create release** workflow.
3. Click **Run workflow**, providing the version tag (e.g., `v0.2.0`).
4. The workflow will:
   - Download the latest artifacts from the build workflows.
   - Package them into `.tar.gz` and `.br` archives.
   - Upload them directly to a new GitHub Release.

## Repository Cleanup (Legacy)
The following branches were previously used to store binary artifacts and are now deprecated. Once the new release process is verified, they can be safely removed to reclaim space:
- `rustc_llvm_with_lld-bins`
- `rustc_llvm_with_lld-bins-tier2-host`
- `rustc_llvm_with_lld-bins-tier2-host-windows`
- `rustc_llvm_with_lld-bins-tier2-host-mac`
- `llvm-tools`
- `gh-pages` (if only used for binaries)

## Dependencies
- [toolchain-for-building-rustc](https://github.com/oligamiq/toolchain-for-building-rustc): Prebuilt toolchain for building rustc.

## Upstream Sources
- **rustc_llvm**: [oligamiq/rust](https://github.com/oligamiq/rust)
- **rustc_cranelift**: [bjorn3/rust](https://github.com/bjorn3/rust)
- **clang, wasm-ld, etc**: [YoWASP/clang](https://github.com/YoWASP/clang)

## References
- [Miri issue #722](https://github.com/rust-lang/miri/issues/722)
- [LLVM Discourse RFC](https://discourse.llvm.org/t/rfc-building-llvm-for-webassembly/79073/37)
- [rubri](https://github.com/LyonSyonII/rubri)

## Platform Support
This project targets Tier 1 and Tier 2 host platforms. See [Rust Platform Support](https://doc.rust-lang.org/nightly/rustc/platform-support.html) for details.
