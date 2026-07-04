# claude-enviroment-for-local-development

面向 **Claude Code（本地开发）** 的环境工具箱：一条命令部署常用开发/编解码/逆向/代码平台
工具，并把它们封装成 **MCP 工具**供 Agent 高效调用；再用统一的 `clenv` 命令管理环境版本、
虚拟环境、项目初始化与 Claude Code 设置。

> 许可证：GPL-3.0 ｜ 目标平台：Linux（Ubuntu/Debian/Fedora/CentOS/Arch/Alpine/openSUSE，
> 亦兼容 macOS + Homebrew）。MCP 服务器仅依赖系统自带的 `python3`。

---

## 一键安装

```bash
# 方式 A：已 clone 到本地
git clone https://github.com/CyberNova2333/claude-enviroment-for-local-development.git
cd claude-enviroment-for-local-development
bash install.sh                       # 只装命令
bash install.sh --envs lang codec     # 装命令 + 顺带部署「语言 + 编解码」环境

# 方式 B：远程一键（自动 clone 到 ~/.local/share/clenv/repo）
curl -fsSL https://raw.githubusercontent.com/CyberNova2333/claude-enviroment-for-local-development/main/install.sh | bash
```

安装完成后 `clenv` 与 `setup-environments.sh` 即为可直接调用的命令（若当前终端未生效，
执行 `source ~/.bashrc` 或 `export PATH="$HOME/.local/bin:$PATH"`）。验证：

```bash
clenv doctor
```

### 自动检测并安装 Claude Code

`install.sh` 默认会**检测 Claude Code 是否已安装**；若未安装，则自动装好前置环境
（curl / Node.js）并安装 Claude Code——优先用官方原生安装脚本
（`curl -fsSL https://claude.ai/install.sh | bash`），失败再回退 `npm install -g @anthropic-ai/claude-code`。
可用 `--no-claude` 跳过这一步。

同时可在安装时**一并配置 Claude Code 全局环境变量**（写入 `~/.claude/settings.json` 的 `env`）。
有两种方式：

**① 交互式（默认，在终端里运行时）**：脚本会询问「是否现在配置 API 地址/模型等」，选 `y`
后**逐项录入全部 8 个变量**（API 地址、令牌、默认模型、Opus/Sonnet/Haiku 档模型、
子代理模型、努力级别；令牌输入不回显，任一项留空即跳过）；配置完成后
**自动刷新 shell**（`exec` 登录 shell）使 PATH 与新设置立即生效，无需手动 `source ~/.bashrc`。

**② 非交互（命令行参数 / 自动化）**：直接给出参数则不询问、不刷新：

```bash
# 安装命令 + 安装 Claude Code + 配置第三方网关、默认模型与各档模型
bash install.sh --api https://your-gateway/v1 --token <令牌> \
  --model claude-opus-4-8 --opus-model claude-opus-4-8 \
  --sonnet-model claude-sonnet-5 --haiku-model claude-haiku-4-5 \
  --subagent-model claude-sonnet-5 --effort high

# 完全静默（curl|bash / CI 场景，绝不弹任何交互）
curl -fsSL <install.sh-URL> | bash -s -- --silent
```

> 通过 `curl | bash` 且未加 `--silent` 时：只要存在可用终端（`/dev/tty`）就会交互询问；
> 若无终端（如 CI）则自动跳过询问，绝不阻塞。

`install.sh` 选项：

| 选项 | 作用 |
|---|---|
| `--envs <分类/项目…>` | 安装完命令后顺带部署这些环境（支持 `name@version`） |
| `--prefix <目录>` | 命令软链目录（默认 `~/.local/bin`） |
| `--copy` | 复制而非软链 clenv（脱离仓库也能跑） |
| `--no-path` | 不改动 shell rc 的 PATH |
| `--no-claude` | 跳过「检测并自动安装 Claude Code」 |
| `--api <url>` | `ANTHROPIC_BASE_URL` |
| `--token <token>` | `ANTHROPIC_AUTH_TOKEN`（明文写入用户级设置） |
| `--model <name>` | `ANTHROPIC_MODEL` |
| `--opus-model <name>` | `ANTHROPIC_DEFAULT_OPUS_MODEL` |
| `--sonnet-model <name>` | `ANTHROPIC_DEFAULT_SONNET_MODEL` |
| `--haiku-model <name>` | `ANTHROPIC_DEFAULT_HAIKU_MODEL` |
| `--subagent-model <name>` | `CLAUDE_CODE_SUBAGENT_MODEL` |
| `--effort <level>` | `CLAUDE_CODE_EFFORT_LEVEL`（low/medium/high） |
| `--silent` / `-s` | 静默：不做任何交互式询问，也不自动刷新 shell |
| `--no-refresh` | 交互配置后不自动刷新（不 `exec` 新登录 shell） |

> 给出任意一个 `--api/--token/--model/--*-model/--effort` 即视为非交互配置。

---

## 组成

| 模块 | 文件 | 作用 |
|---|---|---|
| 环境部署脚本 | `scripts/setup-environments.sh` | 一键部署四类环境，可按分类或单项安装，幂等 |
| 管理命令 | `bin/clenv` | 装环境 / 建虚拟环境 / 初始化项目 / 管理 Claude Code 设置 |
| MCP 工具集 | `mcp/servers/*.py` + `mcp/docs/*.md` | 把工具暴露给 Agent（纯 python3，零依赖） |
| 项目模板 | `templates/` | `clenv init` 用的 CLAUDE.md 模板与权限模板 |
| 总安装脚本 | `install.sh` | 部署命令、注册 PATH、可选装环境 |

---

## 1) 环境部署脚本 `setup-environments.sh`

七大分类，共 47 个可安装项：

| 分类 | 项目 |
|---|---|
| `lang`（语言，无头） | python、node、go、rust、java、ruby、**cpp**（gcc/g++/make/cmake/gdb）、**clang**、**dotnet**(C#)、**php** |
| `codec`（文件编解码/取证） | ffmpeg、imagemagick、jq、yq、pandoc、7z、protobuf、poppler、xxd、exiftool、tesseract、sqlite3、mediainfo、file |
| `reverse`（逆向/静态分析） | apktool、jadx、dex2jar、radare2、binwalk、frida、binutils、checksec、**adb**(安卓) |
| `debug`（调试） | gdb、lldb、valgrind、strace、ltrace |
| `vcs`（代码平台） | git、gh(GitHub CLI)、glab(GitLab CLI)、curl、wget |
| `devtools`（开发辅助） | shellcheck、ruff、pytest |
| `container`（容器） | docker |

覆盖常用语言的**无头开发+调试**（C/C++ 用 gcc/gdb/valgrind，C# 用 .NET SDK，Python/Java/Go/
Rust/PHP 等）与**平台逆向/调试**（安卓：apktool/jadx/frida/adb；Linux 二进制：radare2/gdb/
objdump/strace/ltrace）。

```bash
setup-environments.sh list                 # 列出全部分类与项目
setup-environments.sh doctor               # 只检测、打印各项版本
setup-environments.sh lang debug           # 按分类安装
setup-environments.sh cpp dotnet adb       # 按单项安装
setup-environments.sh all                  # 全部（不含 container）
```

特点：自动探测包管理器（apt/dnf/yum/pacman/apk/zypper/brew）；已安装则跳过；
系统包不可用时回退到官方二进制/tar 包/pip；下载失败自动退避重试；失败项汇总到末尾，可单独重试。

**源码编译兜底（最后手段）**：当系统包与二进制都拿不到时，对可源码构建的工具（如 `jq`）会
自动装好编译工具链（gcc/make/autoconf 等）并 `git clone` 源码本地编译安装，见
`scripts/lib/common.sh` 的 `build_from_source` / `ensure_build_toolchain`。

**指定版本（`name@version`）**：部分项支持精确版本安装 ——
`node`、`go`、`rust`、`yq`、`apktool`、`jadx`、`dex2jar`、`glab`、`ruff`、`pytest`、`frida`。
其余项（多为系统包）不支持精确版本，`@version` 会被忽略并提示。

```bash
setup-environments.sh go@1.21.0 node@20.11.1 yq@4.44.3   # 或 clenv env install go@1.21.0
```

> 指定版本时，只有产物真正落地/版本号匹配才记为成功；下载受阻会**如实报告失败**，
> 不会因系统里已有同名旧版本而误报成功。

---

## 2) MCP 工具集

四个 MCP 服务器（共 **61 个工具**）把上面的工具封装为结构化工具，让 Agent 以「工具调用」
而非「拼 bash」的方式使用，更稳、更省 token。每个工具都带**结构化调用示例**与
**只读/危险标注**（`annotations`），并在调用前校验必填参数、拦截不存在的路径、对未安装命令
给出安装指引——显著降低模型调用出错率。详见 [`mcp/README.md`](mcp/README.md)。

| 服务器 | 工具数 | 覆盖 | 文档 |
|---|:--:|---|---|
| `clenv-lang` | 13 | 内联执行、python/venv/pip/pytest/ruff、node/npm、go、cargo | [mcp/docs/lang.md](mcp/docs/lang.md) |
| `clenv-codec` | 20 | ffmpeg、mediainfo、ImageMagick、tesseract、jq、yq、sqlite3、pandoc、7z、file、strings、xxd、protoc、base64、哈希、poppler、exiftool | [mcp/docs/codec.md](mcp/docs/codec.md) |
| `clenv-reverse` | 13 | apktool、jadx、dex2jar、radare2、readelf/objdump/nm、checksec、gdb、binwalk、frida | [mcp/docs/reverse.md](mcp/docs/reverse.md) |
| `clenv-codeplatform` | 15 | git（状态/历史/diff/show/blame/grep/分支/克隆/提交/推送）、gh、glab、curl | [mcp/docs/codeplatform.md](mcp/docs/codeplatform.md) |

接入当前项目：`clenv mcp add all`（或 `clenv init` 时用 `--mcp` 勾选），在 Claude Code
里执行 `/mcp` 即可看到 `clenv-*` 服务器。

---

## 3) 管理命令 `clenv`

```bash
# 环境（类 apt 用法：查/装/卸/更新一应俱全）
clenv env list                 # 列出全部可安装项与分类
clenv env search ocr           # 按名称/说明/分类搜索
clenv env info gdb             # 查看某项说明、命令、是否已装、安装方式
clenv env installed            # 列出已安装项
clenv env install cpp jq gh    # 安装（可加 @版本，如 go@1.21.0）
clenv env remove ffmpeg        # 卸载（先删本项目产物，再按需卸系统包）
clenv env update               # 刷新包索引（≈ apt update）
clenv env upgrade yq           # 升级某项（卸后重装最新）
clenv env doctor               # 环境自检

# 虚拟环境
clenv venv create .venv                 # 建 Python venv
clenv venv create web --lang node       # 建 Node 项目环境
clenv venv list                         # 列出发现的虚拟环境

# 初始化项目（生成 CLAUDE.md + .claude/settings.json + .mcp.json）
clenv init my-project --name my-project --permissions standard --mcp all
#   --permissions  safe | standard | loose  （命令允许范围模板）
#   --mcp          all | none | 逗号分隔（lang,codec,reverse,codeplatform）
#   --claude-file  指令文件名（默认 CLAUDE.md）  --force 覆盖
#   --docker       启用 Docker 模式（见下文），可配 --docker-image / --docker-envs

# Docker 模式（详见「4) Docker 模式」）
clenv docker build             # 构建/更新镜像
clenv docker shell             # 进入挂载了本目录的容器
clenv docker run -- <命令>     # 在容器内跑一条命令（或用生成的 ./cdev <命令>）
clenv docker status            # 查看镜像/构建/是否需重建

# MCP
clenv mcp list                 # 列出可用 MCP 服务器
clenv mcp add lang codec       # 往当前项目 .mcp.json 增加
clenv mcp remove reverse       # 移除

# Claude Code 设置（默认写当前项目 .claude/settings.json，加 --global 写 ~/.claude）
clenv config show                            # 查看当前配置
clenv config api https://your-gateway/v1     # ANTHROPIC_BASE_URL
clenv config token <token>                   # ANTHROPIC_AUTH_TOKEN（仅写用户级设置）
clenv config model claude-opus-4-8           # ANTHROPIC_MODEL
clenv config opus-model claude-opus-4-8      # ANTHROPIC_DEFAULT_OPUS_MODEL
clenv config sonnet-model claude-sonnet-5    # ANTHROPIC_DEFAULT_SONNET_MODEL
clenv config haiku-model claude-haiku-4-5    # ANTHROPIC_DEFAULT_HAIKU_MODEL
clenv config subagent-model claude-sonnet-5  # CLAUDE_CODE_SUBAGENT_MODEL
clenv config effort high                     # CLAUDE_CODE_EFFORT_LEVEL（low/medium/high）
clenv config context 200000                  # CLAUDE_CODE_CONTEXT_LENGTH（供兼容网关读取）
clenv config output-tokens 32000             # CLAUDE_CODE_MAX_OUTPUT_TOKENS
clenv config default-file AGENTS.md          # init 默认指令文件名
clenv config permissions loose               # init 默认权限模板
```

`clenv` 是**自包含单文件**（仅依赖系统 `python3`），内嵌了兜底的 CLAUDE.md/权限模板，
即便脱离仓库也能完成 `init`。

### 权限（命令允许范围）模板

| 模板 | 适用 | 特点 |
|---|---|---|
| `safe` | 谨慎/生产 | 只放行只读命令，写/推送要问 |
| `standard` | 常规开发（默认） | 放行常用构建/测试/工具，破坏性/推送要问 |
| `loose` | 可信隔离环境 | 几乎放行全部，仅拦极危险与敏感读取 |

模板文件见 `templates/permissions/*.json`。

---

## 4) Docker 模式（安全可控的隔离环境）

在项目文件夹里选择 **Docker 模式**，整套环境就跑在一个**挂载了该文件夹**的容器里：
宿主机不被污染，容器退出即弃，改动通过挂载即时可见。

```bash
clenv init my-project --docker --docker-image ubuntu:24.04 --docker-envs "lang debug jq"
cd my-project
clenv docker build        # 首次构建（会自动检测 docker，缺失则自动安装）
./cdev python3 app.py     # 在容器内运行；等价 clenv docker run -- python3 app.py
clenv docker shell        # 进入容器交互 shell（工作目录即挂载的项目目录）
```

`clenv init --docker` 会在项目目录生成：

| 文件 | 作用 |
|---|---|
| `Dockerfile` | 基于所选镜像，装好 clenv 与 `--docker-envs` 指定的环境，`WORKDIR /workspace` |
| `.dockerignore` | 构建上下文忽略清单 |
| `.clenv-docker.json` | 记录镜像名、基础镜像、预装环境、Dockerfile 指纹 |
| `cdev` | 便捷封装：`./cdev <命令>` = 在挂载本目录的容器里执行 |

要点：

- **自动检测/安装 Docker**：`clenv docker build/run` 若发现 `docker` 缺失，会自动
  `clenv env install docker`（官方脚本优先，失败回退发行版包）；守护进程未运行会明确提示。
- **改动后自动重建**：在宿主机项目目录里改了 `Dockerfile`（或改配置后重生成），下次
  `clenv docker build/run` 会比对 Dockerfile 指纹，**检测到变化即自动重建镜像**以反映更改；
  未变化则跳过构建、直接复用。
- **挂载运行**：`docker run --rm -v <项目目录>:/workspace -w /workspace <镜像> <命令>`，
  容器内对 `/workspace` 的改动就是对宿主机项目目录的改动。

---

## 5) 总安装脚本 `install.sh`

见顶部「一键安装」。它负责：把 `clenv`、`setup-environments.sh` 软链（或复制）到
`~/.local/bin`、写入 PATH、把仓库根记录进 `~/.config/clenv/config.json`（让 `clenv` 在
任意目录都能找到模板与 MCP）、**检测并按需自动安装 Claude Code 及其前置环境、配置全局
API/模型/令牌**，并可选顺带部署环境。

---

## 开发与自测

```bash
bash -n scripts/setup-environments.sh install.sh scripts/lib/common.sh
python3 -m py_compile bin/clenv mcp/servers/*.py
# MCP 冒烟：initialize / tools/list / tools/call 三连
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
              '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python3 mcp/servers/codec_mcp.py
```

协作约定见 [`.claude/CLAUDE.md`](.claude/CLAUDE.md)：中文提交、直接进 `main`、
**代码与文档同步提交**（有 `PreToolUse` 钩子兜底）。
