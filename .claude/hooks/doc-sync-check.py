#!/usr/bin/env python3
# Claude Code PreToolUse 钩子（matcher: Bash）—— 提交前「代码/文档同步」检查。
#
# 规则：本次 git commit 将纳入的改动里，若含「命令/工具/MCP 代码」却无任何「文档」改动，
# 则阻止提交（exit 2，提示反馈给 Claude），要求补文档；确需跳过时在提交信息里加标记
# [skip-doc-check]。
#
# 健壮性：任何内部异常一律放行（exit 0, fail-open）—— 钩子自身绝不能挡住正常工作。
import sys
import json
import subprocess
import re
import shlex

# 「代码」：改这些会影响用户可见行为/接口
CODE = re.compile(r'^(scripts/|bin/|mcp/servers/|install\.sh)')
# 「文档」：与上面变化对应的说明
DOCS = re.compile(r'^(mcp/docs/|mcp/README\.md|README\.md|templates/|(\.claude/)?CLAUDE\.md)')


def git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True,
                              text=True, timeout=10).stdout
    except Exception:
        return ""


def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if "git commit" not in cmd:
        return 0
    if "[skip-doc-check]" in cmd:
        return 0

    files = set()
    # 1) 已暂存
    for ln in git("diff", "--cached", "--name-only").splitlines():
        if ln.strip():
            files.add(ln.strip())
    # 2) 命令里内联的 `git add ...`
    if "git add" in cmd:
        for seg in re.split(r'&&|\|\||;|\n', cmd):
            idx = seg.find("git add")
            if idx < 0:
                continue
            try:
                toks = shlex.split(seg[idx:])[2:]
            except Exception:
                continue
            if any(t in (".", "-A", "--all", "-Av", ":/") for t in toks):
                for ln in git("status", "--porcelain").splitlines():
                    p = ln[3:].strip()
                    if p:
                        files.add(p)
            else:
                for t in toks:
                    if not t.startswith("-"):
                        files.add(t)
    # 3) git commit -a / -am / --all
    if (" --all" in cmd) or re.search(r'commit[^\n;&|]*\s-[A-Za-z]*a[A-Za-z]*\b', cmd):
        for ln in git("diff", "--name-only").splitlines():
            if ln.strip():
                files.add(ln.strip())

    code = sorted(f for f in files if CODE.match(f))
    docs = sorted(f for f in files if DOCS.match(f))
    if code and not docs:
        sys.stderr.write(
            "⛔ 文档同步检查未通过：本次提交改了命令/工具/MCP 代码但没有任何文档改动。\n"
            "改动的代码：\n  " + "\n  ".join(code) + "\n\n"
            "请对照 .claude/CLAUDE.md 的「代码 → 文档对照表」补齐 README/mcp/docs 等文档后再提交。\n"
            "若本次确实无需文档（纯重构/修 typo），在提交信息里加标记 [skip-doc-check] 即可跳过。\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open
