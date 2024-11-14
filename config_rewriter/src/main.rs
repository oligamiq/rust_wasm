use toml_edit::{Array, DocumentMut, Item, Value};

fn main() -> anyhow::Result<()> {
    let args = std::env::args().collect::<Vec<String>>();

    let file_name = &args[1];

    enum Targets {
        All,
        WasmAndX64Linux,
    }
    let targets = match args[2].as_str() {
        "all" => Targets::All,
        "wasm_and_x64_linux" => Targets::WasmAndX64Linux,
        _ => panic!("invalid targets type"),
    };

    enum OS {
        Linux,
        Windows,
        Mac,
    }
    let os = match args[3].as_str() {
        "linux" => OS::Linux,
        "windows" => OS::Windows,
        "mac" => OS::Mac,
        _ => panic!("invalid os type"),
    };

    let file = std::fs::read_to_string(file_name)?;
    // let toml_file = toml_edit::from_str::<toml::Value>(&file)?;
    let mut doc = file.parse::<DocumentMut>().expect("invalid doc");

    match targets {
        Targets::All => {
            doc["llvm"]["targets"] = "AArch64;ARM;BPF;Hexagon;LoongArch;MSP430;Mips;NVPTX;PowerPC;RISCV;Sparc;SystemZ;WebAssembly;X86".into();
            doc["llvm"]["experimental-targets"] = "AVR;M68k;CSKY".into();
            doc["build"]["target"] = match os {
                OS::Linux => {
                    vec![
                        // Tier 1
                        "aarch64-unknown-linux-gnu",
                        "i686-unknown-linux-gnu",
                        "x86_64-unknown-linux-gnu",

                        // Tier 2
                        "aarch64-unknown-linux-musl",
                        "arm-unknown-linux-gnueabi",
                        "arm-unknown-linux-gnueabihf",
                        "armv7-unknown-linux-gnueabihf",
                        "loongarch64-unknown-linux-gnu",
                        "loongarch64-unknown-linux-musl",
                        "powerpc-unknown-linux-gnu",
                        "powerpc64-unknown-linux-gnu",
                        "powerpc64le-unknown-linux-gnu",
                        "riscv64gc-unknown-linux-gnu",
                        "riscv64gc-unknown-linux-musl",
                        "s390x-unknown-linux-gnu",
                        "x86_64-unknown-freebsd",
                        "x86_64-unknown-illumos",
                        "x86_64-unknown-linux-musl",
                        "x86_64-unknown-netbsd",

                        // Tier 2 without host tools
                        "aarch64-unknown-fuchsia",
                        "aarch64-linux-android",
                        "aarch64-unknown-linux-ohos",
                        "aarch64-unknown-none-softfloat",
                        "aarch64-unknown-none",
                        "aarch64-unknown-uefi",
                        "arm-linux-androideabi",
                        "arm-unknown-linux-musleabi",
                        "arm-unknown-linux-musleabihf",
                        "armebv7r-none-eabi",
                        "armebv7r-none-eabihf",
                        "armv5te-unknown-linux-gnueabi",
                        "armv5te-unknown-linux-musleabi",
                        "armv7-linux-androideabi",
                        "armv7-unknown-linux-gnueabi",
                        "armv7-unknown-linux-musleabi",
                        "armv7-unknown-linux-musleabihf",
                        "armv7-unknown-linux-ohos",
                        "armv7a-none-eabi",
                        "armv7r-none-eabi",
                        "armv7r-none-eabihf",
                        "i586-unknown-linux-gnu",
                        "i586-unknown-linux-musl",
                        "i686-linux-android",
                        "i686-unknown-freebsd",
                        "i686-unknown-linux-musl",
                        "i686-unknown-uefi",
                        "loongarch64-unknown-none",
                        "loongarch64-unknown-none-softfloat",
                        "nvptx64-nvidia-cuda",
                        "riscv32imac-unknown-none-elf",
                        "riscv32i-unknown-none-elf",
                        "riscv32im-unknown-none-elf",
                        "riscv32imc-unknown-none-elf",
                        "riscv32imafc-unknown-none-elf",
                        "riscv64gc-unknown-none-elf",
                        "riscv64imac-unknown-none-elf",
                        "sparc64-unknown-linux-gnu",
                        "sparcv9-sun-solaris",
                        "thumbv6m-none-eabi",
                        "thumbv7em-none-eabi",
                        "thumbv7em-none-eabihf",
                        "thumbv7m-none-eabi",
                        "thumbv7neon-linux-androideabi",
                        "thumbv7neon-unknown-linux-gnueabihf",
                        "thumbv8m.base-none-eabi",
                        "thumbv8m.main-none-eabi",
                        "thumbv8m.main-none-eabihf",
                        "wasm32-unknown-emscripten",
                        "wasm32-unknown-unknown",
                        "wasm32-wasip1",
                        "wasm32-wasip2",
                        "wasm32-wasip1-threads",
                        "wasm32v1-none",
                        "x86_64-fortanix-unknown-sgx",
                        "x86_64-unknown-fuchsia",
                        "x86_64-linux-android",
                        "x86_64-pc-solaris",
                        "x86_64-unknown-linux-gnux32",
                        "x86_64-unknown-linux-ohos",
                        "x86_64-unknown-none",
                        "x86_64-unknown-redox",
                        "x86_64-unknown-uefi",
                    ]
                },
                OS::Windows => {
                    vec![
                        // Tier 1
                        "i686-pc-windows-gnu",
                        "i686-pc-windows-msvc",
                        "x86_64-pc-windows-gnu",
                        "x86_64-pc-windows-msvc",

                        // Tier 2
                        "aarch64-pc-windows-msvc",

                        // Tier 2 without host tools
                        "aarch64-pc-windows-gnullvm",
                        "arm64ec-pc-windows-msvc",
                        "i586-pc-windows-msvc",
                        "i686-pc-windows-gnullvm",
                        "x86_64-pc-windows-gnullvm"
                    ]
                },
                OS::Mac => {
                    vec![
                        // Tier 1
                        "aarch64-apple-darwin",
                        "x86_64-apple-darwin",

                        // Tier 2 without host tools
                        "aarch64-apple-ios",
                        "aarch64-apple-ios-macabi",
                        "aarch64-apple-ios-sim",
                        "x86_64-apple-ios",
                        "x86_64-apple-ios-macabi",
                    ]
                },
            }.to_item();
            doc["target"]["aarch64-unknown-linux-musl"]["musl-root"] = "/musl-aarch64".into();
            doc["target"]["loongarch64-unknown-linux-musl"]["musl-root"] = "/musl-loongarch64".into();
            doc["target"]["riscv64gc-unknown-linux-musl"]["musl-root"] = "/musl-riscv64gc".into();
            doc["target"]["x86_64-unknown-linux-musl"]["musl-root"] = "/musl-x86_64".into();
            doc["target"]["arm-unknown-linux-musleabi"]["musl-root"] = "/musl-arm".into();
            doc["target"]["arm-unknown-linux-musleabihf"]["musl-root"] = "/musl-armhf".into();
            doc["target"]["i586-unknown-linux-musl"]["musl-root"] = "/musl-i586".into();
            doc["target"]["i686-unknown-linux-musl"]["musl-root"] = "/musl-i686".into();
        },
        Targets::WasmAndX64Linux => {
            doc["llvm"]["targets"] = "WebAssembly;X86".into();
            doc["llvm"]["experimental-targets"] = "".into();

            doc["build"]["target"] = vec![
                "wasm32-unknown-unknown",
                "wasm32-wasip1",
                "wasm32-wasip2",
                "wasm32-wasip1-threads",
                "wasm32v1-none",
                "x86_64-unknown-linux-gnu",
            ].to_item();
        },
    }

    std::fs::write(file_name, doc.to_string())?;

    Ok(())
}

trait ToItem {
    fn to_item(&self) -> Item;
}

impl<T: AsRef<str>> ToItem for Vec<T> {
    fn to_item(&self) -> Item {
        let item: Value = Value::Array(self.iter().map(|x| x.as_ref().to_string()).collect::<Array>());
        item.into()
    }
}
