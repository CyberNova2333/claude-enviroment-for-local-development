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
#   -h, --help
set -uo pipefail

REPO_URL="${CLENV_REPO_URL:-https://github.com/CyberNova2333/claude-enviroment-for-local-development.git}"
PREFIX="${CLENV_BIN_DIR:-$HOME/.local/bin}"
DO_COPY=0
DO_PATH=1
ENVS=()

# ---- 解析参数 ----
while [ $# -gt 0 ]; do
  case "$1" in
    --envs)   shift; while [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; do ENVS+=("$1"); shift; done;;
    --prefix) PREFIX="$2"; shift 2;;
    --copy)   DO_COPY=1; shift;;
    --no-path) DO_PATH=0; shift;;
    -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "未知选项：$1"; exit 2;;
  esac
done

say()  { printf '\033[34m[*]\033[0m %s\n' "$*"; }
ok()   { printf '\033[32m[✓]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[31m[✗]\033[0m %s\n' "$*" >&2; exit 1; }

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

# ---- 可选：部署环境 ----
if [ "${#ENVS[@]}" -gt 0 ]; then
  say "部署环境：${ENVS[*]}"
  bash "$REPO_ROOT/scripts/setup-environments.sh" "${ENVS[@]}"
fi

echo
ok "安装完成！"
echo "  验证：  clenv doctor"
echo "  装环境：clenv env install ffmpeg jq gh   或   setup-environments.sh lang codec"
echo "  初始化项目：clenv init my-project --permissions standard --mcp all"
[ "$DO_PATH" -eq 1 ] && case ":$PATH:" in *":$PREFIX:"*) : ;; *) echo "  （先执行： export PATH=\"$PREFIX:\$PATH\"  使本终端立即生效）";; esac
