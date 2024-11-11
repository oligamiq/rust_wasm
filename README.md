# rust_wasm
Storage of rust compiler made of wasm

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

## Debian GNU/Linux 12 (bookworm) x86_64 AMD EPYC 7B13
target = [
    "wasm32-unknown-unknown",
    "wasm32-wasip1",
    "wasm32-wasip2",
    "wasm32-wasip1-threads",
    "wasm32v1-none",

    "aarch64-unknown-linux-gnu",
    "aarch64-apple-darwin",
    # "i686-pc-windows-gnu",
    # "i686-pc-windows-msvc",
    "i686-unknown-linux-gnu",
    "x86_64-apple-darwin",
    # "x86_64-pc-windows-gnu",
    # "x86_64-pc-windows-msvc",
    "x86_64-unknown-linux-gnu",
    # "aarch64-pc-windows-msvc",
    "arm-unknown-linux-gnueabi",
    "arm-unknown-linux-gnueabihf",
    "armv7-unknown-linux-gnueabihf",
    "powerpc-unknown-linux-gnu",
    "powerpc64-unknown-linux-gnu",
    "powerpc64le-unknown-linux-gnu",
    "riscv64gc-unknown-linux-gnu",
    "s390x-unknown-linux-gnu",
    "x86_64-unknown-freebsd",
    "x86_64-unknown-illumos",
]

sudo apt install gcc-riscv64-linux-gnu g++-riscv64-linux-gnu libc6-dev-riscv64-cross

sudo apt install gcc-powerpc64-linux-gnu g++-powerpc64-linux-gnu libc6-dev-ppc64-powerpc-cross

sudo apt install gcc-powerpc-linux-gnu g++-powerpc-linux-gnu libc6-dev-ppc64-powerpc-cross

sudo apt install gcc-powerpc64le-linux-gnu g++-powerpc64le-linux-gnu

sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu

sudo apt install gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf

sudo apt install gcc-arm-linux-gnueabi g++-arm-linux-gnueabi

sudo apt install gcc-gnueabihf-linux-gnu g++-gnueabihf-linux-gnu

sudo apt install gcc-gnueabi-linux-gnu g++-gnueabi-linux-gnu

sudo apt install gcc-s390x-linux-gnu g++-s390x-linux-gnu linux-libc-dev-s390x-cross
