# clenv-lang —— 语言开发环境 MCP

服务器文件：`servers/lang_mcp.py` ｜ 版本：1.0.0

面向「无头」语言环境的日常操作：查版本、建虚拟环境、装依赖、编译/运行。所有工具
底层调用系统命令；命令缺失时返回安装指引。

## 工具清单

### `versions`
- **用途**：一次性汇总 python/pip、node/npm、go、cargo/rustc、java、ruby 的版本。
- **参数**：无。
- **典型场景**：开工前核对工具链是否齐备。

### `python_venv_create`
- **用途**：`python3 -m venv <path>` 创建隔离虚拟环境。
- **参数**：`path`（必填）—— venv 目录，如 `.venv`。
- **配套**：随后用 `python_pip_install`/`python_run` 传相同 `venv` 复用。

### `python_pip_install`
- **用途**：在指定 venv（或系统 `pip --user`）里装包。
- **参数**：`packages`（必填，字符串数组）；`venv`（可选，venv 目录）。

### `python_run`
- **用途**：用指定 venv（或系统 python）运行脚本。
- **参数**：`script`（必填）；`venv`（可选）；`args`（可选，脚本参数数组）。

### `npm_install`
- **用途**：在项目目录执行 `npm install`。
- **参数**：`cwd`（可选，默认当前）；`packages`（可选，不给则按 `package.json`）；
  `dev`（可选，true 则 `--save-dev`）。

### `go_build`
- **用途**：`go build`（默认 `./...`）编译校验。
- **参数**：`cwd`（可选）；`target`（可选，默认 `./...`）。

### `cargo_build`
- **用途**：`cargo build` 编译 Rust 项目。
- **参数**：`cwd`（可选）；`release`（可选，true 走优化构建）。

## 涉及工具与版本

| 工具 | 说明 | 安装项名（`clenv env install …`） |
|---|---|---|
| Python 3 + venv + pip | 解释器与虚拟环境/包管理 | `python` |
| Node.js + npm | 系统包或 nvm LTS | `node` |
| Go | 系统包或官方 1.22.x tar 包 | `go` |
| Rust + Cargo | rustup stable | `rust` |
| Java (OpenJDK) | 发行版默认 JDK | `java` |
| Ruby | 发行版 ruby-full | `ruby` |
