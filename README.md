# rust_wasm
Storage of Rust compiler compiled to WebAssembly.

## Overview
This project builds and distributes the Rust compiler and LLVM tools compiled to WebAssembly.

## Upstream Sources
- **rustc_llvm**: [oligamiq/rust](https://github.com/oligamiq/rust)
- **rustc_cranelift**: [bjorn3/rust](https://github.com/bjorn3/rust)
- **clang, wasm-ld, etc**: [YoWASP/clang](https://github.com/YoWASP/clang)

## Dependencies
- [toolchain-for-building-rustc](https://github.com/oligamiq/toolchain-for-building-rustc): Prebuilt toolchain for building rustc.

## Platform Support
This project targets Tier 1 and Tier 2 host platforms. See [Rust Platform Support](https://doc.rust-lang.org/nightly/rustc/platform-support.html) for details.

## 🚀 Release Process

To prevent repository bloat, we no longer commit binaries to Git. Instead, we use **GitHub Actions Artifacts** and **GitHub Releases**.

### Step 1: Build Artifacts
Generate the binaries by running the following workflows via the GitHub Actions UI (or `gh` CLI).

1. **Build LLVM**: Builds the WASM versions of LLVM/Clang tools.
2. **rustc_llvm_with_lld**: Builds the Rust compiler itself.
   - Run this workflow for each `job` input: `install`, `dist-linux`, `dist-macos`, `dist-windows`.

**Verification**: After each job completes, verify that the artifacts are uploaded in the "Artifacts" section at the bottom of the run details page.

### Step 2: Create Release
Once all builds (LLVM and Rust for each OS) are successful, create a release.

1. Run the **create release** workflow.
2. Provide the tag name (e.g., `v0.2.0`) in the `version` input.
3. **Automated Processes**:
   - Automatically downloads the latest artifacts from the most recent successful builds.
   - Packages them for distribution (`.tar.gz`, `.br`).
   - Uploads them directly to the **GitHub Releases** page.

### 🌐 Hosting
- Assets from GitHub Releases are automatically deployed and hosted on Cloudflare Pages.
- To bypass file size limits, files larger than 20MB are automatically split (`.part00`, `.part01`...). Use the included `split_manifest.json` to restore the original files.

## About `rustc_unwind.wasm`

The `rustc_unwind.wasm` file indicates that the compiler itself was built with `panic=unwind`. It does not automatically make generated programs use unwinding. The panic strategy of generated programs is still controlled by the selected sysroot and `-C panic`.

For normal target programs, use:
- `rustc.wasm` or `rustc_unwind.wasm`
- `sysroot-abort`
- `-C panic=abort`

Using `-C panic=unwind` requires a separate unwind-enabled sysroot and runtime support for WebAssembly exception handling.

## 🧹 Legacy Cleanup
The following branches previously used to store binaries are now deprecated. Once it is confirmed that the new release process distributes files correctly, please delete these branches to reduce repository size:

- `rustc_llvm_with_lld-bins`
- `rustc_llvm_with_lld-bins-tier2-host`
- `rustc_llvm_with_lld-bins-tier2-host-windows`
- `rustc_llvm_with_lld-bins-tier2-host-mac`
- `llvm-tools`
- `gh-pages` (if used only for binary distribution)

## References
- [Miri issue #722](https://github.com/rust-lang/miri/issues/722)
- [LLVM Discourse RFC](https://discourse.llvm.org/t/rfc-building-llvm-for-webassembly/79073/37)
- [rubri](https://github.com/LyonSyonII/rubri)
