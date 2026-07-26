# rust_wasm
Storage of rust compiler made of wasm

## Overview
This project builds and distributes the Rust compiler and LLVM tools compiled to WebAssembly.

---

## 🚀 リリース手順 (New Release Process)

Gitのリポジトリ肥大化を防ぐため、バイナリをGitにコミットせず、**GitHub Actions Artifacts** と **GitHub Releases** を活用する仕組みに移行しました。

### ステップ 1: ビルドの実行 (Build Artifacts)
GitHub Actionsの画面（または `gh` CLI）から以下のワークフローを実行して、バイナリを生成します。

1.  **Build LLVM**: LLVM/ClangツールのWASM版をビルドします。
2.  **rustc_llvm_with_lld**: Rustコンパイラ本体をビルドします。
    - `job` 入力で `install`, `dist-linux`, `dist-macos`, `dist-windows` をそれぞれ実行してください。

**確認事項**: 各ジョブの完了後、実行詳細画面の下部「Artifacts」セクションに成果物がアップロードされていることを確認してください。

### ステップ 2: リリースの作成 (Create Release)
すべてのビルド（LLVMおよび各OSのRust）が成功したら、リリースを作成します。

1.  **create release** ワークフローを実行します。
2.  `version` 入力にタグ名（例: `v0.2.0`）を指定して実行します。
3.  **自動処理内容**:
    - 直近のビルドから最新のArtifactsを自動ダウンロード。
    - 配布用パッケージ（`.tar.gz`, `.br`）の作成。
    - **GitHub Releases** ページへの直接アップロード。

### 🌐 ホスティング規則 (Hosting Rules)

本プロジェクトでは配布アセットをCloudflare Pagesでホスティングしています。以下の規則に基づき自動でデプロイが行われます。

1. **自動デプロイ**: `create release` ワークフローの完了後に自動でデプロイ処理（`Deploy to Cloudflare Pages`）が実行されます。
2. **ディレクトリ構成**: GitHub Releasesのアセットは、タグ名からサフィックスを除いたバージョン名のディレクトリ（例: `v3.0.0-release` -> `public/v3.0.0/`）に配置されます。
3. **大容量ファイルの自動分割**: Cloudflare Pagesのファイルサイズ制限（1ファイル25MB）に準拠するため、**20MBを超えるファイルは自動的に20MBごとに分割**されます（ファイル名の末尾に `.part00`, `.part01`... が付与されます）。
4. **マニフェストの生成**: 分割されたファイルの結合情報は、同ディレクトリ内の `split_manifest.json` に自動生成されます。クライアント側でダウンロードする際は、このファイルを参照して結合してください。

---

## 🧹 レポジトリのクリーンアップ (Legacy Cleanup)
以前の仕組みで使用していた以下のバイナリ保存用ブランチは非推奨となりました。新しいリリース方式で正常に配布できることが確認でき次第、これらを削除してリポジトリを軽量化してください。

- `rustc_llvm_with_lld-bins`
- `rustc_llvm_with_lld-bins-tier2-host`
- `rustc_llvm_with_lld-bins-tier2-host-windows`
- `rustc_llvm_with_lld-bins-tier2-host-mac`
- `llvm-tools`
- `gh-pages` (バイナリ配布のみに使用していた場合)

---

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

## About `rustc_unwind.wasm`

`rustc_unwind.wasm` means that the compiler itself was built with
`panic=unwind`. It does not automatically make generated programs use
unwinding. The panic strategy of generated programs is still controlled by
the selected sysroot and `-C panic`.

For normal target programs, use:

- `rustc.wasm` or `rustc_unwind.wasm`
- `sysroot-abort`
- `-C panic=abort`

Using `-C panic=unwind` requires a separate unwind-enabled sysroot and
runtime support for WebAssembly exception handling.
