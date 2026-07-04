#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codeplatform_mcp —— 开源代码平台「访问 / 协作」工具的 MCP 服务器。

覆盖（全部免费/开源）：git（本地版本控制）、gh（GitHub CLI）、glab（GitLab CLI）、
curl（通用只读 HTTP）。

安全约定：
  * 默认只做**只读 / 本地**操作；会「留下痕迹」的写操作（push、commit、创建 PR/Issue、
    评论、非 GET API 等）统一需要显式 allow_write=true，避免 Agent 误触。
  * 不接受、也不回显任何令牌明文；鉴权沿用本机既有的 gh/glab/git 凭证。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd  # noqa: E402

RO = {"readOnlyHint": True}
RO_OPEN = {"readOnlyHint": True, "openWorldHint": True}   # 访问外部网络
WRITE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}

srv = MCPServer(
    "clenv-codeplatform", "2.0.0",
    instructions=(
        "Git 与 GitHub/GitLab 访问工具集。默认只读；任何会改变本地历史或远端状态的操作"
        "都需显式 allow_write=true。repo 参数默认当前工作目录。"),
)

_WRITE_HINT = "[已拦截] 该操作会改变本地历史或远端状态。若确认授权，请传 allow_write=true 再调用。"


# ============================ git 只读 ============================
@srv.tool(
    "git_status",
    "查看仓库状态（分支、暂存、未跟踪），git status -sb。只读。",
    {"type": "object", "properties": {"repo": {"type": "string", "description": "仓库路径，默认当前目录", "default": "."}}},
    annotations=dict(RO, title="git 状态"),
    examples=[{"desc": "查看当前仓库", "arguments": {}}],
)
def _git_status(a):
    return run_cmd(["git", "status", "-sb"], cwd=a.get("repo") or ".")


@srv.tool(
    "git_log",
    "查看提交历史（git log --oneline）。n 控制条数，path 限定文件。只读。",
    {"type": "object",
     "properties": {"repo": {"type": "string", "default": "."},
                    "n": {"type": "integer", "default": 20},
                    "path": {"type": "string"}}},
    annotations=dict(RO, title="git 历史"),
    examples=[{"desc": "看最近 10 条", "arguments": {"n": 10}}],
)
def _git_log(a):
    cmd = ["git", "log", "--oneline", "--decorate", "-n", str(a.get("n", 20))]
    if a.get("path"):
        cmd += ["--", a["path"]]
    return run_cmd(cmd, cwd=a.get("repo") or ".")


@srv.tool(
    "git_diff",
    "查看改动（git diff）。staged=true 看已暂存；ref 指定与某提交/分支比较。只读。",
    {"type": "object",
     "properties": {"repo": {"type": "string", "default": "."},
                    "staged": {"type": "boolean", "default": False},
                    "ref": {"type": "string"}}},
    annotations=dict(RO, title="git 差异"),
    examples=[
        {"desc": "工作区差异", "arguments": {}},
        {"desc": "与 main 比较", "arguments": {"ref": "main"}},
    ],
)
def _git_diff(a):
    cmd = ["git", "diff"]
    if a.get("staged"):
        cmd.append("--cached")
    if a.get("ref"):
        cmd.append(a["ref"])
    return run_cmd(cmd, cwd=a.get("repo") or ".")


@srv.tool(
    "git_show",
    "查看某次提交的详情或某文件在某提交处的内容（git show）。target 如 'HEAD'、'<sha>'、'<sha>:path'。只读。",
    {"type": "object",
     "properties": {"repo": {"type": "string", "default": "."},
                    "target": {"type": "string", "default": "HEAD"}}},
    annotations=dict(RO, title="git show"),
    examples=[
        {"desc": "看最新提交", "arguments": {"target": "HEAD"}},
        {"desc": "看历史版本文件", "arguments": {"target": "HEAD~3:README.md"}},
    ],
)
def _git_show(a):
    return run_cmd(["git", "show", a.get("target", "HEAD")], cwd=a.get("repo") or ".")


@srv.tool(
    "git_blame",
    "逐行追溯某文件的最后修改提交/作者（git blame）。start/end 限定行范围。只读。",
    {"type": "object",
     "properties": {"repo": {"type": "string", "default": "."},
                    "path": {"type": "string"},
                    "start": {"type": "integer"}, "end": {"type": "integer"}},
     "required": ["path"]},
    annotations=dict(RO, title="git blame"),
    examples=[{"desc": "看 10-40 行", "arguments": {"path": "app.py", "start": 10, "end": 40}}],
)
def _git_blame(a):
    cmd = ["git", "blame"]
    if a.get("start") and a.get("end"):
        cmd += ["-L", "%d,%d" % (a["start"], a["end"])]
    cmd.append(a["path"])
    return run_cmd(cmd, cwd=a.get("repo") or ".")


@srv.tool(
    "git_grep",
    "在仓库已跟踪文件中按正则搜索（git grep），比全盘 grep 快且自动忽略 .git/。只读。",
    {"type": "object",
     "properties": {"repo": {"type": "string", "default": "."},
                    "pattern": {"type": "string", "description": "要搜索的正则/字符串"}},
     "required": ["pattern"]},
    annotations=dict(RO, title="git 搜索"),
    examples=[{"desc": "找 TODO", "arguments": {"pattern": "TODO"}}],
)
def _git_grep(a):
    return run_cmd(["git", "grep", "-n", "-I", a["pattern"]], cwd=a.get("repo") or ".")


@srv.tool(
    "git_branch_list",
    "列出本地与远端分支及当前分支（git branch -a）。只读。",
    {"type": "object", "properties": {"repo": {"type": "string", "default": "."}}},
    annotations=dict(RO, title="分支列表"),
    examples=[{"desc": "列分支", "arguments": {}}],
)
def _git_branch(a):
    return run_cmd(["git", "branch", "-a", "-vv"], cwd=a.get("repo") or ".")


@srv.tool(
    "git_clone",
    "克隆仓库到本地（只读拉取，不改远端）。depth 做浅克隆。用途：把公开仓库拉下来阅读/比对。",
    {"type": "object",
     "properties": {"url": {"type": "string"}, "dest": {"type": "string"},
                    "depth": {"type": "integer", "description": "浅克隆深度，如 1"}},
     "required": ["url"]},
    annotations=dict(RO_OPEN, title="克隆仓库"),
    examples=[{"desc": "浅克隆", "arguments": {"url": "https://github.com/cli/cli.git", "depth": 1}}],
)
def _git_clone(a):
    cmd = ["git", "clone"]
    if a.get("depth"):
        cmd += ["--depth", str(a["depth"])]
    cmd.append(a["url"])
    if a.get("dest"):
        cmd.append(a["dest"])
    return run_cmd(cmd, timeout=600)


# ============================ git 写操作（需授权） ============================
@srv.tool(
    "git_commit",
    "在指定仓库创建提交（git commit）。需 allow_write=true。add_all=true 先 git add -A。message 为提交信息。",
    {"type": "object",
     "properties": {
         "repo": {"type": "string", "default": "."},
         "message": {"type": "string"},
         "add_all": {"type": "boolean", "default": False},
         "allow_write": {"type": "boolean", "default": False}},
     "required": ["message"]},
    annotations={"readOnlyHint": False, "destructiveHint": False, "title": "git 提交"},
    examples=[{"desc": "提交全部改动", "arguments": {"message": "修复空指针", "add_all": True, "allow_write": True}}],
)
def _git_commit(a):
    if not a.get("allow_write"):
        return _WRITE_HINT
    repo = a.get("repo") or "."
    if a.get("add_all"):
        r = run_cmd(["git", "add", "-A"], cwd=repo)
        if "exit=0" not in r:
            return r
    return run_cmd(["git", "commit", "-m", a["message"]], cwd=repo)


@srv.tool(
    "git_push",
    "把本地提交推送到远端（git push）。需 allow_write=true。remote 默认 origin，branch 默认当前分支。",
    {"type": "object",
     "properties": {
         "repo": {"type": "string", "default": "."},
         "remote": {"type": "string", "default": "origin"},
         "branch": {"type": "string"},
         "allow_write": {"type": "boolean", "default": False}},
     "required": []},
    annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True, "title": "git 推送"},
    examples=[{"desc": "推送到 origin main", "arguments": {"remote": "origin", "branch": "main", "allow_write": True}}],
)
def _git_push(a):
    if not a.get("allow_write"):
        return _WRITE_HINT
    cmd = ["git", "push", a.get("remote", "origin")]
    if a.get("branch"):
        cmd.append(a["branch"])
    return run_cmd(cmd, cwd=a.get("repo") or ".", timeout=300)


# ============================ GitHub / GitLab ============================
@srv.tool(
    "gh_repo_view",
    "查看 GitHub 仓库概况（gh repo view，只读）。repo 形如 'owner/name'。",
    {"type": "object", "properties": {"repo": {"type": "string"}}, "required": ["repo"]},
    annotations=dict(RO_OPEN, title="查看 GitHub 仓库"),
    examples=[{"desc": "看 cli/cli", "arguments": {"repo": "cli/cli"}}],
)
def _gh_repo(a):
    return run_cmd(["gh", "repo", "view", a["repo"]], timeout=120)


@srv.tool(
    "gh_list",
    "列出某 GitHub 仓库的 issues 或 pull requests（gh，只读）。kind=issue|pr，state=open|closed|all。",
    {"type": "object",
     "properties": {
         "repo": {"type": "string", "description": "owner/name"},
         "kind": {"type": "string", "enum": ["issue", "pr"], "default": "issue"},
         "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
         "limit": {"type": "integer", "default": 20}},
     "required": ["repo"]},
    annotations=dict(RO_OPEN, title="列 Issue/PR"),
    examples=[
        {"desc": "列开放 issue", "arguments": {"repo": "cli/cli"}},
        {"desc": "列已合并 PR", "arguments": {"repo": "cli/cli", "kind": "pr", "state": "all"}},
    ],
)
def _gh_list(a):
    sub = "issue" if a.get("kind", "issue") == "issue" else "pr"
    return run_cmd(["gh", sub, "list", "-R", a["repo"], "--state", a.get("state", "open"),
                    "-L", str(a.get("limit", 20))], timeout=120)


@srv.tool(
    "gh_api",
    "用 GitHub CLI 调 REST/GraphQL API（gh api）。默认 GET（只读）；method 非 GET 需 allow_write=true。"
    "endpoint 形如 'repos/OWNER/REPO'、'user'、'repos/OWNER/REPO/issues'。",
    {"type": "object",
     "properties": {
         "endpoint": {"type": "string"},
         "method": {"type": "string", "enum": ["GET", "POST", "PATCH", "PUT", "DELETE"], "default": "GET"},
         "fields": {"type": "object", "description": "写操作字段键值对，可选"},
         "allow_write": {"type": "boolean", "default": False}},
     "required": ["endpoint"]},
    annotations=dict(RO_OPEN, title="GitHub API"),
    examples=[{"desc": "查仓库元数据", "arguments": {"endpoint": "repos/cli/cli"}}],
)
def _gh_api(a):
    method = (a.get("method") or "GET").upper()
    if method != "GET" and not a.get("allow_write"):
        return _WRITE_HINT
    cmd = ["gh", "api", "-X", method, a["endpoint"]]
    for k, v in (a.get("fields") or {}).items():
        cmd += ["-f", "%s=%s" % (k, v)]
    return run_cmd(cmd, timeout=120)


@srv.tool(
    "glab_api",
    "用 GitLab CLI 调 GitLab API（glab api）。默认 GET（只读）；非 GET 需 allow_write=true。"
    "endpoint 形如 'projects/:id'、'user'。",
    {"type": "object",
     "properties": {
         "endpoint": {"type": "string"},
         "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
         "allow_write": {"type": "boolean", "default": False}},
     "required": ["endpoint"]},
    annotations=dict(RO_OPEN, title="GitLab API"),
    examples=[{"desc": "看当前用户", "arguments": {"endpoint": "user"}}],
)
def _glab_api(a):
    method = (a.get("method") or "GET").upper()
    if method != "GET" and not a.get("allow_write"):
        return _WRITE_HINT
    return run_cmd(["glab", "api", "-X", method, a["endpoint"]], timeout=120)


@srv.tool(
    "http_get",
    "发起只读 HTTP GET（curl），返回响应头与正文（截断）。用途：访问任意公开 REST API / 原始文件 URL。",
    {"type": "object",
     "properties": {
         "url": {"type": "string"},
         "headers": {"type": "array", "items": {"type": "string"},
                     "description": "额外请求头，如 ['Accept: application/json']"}},
     "required": ["url"]},
    annotations=dict(RO_OPEN, title="HTTP GET"),
    examples=[{"desc": "取 JSON", "arguments": {"url": "https://api.github.com/repos/cli/cli",
                                              "headers": ["Accept: application/json"]}}],
)
def _http_get(a):
    cmd = ["curl", "-sSL", "-i", "--max-time", "60"]
    for h in (a.get("headers") or []):
        cmd += ["-H", h]
    cmd.append(a["url"])
    return run_cmd(cmd, timeout=70)


if __name__ == "__main__":
    srv.run()
