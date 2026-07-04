# clenv-lang —— 语言开发环境 MCP

服务器文件：`servers/lang_mcp.py` ｜ 版本：2.0.0 ｜ 工具数：13

面向「无头」语言环境：查版本、跑内联代码、建虚拟环境、装依赖、编译、测试、静态检查。
每个工具带只读/写标注与调用示例。

## 工具清单

| 工具 | 用途 | 只读 | 关键参数 |
|---|---|:--:|---|
| `versions` | 汇总各语言工具链版本 | ✓ | 无 |
| `run_code` | 执行内联 python/node/ruby/bash | | `lang`,`code`,`stdin?`,`timeout?` |
| `python_venv_create` | 创建 venv | | `path` |
| `python_pip_install` | venv/系统装 pip 包 | | `packages`,`venv?` |
| `python_run` | 运行 Python 脚本 | | `script`,`venv?`,`args?` |
| `pytest_run` | 跑 pytest | | `cwd?`,`target?`,`k?` |
| `python_lint` | ruff 静态检查（可 fix） | | `path?`,`fix?` |
| `npm_install` | npm 安装依赖 | | `cwd?`,`packages?`,`dev?` |
| `npm_script` | 运行 npm run <脚本> | | `cwd?`,`script` |
| `go_build` | go build | | `cwd?`,`target?` |
| `go_test` | go test | | `cwd?`,`target?` |
| `cargo_build` | cargo build（可 release） | | `cwd?`,`release?` |
| `cargo_test` | cargo test | | `cwd?` |

> `run_code` 特别适合「验证一小段逻辑、做计算、跑一次性脚本」，无需先落文件；
> 支持通过 `stdin` 喂标准输入、`timeout` 限时。

## 涉及工具与版本

| 工具 | 说明 | 安装项名 |
|---|---|---|
| Python 3 + venv + pip | 解释器与虚拟环境/包管理 | `python` |
| pytest | Python 测试框架 | `pytest` |
| ruff | Python 静态检查/格式化 | `ruff` |
| Node.js + npm | 系统包或 nvm LTS | `node` |
| Go | 系统包或官方 tar 包 | `go` |
| Rust + Cargo | rustup stable | `rust` |
| Ruby | 发行版 ruby-full | `ruby` |
| Java (OpenJDK) | 发行版默认 JDK | `java` |
