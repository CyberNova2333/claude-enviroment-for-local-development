#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codeplatform_mcp —— 开源代码平台「访问 / 协作」工具的 MCP 服务器。

覆盖：git（本地版本控制）、gh（GitHub CLI）、glab（GitLab CLI）、
以及基于 curl 的通用 REST 只读访问。

安全约定：
  * 默认只做**只读 / 本地**操作；会「留下痕迹」的写操作（push、创建 PR/Issue、评论等）
    统一由 allow_write=true 显式开启，避免 Agent 误触。
  * 不在结果中回显任何令牌；鉴权沿用调用者本机既有的 gh/glab/git 凭证。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd  # noqa: E402

srv = MCPServer(
    "clenv-codeplatform", "1.0.0",
    instructions="Git 与 GitHub/GitLab 访问工具集。写操作需显式 allow_write=true。",
)

_WRITE_HINT = "[已拦截] 该操作会改变远端状态。若确认授权，请传 allow_write=true 再调用。"


@srv.tool(
    "git_status",
    "在指定仓库目录执行 git status（含分支与工作区状态，只读）。",
    {"type": "object", "properties": {"repo": {"type": "string", "description": "仓库路径，默认当前目录"}}},
)
def _git_status(a):
    return run_cmd(["git", "status", "-sb"], cwd=a.get("repo") or ".")


@srv.tool(
    "git_log",
    "查看提交历史（只读）。n 控制条数（默认 20），path 可选限定文件。",
    {"type": "object",
     "properties": {"repo": {"type": "string"}, "n": {"type": "integer"}, "path": {"type": "string"}}},
)
def _git_log(a):
    cmd = ["git", "log", "--oneline", "-n", str(a.get("n", 20))]
    if a.get("path"):
        cmd += ["--", a["path"]]
    return run_cmd(cmd, cwd=a.get("repo") or ".")


@srv.tool(
    "git_diff",
    "查看改动（只读）。staged=true 看已暂存差异；ref 可指定与某提交/分支比较。",
    {"type": "object",
     "properties": {"repo": {"type": "string"}, "staged": {"type": "boolean"}, "ref": {"type": "string"}}},
)
def _git_diff(a):
    cmd = ["git", "diff"]
    if a.get("staged"):
        cmd.append("--cached")
    if a.get("ref"):
        cmd.append(a["ref"])
    return run_cmd(cmd, cwd=a.get("repo") or ".")


@srv.tool(
    "git_clone",
    "克隆仓库到本地（只读拉取，不改远端）。depth 可做浅克隆。用途：把公开仓库拉到本地阅读/比对。",
    {"type": "object",
     "properties": {"url": {"type": "string"}, "dest": {"type": "string"}, "depth": {"type": "integer"}},
     "required": ["url"]},
)
def _git_clone(a):
    cmd = ["git", "clone"]
    if a.get("depth"):
        cmd += ["--depth", str(a["depth"])]
    cmd.append(a["url"])
    if a.get("dest"):
        cmd.append(a["dest"])
    return run_cmd(cmd, timeout=600)


@srv.tool(
    "git_push",
    "把本地提交推送到远端（写操作）。需 allow_write=true。remote 默认 origin，branch 默认当前分支。",
    {"type": "object",
     "properties": {
         "repo": {"type": "string"}, "remote": {"type": "string"}, "branch": {"type": "string"},
         "allow_write": {"type": "boolean"}},
     "required": []},
)
def _git_push(a):
    if not a.get("allow_write"):
        return _WRITE_HINT
    cmd = ["git", "push", a.get("remote", "origin")]
    if a.get("branch"):
        cmd.append(a["branch"])
    return run_cmd(cmd, cwd=a.get("repo") or ".", timeout=300)


@srv.tool(
    "gh_api",
    "用 GitHub CLI 调 REST/GraphQL API（默认 GET，只读）。endpoint 形如 'repos/OWNER/REPO'。"
    "method 非 GET 时视为写操作，需 allow_write=true。用途：查询仓库/Issue/PR/Release 等。",
    {"type": "object",
     "properties": {
         "endpoint": {"type": "string", "description": "如 repos/cli/cli 或 user"},
         "method": {"type": "string", "description": "GET/POST/PATCH/DELETE，默认 GET"},
         "fields": {"type": "object", "description": "写操作的字段键值对，可选"},
         "allow_write": {"type": "boolean"}},
     "required": ["endpoint"]},
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
    "gh_repo_view",
    "用 gh 查看某仓库概况（描述、star、默认分支等，只读）。repo 形如 'owner/name'。",
    {"type": "object", "properties": {"repo": {"type": "string"}}, "required": ["repo"]},
)
def _gh_repo(a):
    return run_cmd(["gh", "repo", "view", a["repo"]], timeout=120)


@srv.tool(
    "glab_api",
    "用 GitLab CLI 调 GitLab API（默认 GET，只读）。endpoint 形如 'projects/:id'。"
    "非 GET 需 allow_write=true。用途：查询 GitLab 项目/MR/Issue 等。",
    {"type": "object",
     "properties": {
         "endpoint": {"type": "string"},
         "method": {"type": "string"},
         "allow_write": {"type": "boolean"}},
     "required": ["endpoint"]},
)
def _glab_api(a):
    method = (a.get("method") or "GET").upper()
    if method != "GET" and not a.get("allow_write"):
        return _WRITE_HINT
    return run_cmd(["glab", "api", "-X", method, a["endpoint"]], timeout=120)


@srv.tool(
    "http_get",
    "用 curl 发起只读 HTTP GET，返回响应头与正文（截断到合理长度）。"
    "用途：访问任意公开 REST API / 原始文件 URL 做只读查询。",
    {"type": "object",
     "properties": {
         "url": {"type": "string"},
         "headers": {"type": "array", "items": {"type": "string"},
                     "description": "额外请求头，如 ['Accept: application/json']"}},
     "required": ["url"]},
)
def _http_get(a):
    cmd = ["curl", "-sSL", "-i", "--max-time", "60"]
    for h in (a.get("headers") or []):
        cmd += ["-H", h]
    cmd.append(a["url"])
    out = run_cmd(cmd, timeout=70)
    return out[:20000]


if __name__ == "__main__":
    srv.run()
