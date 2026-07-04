# MCP 工具集说明

本目录为「本地开发/逆向/工具环境」封装的 **MCP（Model Context Protocol）服务器**，
让 Claude Code 等 Agent 能以「结构化工具调用」而非「拼 bash 命令」的方式使用这些工具，
从而更稳、更省 token。

## 特点

- **零第三方依赖**：全部用系统自带的 `python3` 实现 MCP 的 stdio + JSON-RPC 2.0
  协议（见 `servers/mcpbase.py`），无需 `pip install` 任何东西即可运行。
- **未安装即引导**：底层命令若不在 `PATH`，工具会返回明确的安装指引
  （`setup-environments.sh <项目>` 或 `clenv env install <项目>`），不会静默失败。
- **写操作显式化**：涉及「留下痕迹」的动作（`git push`、非 GET 的 API 调用等）
  一律需要显式 `allow_write=true`，避免 Agent 误触。

## 四个服务器

| 服务器 | 文件 | 覆盖工具 | 详细文档 |
|---|---|---|---|
| `clenv-lang` | `servers/lang_mcp.py` | python/venv/pip、node/npm、go、cargo、版本汇总 | [docs/lang.md](docs/lang.md) |
| `clenv-codec` | `servers/codec_mcp.py` | ffmpeg、ImageMagick、jq、yq、pandoc、7z、protoc、poppler、xxd | [docs/codec.md](docs/codec.md) |
| `clenv-reverse` | `servers/reverse_mcp.py` | apktool、jadx、dex2jar、radare2、binwalk、frida | [docs/reverse.md](docs/reverse.md) |
| `clenv-codeplatform` | `servers/codeplatform_mcp.py` | git、gh、glab、curl | [docs/codeplatform.md](docs/codeplatform.md) |

## 接入 Claude Code

三种方式任选其一：

1. **一键**：`clenv init` 初始化项目时勾选需要的 MCP 服务器，会自动写好 `.mcp.json`。
2. **半自动**：`clenv mcp add <名字>` 往当前项目的 `.mcp.json` 增删服务器。
3. **手动**：拷贝 `mcp.template.json` 为项目根的 `.mcp.json`，把 `__CLENV_MCP_DIR__`
   替换为 `servers/` 的绝对路径。

接好后在 Claude Code 里执行 `/mcp` 即可看到 `clenv-*` 服务器与其工具。

## 自测

每个服务器都能用一串 JSON-RPC 直接冒烟测试（无需客户端）：

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python3 servers/codec_mcp.py
```

会依次打印握手结果与工具清单。
