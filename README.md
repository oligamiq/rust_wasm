# rust_wasm
Storage of rust compiler made of wasm

# Dependencies
https://github.com/oligamiq/toolchain-for-building-rustc
This give prebuilt toolchain for building rustc.

# The site from which the wasm file was generated:
- rustc_llvm: https://github.com/oligamiq/rust contributor:oligamiq
- rustc_cranelift https://github.com/bjorn3/rust contributor:bjorn3
- clang, wasm-ld, etc :https://github.com/YoWASP/clang contributor:whitequark, ArcaneNibble

# What's involved
- https://github.com/rust-lang/miri/issues/722
- https://discourse.llvm.org/t/rfc-building-llvm-for-webassembly/79073/37
- https://github.com/LyonSyonII/rubri

# all features
This branch targets are target which support for Tier 1, Tier 2 which support for host.

https://doc.rust-lang.org/nightly/rustc/platform-support.html
