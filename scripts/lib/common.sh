#!/usr/bin/env bash
# common.sh —— 供本仓库各 shell 脚本复用的公共函数库。
#
# 设计目标：
#   * 零外部依赖（仅用 coreutils / bash 内建），可在最小化容器里跑；
#   * 幂等：所有安装动作都先探测「是否已存在」，已装则跳过；
#   * 跨发行版：自动探测包管理器（apt / dnf / yum / pacman / apk / zypper / brew）。
#
# 用法：在其它脚本顶部 `source "$(dirname "$0")/lib/common.sh"`。

# ---- 严格模式（被 source 时不强行改变父 shell 选项，交由调用方决定）----------

# ---- 颜色 / 日志 -------------------------------------------------------------
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  C_RESET='\033[0m'; C_RED='\033[31m'; C_GREEN='\033[32m'
  C_YELLOW='\033[33m'; C_BLUE='\033[34m'; C_DIM='\033[2m'; C_BOLD='\033[1m'
else
  C_RESET=''; C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_DIM=''; C_BOLD=''
fi

log()   { printf '%b\n' "${C_BLUE}[*]${C_RESET} $*"; }
ok()    { printf '%b\n' "${C_GREEN}[✓]${C_RESET} $*"; }
warn()  { printf '%b\n' "${C_YELLOW}[!]${C_RESET} $*" >&2; }
err()   { printf '%b\n' "${C_RED}[✗]${C_RESET} $*" >&2; }
step()  { printf '%b\n' "\n${C_BOLD}==> $*${C_RESET}"; }
die()   { err "$*"; exit 1; }

# 命令是否存在
has() { command -v "$1" >/dev/null 2>&1; }

# ---- 包管理器探测 -----------------------------------------------------------
# 全局变量 PKG_MGR / PKG_INSTALL / PKG_UPDATE / SUDO
detect_pkg_mgr() {
  if [ -n "${PKG_MGR:-}" ]; then return 0; fi
  # 是否需要 sudo
  if [ "$(id -u)" -eq 0 ]; then SUDO=""; else
    if has sudo; then SUDO="sudo"; else SUDO=""; fi
  fi
  if has apt-get;  then PKG_MGR=apt;    PKG_UPDATE="$SUDO apt-get update -y";        PKG_INSTALL="$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends";
  elif has dnf;    then PKG_MGR=dnf;    PKG_UPDATE="$SUDO dnf makecache -y";          PKG_INSTALL="$SUDO dnf install -y";
  elif has yum;    then PKG_MGR=yum;    PKG_UPDATE="$SUDO yum makecache -y";          PKG_INSTALL="$SUDO yum install -y";
  elif has pacman; then PKG_MGR=pacman; PKG_UPDATE="$SUDO pacman -Sy";                PKG_INSTALL="$SUDO pacman -S --noconfirm --needed";
  elif has apk;    then PKG_MGR=apk;    PKG_UPDATE="$SUDO apk update";                PKG_INSTALL="$SUDO apk add";
  elif has zypper; then PKG_MGR=zypper; PKG_UPDATE="$SUDO zypper refresh";            PKG_INSTALL="$SUDO zypper install -y";
  elif has brew;   then PKG_MGR=brew;   PKG_UPDATE="brew update";                     PKG_INSTALL="brew install";
  else PKG_MGR=""; warn "未识别到受支持的包管理器，系统级安装将被跳过。"; return 1; fi
  export PKG_MGR PKG_INSTALL PKG_UPDATE SUDO
  return 0
}

# 缓存「本会话是否已 update 过索引」，避免重复刷新
_PKG_UPDATED=""
pkg_update_once() {
  detect_pkg_mgr || return 1
  [ -n "$_PKG_UPDATED" ] && return 0
  log "刷新包索引（$PKG_MGR）…"
  eval "$PKG_UPDATE" >/dev/null 2>&1 || warn "包索引刷新失败，继续尝试安装。"
  _PKG_UPDATED=1
}

# pkg_install <系统包名...>：用探测到的包管理器安装若干系统包
pkg_install() {
  detect_pkg_mgr || { warn "无包管理器，跳过：$*"; return 1; }
  pkg_update_once
  log "安装系统包：$*"
  eval "$PKG_INSTALL $*"
}

# ensure_cmd <命令名> <系统包名>：命令不存在则用系统包名安装
ensure_cmd() {
  local cmd="$1" pkg="${2:-$1}"
  if has "$cmd"; then ok "已存在：$cmd"; return 0; fi
  pkg_install "$pkg" && has "$cmd" && ok "已安装：$cmd" || warn "安装 $cmd 可能未成功。"
}

# 版本号打印（尽量取一行）
show_ver() { "$@" 2>&1 | head -n1; }

# 确保某目录在 PATH 中（写入 shell rc）；返回是否新增
ensure_path() {
  local dir="$1" rc
  case ":$PATH:" in *":$dir:"*) return 0;; esac
  export PATH="$dir:$PATH"
  for rc in "$HOME/.bashrc" "$HOME/.profile" "$HOME/.zshrc"; do
    [ -f "$rc" ] || continue
    grep -qsF "$dir" "$rc" 2>/dev/null && continue
    printf '\n# added by claude-enviroment-for-local-development\nexport PATH="%s:$PATH"\n' "$dir" >> "$rc"
  done
}
