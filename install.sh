#!/usr/bin/env bash
# install.sh —— 项目总一键安装脚本。
#
# 作用：把本项目部署到用户机器，让 `clenv` 与 `setup-environments.sh` 成为可直接调用
# 的命令，并（可选）顺带安装一批开发/工具环境。
#
# 两种用法：
#   1) 已 clone 到本地：  bash install.sh [选项]
#   2) 远程一键（会自动 clone 本仓库到 ~/.local/share/clenv/repo）：
#        curl -fsSL <raw-install.sh-URL> | bash
#        curl -fsSL <raw-install.sh-URL> | bash -s -- --envs lang codec
#
# 选项：
#   --envs <分类/项目…>   安装完命令后，顺带部署这些环境（等价 setup-environments.sh …）
#   --prefix <dir>        命令软链目录（默认 ~/.local/bin）
#   --copy                复制而非软链 clenv（脱离仓库也能跑；默认软链，便于随仓库更新）
#   --no-path             不改动 shell rc 的 PATH
#   --no-claude           跳过「检测并自动安装 Claude Code」这一步
#   --api <url>           配置 Claude Code 全局 API 地址（ANTHROPIC_BASE_URL）
#   --model <name>        配置 Claude Code 全局默认模型（ANTHROPIC_MODEL）
#   --token <token>       配置全局令牌（ANTHROPIC_AUTH_TOKEN，明文写入用户级设置）
#   --model <name>        配置全局默认模型（ANTHROPIC_MODEL）
#   --opus-model <name>   配置 ANTHROPIC_DEFAULT_OPUS_MODEL
#   --sonnet-model <name> 配置 ANTHROPIC_DEFAULT_SONNET_MODEL
#   --haiku-model <name>  配置 ANTHROPIC_DEFAULT_HAIKU_MODEL
#   --subagent-model <n>  配置 CLAUDE_CODE_SUBAGENT_MODEL
#   --effort <level>      配置 CLAUDE_CODE_EFFORT_LEVEL（low/medium/high）
#   --silent, -s          静默：不做任何交互式询问（适合 curl|bash / CI），也不自动刷新 shell
#   --no-refresh          配置完成后不自动刷新（不 exec 新的登录 shell）
#   -h, --help
#
# 默认行为：安装 clenv 后自动检测 Claude Code 是否已安装；未安装则装前置环境（Node/curl）
# 并安装 Claude Code。随后：
#   * 若通过命令行给了任意 --api/--token/--model/--*-model/--effort → 直接写入全局设置（非交互）；
#   * 否则在**交互式终端**下询问「是否现在配置 API 地址/模型等」，选是则逐项交互录入并写入，
#     完成后自动刷新 shell（exec 登录 shell）使 PATH 与配置立即生效；
#   * --silent 则完全跳过上述询问与刷新。
set -uo pipefail

REPO_URL="${CLENV_REPO_URL:-https://github.com/CyberNova2333/claude-enviroment-for-local-development.git}"
PREFIX="${CLENV_BIN_DIR:-$HOME/.local/bin}"
DO_COPY=0
DO_PATH=1
DO_CLAUDE=1
SILENT=0
DO_REFRESH=1
ENVS=()

# ---- 可配置的 Claude Code 环境变量表（顺序即交互录入顺序）----
# 下标对齐：CFG_SUB=clenv 子命令，CFG_DESC=交互提示，CFG_SECRET=是否隐藏输入，CFG_VAL=收集到的值
CFG_SUB=(api            token          model            opus-model                    sonnet-model                    haiku-model                    subagent-model               effort)
CFG_DESC=("第三方 API 地址 ANTHROPIC_BASE_URL" \
          "令牌 ANTHROPIC_AUTH_TOKEN（输入不回显）" \
          "默认模型 ANTHROPIC_MODEL" \
          "Opus 档模型 ANTHROPIC_DEFAULT_OPUS_MODEL" \
          "Sonnet 档模型 ANTHROPIC_DEFAULT_SONNET_MODEL" \
          "Haiku 档模型 ANTHROPIC_DEFAULT_HAIKU_MODEL" \
          "子代理模型 CLAUDE_CODE_SUBAGENT_MODEL" \
          "努力级别 CLAUDE_CODE_EFFORT_LEVEL（low/medium/high）")
CFG_ENV=(ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_SONNET_MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL CLAUDE_CODE_SUBAGENT_MODEL CLAUDE_CODE_EFFORT_LEVEL)
CFG_SECRET=(0 1 0 0 0 0 0 0)
CFG_VAL=("" "" "" "" "" "" "" "")

# 把命令行 --flag 值写进对应下标
_set_cfg() { # _set_cfg <子命令名> <值>
  local i
  for i in "${!CFG_SUB[@]}"; do
    [ "${CFG_SUB[$i]}" = "$1" ] && { CFG_VAL[$i]="$2"; return 0; }
  done
}

# ---- 解析参数 ----
while [ $# -gt 0 ]; do
  case "$1" in
    --envs)   shift; while [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; do ENVS+=("$1"); shift; done;;
    --prefix) PREFIX="$2"; shift 2;;
    --copy)   DO_COPY=1; shift;;
    --no-path) DO_PATH=0; shift;;
    --no-claude) DO_CLAUDE=0; shift;;
    --api)            _set_cfg api "$2"; shift 2;;
    --token)          _set_cfg token "$2"; shift 2;;
    --model)          _set_cfg model "$2"; shift 2;;
    --opus-model)     _set_cfg opus-model "$2"; shift 2;;
    --sonnet-model)   _set_cfg sonnet-model "$2"; shift 2;;
    --haiku-model)    _set_cfg haiku-model "$2"; shift 2;;
    --subagent-model) _set_cfg subagent-model "$2"; shift 2;;
    --effort)         _set_cfg effort "$2"; shift 2;;
    --silent|-s) SILENT=1; shift;;
    --no-refresh) DO_REFRESH=0; shift;;
    -h|--help) sed -n '2,41p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "未知选项：$1"; exit 2;;
  esac
done

say()  { printf '\033[34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m[✓]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31m[✗]\033[0m %s\n' "$*" >&2; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

# 是否处于可交互终端（curl|bash 时 stdin 是管道，但仍可能有 /dev/tty）
is_tty() { [ -t 0 ] && return 0; [ -t 1 ] && [ -r /dev/tty ] && return 0; return 1; }
# 交互读取一行：优先从 /dev/tty 读，回退 stdin。用法：ask <变量名> [secret]
ask() {
  local __src=/dev/stdin __val=""
  [ -r /dev/tty ] && __src=/dev/tty
  if [ "${2:-}" = "secret" ]; then read -rs __val < "$__src"; echo; else read -r __val < "$__src"; fi
  printf -v "$1" '%s' "$__val"
}

# 需要提权时用（root 则为空）
if [ "$(id -u)" -eq 0 ]; then SUDO=""; elif has sudo; then SUDO="sudo"; else SUDO=""; fi

# ---- 定位仓库根 ----
# 若脚本随仓库存在（BASH_SOURCE 指向真实文件且旁边有 bin/clenv），直接用；
# 否则（如 curl | bash）自动 clone 到 ~/.local/share/clenv/repo。
REPO_ROOT=""
SELF="${BASH_SOURCE[0]:-}"
if [ -n "$SELF" ] && [ -f "$SELF" ]; then
  cand="$(cd "$(dirname "$SELF")" && pwd)"
  [ -f "$cand/bin/clenv" ] && REPO_ROOT="$cand"
fi

if [ -z "$REPO_ROOT" ]; then
  say "未在本地检测到仓库，准备克隆：$REPO_URL"
  command -v git >/dev/null 2>&1 || die "需要 git 才能远程安装，请先安装 git。"
  DEST="$HOME/.local/share/clenv/repo"
  mkdir -p "$(dirname "$DEST")"
  if [ -d "$DEST/.git" ]; then
    say "已存在克隆，拉取更新…"
    git -C "$DEST" pull --ff-only >/dev/null 2>&1 || warn "更新失败，用现有版本继续。"
  else
    n=0
    until git clone --depth 1 "$REPO_URL" "$DEST" >/dev/null 2>&1; do
      n=$((n+1)); [ $n -ge 4 ] && die "克隆失败（已重试 $n 次）。"
      warn "克隆失败，$((2**n))s 后重试…"; sleep $((2**n))
    done
  fi
  REPO_ROOT="$DEST"
fi
ok "仓库根：$REPO_ROOT"

[ -f "$REPO_ROOT/bin/clenv" ] || die "仓库不完整：缺 bin/clenv"

# ---- 安装命令 ----
mkdir -p "$PREFIX"
chmod +x "$REPO_ROOT/bin/clenv" "$REPO_ROOT/scripts/setup-environments.sh" \
         "$REPO_ROOT/mcp/servers/"*.py 2>/dev/null

link_or_copy() { # link_or_copy <源> <目标名>
  local src="$1" name="$2" dst="$PREFIX/$2"
  if [ "$DO_COPY" -eq 1 ]; then
    cp "$src" "$dst"; chmod +x "$dst"
  else
    ln -sf "$src" "$dst"
  fi
  ok "已安装命令：$name -> $dst"
}
link_or_copy "$REPO_ROOT/bin/clenv" "clenv"
link_or_copy "$REPO_ROOT/scripts/setup-environments.sh" "setup-environments.sh"

# ---- 记录 repo_root 到 clenv 配置（让 clenv 在任意目录都能找到模板/MCP）----
CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/clenv"
CFG="$CFG_DIR/config.json"
mkdir -p "$CFG_DIR"
python3 - "$CFG" "$REPO_ROOT" <<'PY' 2>/dev/null || {
import json, os, sys
cfg_path, root = sys.argv[1], sys.argv[2]
try:
    with open(cfg_path) as f: cfg = json.load(f)
except Exception:
    cfg = {}
cfg["repo_root"] = root
cfg.setdefault("default_permissions", "standard")
cfg.setdefault("default_claude_file", "CLAUDE.md")
cfg.setdefault("default_mcp", "all")
with open(cfg_path, "w") as f: json.dump(cfg, f, ensure_ascii=False, indent=2)
PY
  warn "写入 clenv 配置失败（不影响命令使用，clenv 会自行按脚本路径推断仓库）。"
}
[ -f "$CFG" ] && ok "已写入 clenv 配置：$CFG"

# ---- PATH ----
if [ "$DO_PATH" -eq 1 ]; then
  case ":$PATH:" in
    *":$PREFIX:"*) : ;;
    *)
      for rc in "$HOME/.bashrc" "$HOME/.profile" "$HOME/.zshrc"; do
        [ -e "$rc" ] || continue
        grep -qsF "$PREFIX" "$rc" 2>/dev/null && continue
        printf '\n# added by claude-enviroment-for-local-development installer\nexport PATH="%s:$PATH"\n' "$PREFIX" >> "$rc"
      done
      warn "已把 $PREFIX 加入 PATH（当前 shell 需 source ~/.bashrc 或重开）。"
      ;;
  esac
fi

# ---- 检测并安装 Claude Code ----
# 把 Claude Code 常见安装目录加入本会话 PATH，便于安装后立即探测到。
refresh_claude_path() {
  local d
  for d in "$HOME/.local/bin" "$HOME/.claude/local" "$HOME/.claude/bin" "$HOME/bin"; do
    [ -d "$d" ] || continue
    case ":$PATH:" in *":$d:"*) : ;; *) PATH="$d:$PATH";; esac
  done
  export PATH
}

install_claude_code() {
  say "未检测到 Claude Code，开始安装前置环境与 Claude Code…"
  # 前置：curl（原生安装脚本需要）
  has curl || bash "$REPO_ROOT/scripts/setup-environments.sh" curl >/dev/null 2>&1 || true

  # 方式 1：官方原生安装脚本（自带二进制，无需 Node）
  if has curl; then
    say "尝试官方原生安装：curl -fsSL https://claude.ai/install.sh | bash"
    curl -fsSL https://claude.ai/install.sh 2>/dev/null | bash >/dev/null 2>&1 || true
    refresh_claude_path
  fi

  # 方式 2：npm 全局安装（回退，需 Node.js）
  if ! has claude; then
    warn "原生安装未成功或不可用，回退到 npm 方式（需 Node.js）…"
    has node || bash "$REPO_ROOT/scripts/setup-environments.sh" node >/dev/null 2>&1 || true
    refresh_claude_path
    if has npm; then
      say "npm install -g @anthropic-ai/claude-code"
      npm install -g @anthropic-ai/claude-code >/dev/null 2>&1 \
        || $SUDO npm install -g @anthropic-ai/claude-code >/dev/null 2>&1 || true
      refresh_claude_path
    fi
  fi

  if has claude; then
    ok "Claude Code 安装完成：$(claude --version 2>/dev/null || echo '已安装')"
  else
    warn "Claude Code 自动安装未成功（可能网络受限）。可稍后手动安装："
    warn "  curl -fsSL https://claude.ai/install.sh | bash   或   npm install -g @anthropic-ai/claude-code"
  fi
}

if [ "$DO_CLAUDE" -eq 1 ]; then
  refresh_claude_path
  if has claude; then
    ok "已检测到 Claude Code：$(claude --version 2>/dev/null || echo '已安装')"
  else
    install_claude_code
  fi
else
  say "按 --no-claude，跳过 Claude Code 检测/安装。"
fi

# ---- 配置 Claude Code 全局环境变量（覆盖 API/令牌/各档模型/子代理模型/努力级别）----
NEED_REFRESH=0
cfg_has_values() { local v; for v in "${CFG_VAL[@]}"; do [ -n "$v" ] && return 0; done; return 1; }
configure_claude_env() {
  local cli="$PREFIX/clenv" i
  has "$cli" || cli="clenv"
  for i in "${!CFG_SUB[@]}"; do
    [ -n "${CFG_VAL[$i]}" ] || continue
    "$cli" config "${CFG_SUB[$i]}" "${CFG_VAL[$i]}" --global
    # 同时导出到本进程环境，供随后 exec 的登录 shell 继承，立即生效
    export "${CFG_ENV[$i]}=${CFG_VAL[$i]}"
  done
}

# 交互式询问是否配置，并逐项录入（全部环境变量）
prompt_configure_claude() {
  local ans v i
  printf '\033[34m[?]\033[0m 是否现在配置 Claude Code 的 API 地址 / 模型 / 努力级别等全局设置？[y/N] '
  ask ans
  case "$ans" in
    y|Y|yes|YES|是) ;;
    *) say "跳过 Claude Code 配置（以后可随时 clenv config <项> <值> --global）。"; return 0;;
  esac
  say "逐项录入（每项回车即跳过）："
  for i in "${!CFG_SUB[@]}"; do
    printf '  %s: ' "${CFG_DESC[$i]}"
    if [ "${CFG_SECRET[$i]}" = 1 ]; then ask v secret; else ask v; fi
    [ -n "$v" ] && CFG_VAL[$i]="$v"
  done
  if ! cfg_has_values; then say "未输入任何值，跳过配置。"; return 0; fi
  say "写入全局设置（~/.claude/settings.json 的 env）…"
  configure_claude_env
  NEED_REFRESH=1
}

if cfg_has_values; then
  # 命令行已给出任意配置 → 非交互直接写入
  say "配置 Claude Code 全局设置（写入 ~/.claude/settings.json 的 env）…"
  configure_claude_env
elif [ "$SILENT" -eq 1 ]; then
  : # 静默：不询问
elif is_tty; then
  prompt_configure_claude
elif [ "$DO_CLAUDE" -eq 1 ] && has claude; then
  say "如需配置第三方 API/模型：clenv config api <url> --global；clenv config model <name> --global"
fi

# ---- 可选：部署环境 ----
if [ "${#ENVS[@]}" -gt 0 ]; then
  say "部署环境：${ENVS[*]}"
  bash "$REPO_ROOT/scripts/setup-environments.sh" "${ENVS[@]}"
fi

echo
ok "安装完成！"
echo "  验证：  clenv doctor"
has claude && echo "  Claude Code：$(claude --version 2>/dev/null || echo 已安装)（配置：clenv config api <url> --global）"
echo "  装环境：clenv env install ffmpeg jq gh   或   setup-environments.sh lang codec"
echo "  初始化项目：clenv init my-project --permissions standard --mcp all"

# ---- 自动刷新 shell：让新配置与 PATH 立即生效 ----
# 仅在「交互配置过、允许刷新、非静默、且处于交互终端」时，用登录 shell 替换当前进程。
if [ "$NEED_REFRESH" -eq 1 ] && [ "$DO_REFRESH" -eq 1 ] && [ "$SILENT" -eq 0 ] && is_tty; then
  echo
  ok "配置完成，正在刷新 shell 使 PATH 与 API/模型设置立即生效…"
  # 已 export 的 ANTHROPIC_* 会被下面 exec 的登录 shell 继承；-l 让其重读 profile 拿到新 PATH
  exec "${SHELL:-bash}" -l
fi
[ "$DO_PATH" -eq 1 ] && case ":$PATH:" in *":$PREFIX:"*) : ;; *) echo "  （先执行： export PATH=\"$PREFIX:\$PATH\"  使本终端立即生效）";; esac
