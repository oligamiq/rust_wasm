pub fn main() -> anyhow::Result<()> {
    let mut wasm_path = std::env::args().nth(1).expect("no wasm path given");

    let mut file_size = std::fs::metadata(&wasm_path)?.len();

    println!("Initial size: {} bytes", file_size);

    let mut i = 0;

    loop {
        let file_name = format!("opt_{i}.wasm");

        let cmd = std::process::Command::new("wasm-opt")
            .arg(&wasm_path)
            .arg("-Oz")
            .arg("-o")
            .arg(&file_name)
            .output()?;

        if !cmd.status.success() {
            anyhow::bail!(
                "failed to run wasm-opt: {}",
                String::from_utf8_lossy(&cmd.stderr)
            );
        }

        let new_file_size = std::fs::metadata(&file_name)?.len();

        if new_file_size >= file_size {
            break;
        }

        file_size = new_file_size;
        wasm_path = file_name;

        i += 1;

        println!("Optimized to {} bytes", file_size);
    }

    std::fs::rename(wasm_path, "opt.wasm")?;

    for i in 0..i {
        std::fs::remove_file(format!("opt_{i}.wasm"))?;
    }

    println!("Final size: {} bytes", file_size);

    Ok(())
}
