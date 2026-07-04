#!/usr/bin/env bash
# setup-environments.sh —— 一键部署本地开发/逆向/工具环境（无头，可直接在 bash 调用）。
#
# 四大类：
#   lang    编程语言开发环境（无头）：python / node / go / rust / java / ruby
#   codec   文件格式编解码工具：ffmpeg / imagemagick / jq / yq / pandoc / 7z / protobuf / poppler / xxd
#   reverse 逆向工程工具：apktool / jadx / dex2jar / radare2 / binwalk / frida
#   vcs     开源代码平台访问工具：git / gh(GitHub CLI) / glab(GitLab CLI) / curl / wget
#
# 用法：
#   setup-environments.sh list                 列出所有可安装项及其分类
#   setup-environments.sh all                   安装全部（较重，慎用）
#   setup-environments.sh lang codec            安装若干分类
#   setup-environments.sh python go ffmpeg jq   安装若干单项
#   setup-environments.sh doctor                只检测、不安装，打印各项版本
#   setup-environments.sh --help
#
# 约定：所有安装函数幂等——已安装则跳过；失败不中断整体（记录到末尾汇总）。
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$SCRIPT_DIR/lib/common.sh"

# 用户级安装目录（放置手动下载的工具与 wrapper）
CLENV_HOME="${CLENV_HOME:-$HOME/.local/share/clenv}"
BIN_DIR="${CLENV_BIN_DIR:-$HOME/.local/bin}"
OPT_DIR="$CLENV_HOME/opt"
mkdir -p "$BIN_DIR" "$OPT_DIR"
ensure_path "$BIN_DIR"

FAILED=()   # 收集失败项
DONE=()     # 收集成功/已存在项
_mark_ok()   { DONE+=("$1"); }
_mark_fail() { FAILED+=("$1"); }

# 下载助手：curl 优先，回退 wget
fetch() { # fetch <url> <dest>
  if has curl; then curl -fsSL "$1" -o "$2"
  elif has wget; then wget -qO "$2" "$1"
  else err "缺少 curl/wget，无法下载 $1"; return 1; fi
}

# 生成一个把某 jar 包装成命令的 wrapper 脚本
make_jar_wrapper() { # make_jar_wrapper <命令名> <jar绝对路径> [默认JVM参数]
  local name="$1" jar="$2" jvm="${3:-}"
  cat > "$BIN_DIR/$name" <<EOF
#!/usr/bin/env bash
exec java $jvm -jar "$jar" "\$@"
EOF
  chmod +x "$BIN_DIR/$name"
}

# ============================ lang：语言环境 ================================
install_python() {
  if has python3; then _mark_ok "python3 ($(python3 -V 2>&1))"; else
    pkg_install python3 python3-pip python3-venv || { _mark_fail python3; return; }
    _mark_ok python3
  fi
  # 确保 pip / venv 可用
  has pip3 || pkg_install python3-pip || true
  python3 -m venv --help >/dev/null 2>&1 || pkg_install python3-venv || true
}

install_node() {
  if has node; then _mark_ok "node ($(node -v))"; return; fi
  # 优先系统包；失败再用 nvm
  if pkg_install nodejs npm && has node; then _mark_ok node; return; fi
  log "系统包安装 node 失败，改用 nvm…"
  export NVM_DIR="$HOME/.nvm"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    fetch "https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh" "$OPT_DIR/nvm-install.sh" \
      && bash "$OPT_DIR/nvm-install.sh" >/dev/null 2>&1
  fi
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm install --lts >/dev/null 2>&1
  has node && _mark_ok "node (via nvm)" || _mark_fail node
}

install_go() {
  if has go; then _mark_ok "go ($(go version 2>&1 | awk '{print $3}'))"; return; fi
  if pkg_install golang-go && has go; then _mark_ok go; return; fi
  # 官方 tar 包（amd64/arm64）
  local arch ver="1.22.5" tgz
  case "$(uname -m)" in x86_64) arch=amd64;; aarch64|arm64) arch=arm64;; *) _mark_fail "go(未知架构)"; return;; esac
  tgz="$OPT_DIR/go.tgz"
  fetch "https://go.dev/dl/go${ver}.linux-${arch}.tar.gz" "$tgz" \
    && rm -rf "$OPT_DIR/go" && tar -C "$OPT_DIR" -xzf "$tgz" \
    && ln -sf "$OPT_DIR/go/bin/go" "$BIN_DIR/go" && ln -sf "$OPT_DIR/go/bin/gofmt" "$BIN_DIR/gofmt"
  has go && _mark_ok "go (官方包 $ver)" || _mark_fail go
}

install_rust() {
  if has rustc; then _mark_ok "rust ($(rustc --version 2>&1 | awk '{print $2}'))"; return; fi
  if fetch "https://sh.rustup.rs" "$OPT_DIR/rustup.sh"; then
    sh "$OPT_DIR/rustup.sh" -y --no-modify-path >/dev/null 2>&1
    [ -f "$HOME/.cargo/bin/rustc" ] && ln -sf "$HOME/.cargo/bin/"* "$BIN_DIR/" 2>/dev/null
    ensure_path "$HOME/.cargo/bin"
  fi
  has rustc && _mark_ok "rust (rustup)" || _mark_fail rust
}

install_java() {
  if has java; then _mark_ok "java ($(java -version 2>&1 | head -n1))"; return; fi
  # 常见发行版包名各异，逐一尝试
  for p in default-jdk java-21-openjdk-devel java-latest-openjdk-devel openjdk-21 openjdk21; do
    pkg_install "$p" >/dev/null 2>&1 && has java && break
  done
  has java && _mark_ok java || _mark_fail java
}

install_ruby() {
  if has ruby; then _mark_ok "ruby ($(ruby -v 2>&1 | awk '{print $2}'))"; return; fi
  pkg_install ruby-full || pkg_install ruby
  has ruby && _mark_ok ruby || _mark_fail ruby
}

# ============================ codec：编解码工具 ============================
install_ffmpeg()      { ensure_cmd ffmpeg ffmpeg && _mark_ok ffmpeg || _mark_fail ffmpeg; }
install_imagemagick() {
  if has convert || has magick; then _mark_ok imagemagick; return; fi
  pkg_install imagemagick; (has convert || has magick) && _mark_ok imagemagick || _mark_fail imagemagick
}
install_jq()   { ensure_cmd jq jq && _mark_ok jq || _mark_fail jq; }
install_yq()   {
  if has yq; then _mark_ok yq; return; fi
  # yq(mikefarah) 单文件二进制
  local arch; case "$(uname -m)" in x86_64) arch=amd64;; aarch64|arm64) arch=arm64;; *) arch=amd64;; esac
  fetch "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_${arch}" "$BIN_DIR/yq" \
    && chmod +x "$BIN_DIR/yq"
  has yq && _mark_ok yq || _mark_fail yq
}
install_pandoc()  { ensure_cmd pandoc pandoc && _mark_ok pandoc || _mark_fail pandoc; }
install_7z()      {
  if has 7z || has 7za || has 7zr; then _mark_ok 7z; return; fi
  pkg_install p7zip-full || pkg_install p7zip
  (has 7z || has 7za || has 7zr) && _mark_ok 7z || _mark_fail 7z
}
install_protobuf() {
  if has protoc; then _mark_ok protobuf; return; fi
  pkg_install protobuf-compiler || pkg_install protobuf
  has protoc && _mark_ok protobuf || _mark_fail protobuf
}
install_poppler() { # pdf 工具集：pdftotext / pdfinfo / pdfimages
  if has pdftotext; then _mark_ok poppler; return; fi
  pkg_install poppler-utils || pkg_install poppler
  has pdftotext && _mark_ok poppler || _mark_fail poppler
}
install_xxd() {
  if has xxd; then _mark_ok xxd; return; fi
  pkg_install xxd || pkg_install vim-common || pkg_install vim
  has xxd && _mark_ok xxd || _mark_fail xxd
}

# ============================ reverse：逆向工具 ============================
install_apktool() {
  if has apktool; then _mark_ok apktool; return; fi
  has java || install_java
  local jar="$OPT_DIR/apktool.jar"
  fetch "https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar" "$jar" \
    && make_jar_wrapper apktool "$jar"
  has apktool && _mark_ok "apktool 2.9.3" || _mark_fail apktool
}
install_jadx() {
  if has jadx; then _mark_ok jadx; return; fi
  has java || install_java
  local zip="$OPT_DIR/jadx.zip" ver="1.5.0"
  if fetch "https://github.com/skylot/jadx/releases/download/v${ver}/jadx-${ver}.zip" "$zip"; then
    rm -rf "$OPT_DIR/jadx" && mkdir -p "$OPT_DIR/jadx" \
      && (has unzip || pkg_install unzip) \
      && unzip -oq "$zip" -d "$OPT_DIR/jadx" \
      && ln -sf "$OPT_DIR/jadx/bin/jadx" "$BIN_DIR/jadx" \
      && ln -sf "$OPT_DIR/jadx/bin/jadx-gui" "$BIN_DIR/jadx-gui" 2>/dev/null
  fi
  has jadx && _mark_ok "jadx $ver" || _mark_fail jadx
}
install_dex2jar() {
  if has d2j-dex2jar || has d2j-dex2jar.sh; then _mark_ok dex2jar; return; fi
  has java || install_java
  local zip="$OPT_DIR/dex2jar.zip" ver="2.4" d
  if fetch "https://github.com/pxb1988/dex2jar/releases/download/v${ver}/dex-tools-v${ver}.zip" "$zip"; then
    has unzip || pkg_install unzip
    rm -rf "$OPT_DIR/dex2jar"
    if unzip -oq "$zip" -d "$OPT_DIR/dex2jar"; then
      d="$(find "$OPT_DIR/dex2jar" -maxdepth 1 -type d -name 'dex-tools*' | head -n1)"
      if [ -n "$d" ]; then
        chmod +x "$d"/*.sh 2>/dev/null
        for s in "$d"/d2j-*.sh; do ln -sf "$s" "$BIN_DIR/$(basename "$s" .sh)"; done
      fi
    fi
  fi
  has d2j-dex2jar && _mark_ok "dex2jar $ver" || _mark_fail dex2jar
}
install_radare2() {
  if has r2 || has radare2; then _mark_ok radare2; return; fi
  pkg_install radare2
  (has r2 || has radare2) && _mark_ok radare2 || _mark_fail radare2
}
install_binwalk() {
  if has binwalk; then _mark_ok binwalk; return; fi
  pkg_install binwalk || { has python3 && python3 -m pip install --user binwalk >/dev/null 2>&1; }
  has binwalk && _mark_ok binwalk || _mark_fail binwalk
}
install_frida() {
  if has frida; then _mark_ok frida; return; fi
  has python3 || install_python
  python3 -m pip install --user frida-tools >/dev/null 2>&1
  has frida && _mark_ok "frida-tools" || _mark_fail frida
}

# ============================ vcs：代码平台工具 ============================
install_git()  { ensure_cmd git git && _mark_ok git || _mark_fail git; }
install_curl() { ensure_cmd curl curl && _mark_ok curl || _mark_fail curl; }
install_wget() { ensure_cmd wget wget && _mark_ok wget || _mark_fail wget; }
install_gh() {
  if has gh; then _mark_ok gh; return; fi
  if [ "$PKG_MGR" = apt ]; then
    # GitHub 官方 apt 源
    detect_pkg_mgr
    $SUDO mkdir -p /etc/apt/keyrings 2>/dev/null
    if fetch "https://cli.github.com/packages/githubcli-archive-keyring.gpg" "$OPT_DIR/gh.gpg"; then
      $SUDO install -m 0644 "$OPT_DIR/gh.gpg" /etc/apt/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
      echo "deb [signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        | $SUDO tee /etc/apt/sources.list.d/github-cli.list >/dev/null 2>&1
      _PKG_UPDATED=""; pkg_install gh
    fi
  else
    pkg_install gh || pkg_install github-cli
  fi
  has gh && _mark_ok gh || _mark_fail gh
}
install_glab() {
  if has glab; then _mark_ok glab; return; fi
  local arch ver="1.44.0" tgz; case "$(uname -m)" in x86_64) arch=amd64;; aarch64|arm64) arch=arm64;; *) arch=amd64;; esac
  tgz="$OPT_DIR/glab.tgz"
  if fetch "https://gitlab.com/gitlab-org/cli/-/releases/v${ver}/downloads/glab_${ver}_linux_${arch}.tar.gz" "$tgz"; then
    rm -rf "$OPT_DIR/glab" && mkdir -p "$OPT_DIR/glab" && tar -C "$OPT_DIR/glab" -xzf "$tgz" \
      && ln -sf "$(find "$OPT_DIR/glab" -type f -name glab | head -n1)" "$BIN_DIR/glab"
  fi
  has glab && _mark_ok "glab $ver" || _mark_fail glab
}

# ============================ 分类映射 =====================================
LANG_ITEMS="python node go rust java ruby"
CODEC_ITEMS="ffmpeg imagemagick jq yq pandoc 7z protobuf poppler xxd"
REVERSE_ITEMS="apktool jadx dex2jar radare2 binwalk frida"
VCS_ITEMS="git gh glab curl wget"
ALL_ITEMS="$LANG_ITEMS $CODEC_ITEMS $REVERSE_ITEMS $VCS_ITEMS"

# 把单项名映射到安装函数
install_item() {
  case "$1" in
    python|python3) install_python;;
    node|nodejs)    install_node;;
    go|golang)      install_go;;
    rust|rustc)     install_rust;;
    java|jdk)       install_java;;
    ruby)           install_ruby;;
    ffmpeg)         install_ffmpeg;;
    imagemagick|convert) install_imagemagick;;
    jq)             install_jq;;
    yq)             install_yq;;
    pandoc)         install_pandoc;;
    7z|7zip|p7zip)  install_7z;;
    protobuf|protoc) install_protobuf;;
    poppler|pdftotext) install_poppler;;
    xxd)            install_xxd;;
    apktool)        install_apktool;;
    jadx)           install_jadx;;
    dex2jar)        install_dex2jar;;
    radare2|r2)     install_radare2;;
    binwalk)        install_binwalk;;
    frida)          install_frida;;
    git)            install_git;;
    gh|github)      install_gh;;
    glab|gitlab)    install_glab;;
    curl)           install_curl;;
    wget)           install_wget;;
    *) err "未知项：$1"; _mark_fail "$1"; return 1;;
  esac
}

install_category() {
  case "$1" in
    lang)    step "分类 lang（语言环境）";    for i in $LANG_ITEMS;    do install_item "$i"; done;;
    codec)   step "分类 codec（编解码工具）"; for i in $CODEC_ITEMS;   do install_item "$i"; done;;
    reverse) step "分类 reverse（逆向工具）"; for i in $REVERSE_ITEMS; do install_item "$i"; done;;
    vcs)     step "分类 vcs（代码平台工具）"; for i in $VCS_ITEMS;     do install_item "$i"; done;;
    *) return 1;;
  esac
}

# ============================ doctor / list ================================
DOCTOR=(
  "python3|python3 -V" "node|node -v" "go|go version" "rustc|rustc --version"
  "java|java -version" "ruby|ruby -v"
  "ffmpeg|ffmpeg -version" "convert|convert --version" "jq|jq --version" "yq|yq --version"
  "pandoc|pandoc -v" "7z|7z i" "protoc|protoc --version" "pdftotext|pdftotext -v" "xxd|xxd -v"
  "apktool|apktool --version" "jadx|jadx --version" "d2j-dex2jar|d2j-dex2jar --version"
  "r2|r2 -v" "binwalk|binwalk --help" "frida|frida --version"
  "git|git --version" "gh|gh --version" "glab|glab --version" "curl|curl --version" "wget|wget --version"
)
do_doctor() {
  step "环境自检（doctor）"
  local entry cmd probe
  for entry in "${DOCTOR[@]}"; do
    cmd="${entry%%|*}"; probe="${entry#*|}"
    if has "$cmd"; then
      printf '%b %-14s %s\n' "${C_GREEN}[✓]${C_RESET}" "$cmd" "${C_DIM}$($probe 2>&1 | head -n1)${C_RESET}"
    else
      printf '%b %-14s %s\n' "${C_RED}[ ]${C_RESET}" "$cmd" "${C_DIM}未安装${C_RESET}"
    fi
  done
}

do_list() {
  printf '%b\n' "${C_BOLD}可安装分类与项目：${C_RESET}"
  printf '  %-9s %s\n' "lang"    "$LANG_ITEMS"
  printf '  %-9s %s\n' "codec"   "$CODEC_ITEMS"
  printf '  %-9s %s\n' "reverse" "$REVERSE_ITEMS"
  printf '  %-9s %s\n' "vcs"     "$VCS_ITEMS"
  echo
  echo "示例：setup-environments.sh lang codec   或   setup-environments.sh python ffmpeg gh"
}

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

summary() {
  step "汇总"
  [ ${#DONE[@]}   -gt 0 ] && ok   "成功/已存在（${#DONE[@]}）：${DONE[*]}"
  if [ ${#FAILED[@]} -gt 0 ]; then
    warn "失败/跳过（${#FAILED[@]}）：${FAILED[*]}"
    warn "失败多因网络受限或该发行版无对应包，可稍后单独重试：setup-environments.sh <项目名>"
  fi
  echo
  ok "完成。新装命令若未生效，请执行：source ~/.bashrc  或重新登录 shell。"
}

main() {
  [ $# -eq 0 ] && { usage; exit 0; }
  detect_pkg_mgr || true
  local ran=0
  for arg in "$@"; do
    case "$arg" in
      -h|--help) usage; exit 0;;
      list)      do_list; exit 0;;
      doctor)    do_doctor; exit 0;;
      all)       ran=1; for c in lang codec reverse vcs; do install_category "$c"; done;;
      lang|codec|reverse|vcs) ran=1; install_category "$arg";;
      *) ran=1; install_item "$arg";;
    esac
  done
  [ $ran -eq 1 ] && summary
}

main "$@"
