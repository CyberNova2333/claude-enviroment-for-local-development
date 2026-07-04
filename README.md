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

同时可在安装时**一并配置 Claude Code 全局环境变量**（写入 `~/.claude/settings.json` 的 `env`）：

```bash
# 安装命令 + 安装 Claude Code + 配置第三方 API 地址与默认模型
bash install.sh --api https://your-gateway/v1 --model claude-sonnet-5 --token <令牌>
```

`install.sh` 选项：

| 选项 | 作用 |
|---|---|
| `--envs <分类/项目…>` | 安装完命令后顺带部署这些环境 |
| `--prefix <目录>` | 命令软链目录（默认 `~/.local/bin`） |
| `--copy` | 复制而非软链 clenv（脱离仓库也能跑） |
| `--no-path` | 不改动 shell rc 的 PATH |
| `--no-claude` | 跳过「检测并自动安装 Claude Code」 |
| `--api <url>` | 配置全局 `ANTHROPIC_BASE_URL` |
| `--model <name>` | 配置全局 `ANTHROPIC_MODEL` |
| `--token <token>` | 配置全局 `ANTHROPIC_AUTH_TOKEN`（明文写入用户级设置） |

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

五大分类，共 36 个可安装项：

| 分类 | 项目 |
|---|---|
| `lang`（语言，无头） | python、node、go、rust、java、ruby |
| `codec`（文件编解码/取证） | ffmpeg、imagemagick、jq、yq、pandoc、7z、protobuf、poppler、xxd、exiftool、tesseract、sqlite3、mediainfo、file |
| `reverse`（逆向/静态分析） | apktool、jadx、dex2jar、radare2、binwalk、frida、binutils、gdb、checksec |
| `vcs`（代码平台） | git、gh(GitHub CLI)、glab(GitLab CLI)、curl、wget |
| `devtools`（开发辅助） | shellcheck、ruff、pytest |

```bash
setup-environments.sh list                 # 列出全部分类与项目
setup-environments.sh doctor               # 只检测、打印各项版本
setup-environments.sh lang codec           # 按分类安装
setup-environments.sh python ffmpeg gh     # 按单项安装
setup-environments.sh all                  # 全部（较重）
```

特点：自动探测包管理器（apt/dnf/yum/pacman/apk/zypper/brew）；已安装则跳过；
系统包不可用时回退到官方二进制/tar 包/pip；失败项汇总到末尾，可单独重试。

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
# 环境
clenv env list                 # 列出可安装项
clenv env doctor               # 环境自检
clenv env install ffmpeg jq gh # 安装若干项

# 虚拟环境
clenv venv create .venv                 # 建 Python venv
clenv venv create web --lang node       # 建 Node 项目环境
clenv venv list                         # 列出发现的虚拟环境

# 初始化项目（生成 CLAUDE.md + .claude/settings.json + .mcp.json）
clenv init my-project --name my-project --permissions standard --mcp all
#   --permissions  safe | standard | loose  （命令允许范围模板）
#   --mcp          all | none | 逗号分隔（lang,codec,reverse,codeplatform）
#   --claude-file  指令文件名（默认 CLAUDE.md）  --force 覆盖

# MCP
clenv mcp list                 # 列出可用 MCP 服务器
clenv mcp add lang codec       # 往当前项目 .mcp.json 增加
clenv mcp remove reverse       # 移除

# Claude Code 设置（默认写当前项目 .claude/settings.json，加 --global 写 ~/.claude）
clenv config show                          # 查看当前配置
clenv config api https://your-gateway/v1   # 第三方 API 地址（ANTHROPIC_BASE_URL）
clenv config token <token>                 # 网关令牌（ANTHROPIC_AUTH_TOKEN，仅写用户级设置）
clenv config model claude-fable-5          # 默认模型（ANTHROPIC_MODEL）
clenv config context 200000                # 模型上下文长度（供兼容网关读取）
clenv config output-tokens 32000           # 最大输出 token
clenv config default-file AGENTS.md        # init 默认指令文件名
clenv config permissions loose             # init 默认权限模板
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

## 4) 总安装脚本 `install.sh`

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
