#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lang_mcp —— 编程语言开发环境的 MCP 服务器。

面向「无头」语言环境的日常操作：查询版本、创建/使用虚拟环境、装依赖、跑代码。
覆盖：python（venv/pip）、node（npm）、go、rust（cargo）、java、ruby。

设计原则：只做**项目级、可复现**的操作；跑任意代码/装依赖有副作用，故都显式命名清楚。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd  # noqa: E402

srv = MCPServer(
    "clenv-lang", "1.0.0",
    instructions="语言开发环境工具集：版本查询、虚拟环境、依赖安装、运行代码。",
)


@srv.tool(
    "versions",
    "汇总报告本机各语言工具链的版本（python/node/go/rust/java/ruby 及包管理器）。"
    "用途：开工前快速核对环境是否齐备。",
    {"type": "object", "properties": {}},
)
def _versions(_a):
    import shutil
    probes = [
        ("python3", ["python3", "-V"]), ("pip3", ["pip3", "--version"]),
        ("node", ["node", "-v"]), ("npm", ["npm", "-v"]),
        ("go", ["go", "version"]), ("cargo", ["cargo", "--version"]),
        ("rustc", ["rustc", "--version"]), ("java", ["java", "-version"]),
        ("ruby", ["ruby", "-v"]),
    ]
    lines = []
    for name, cmd in probes:
        if shutil.which(cmd[0]) is None:
            lines.append("%-8s : 未安装" % name)
        else:
            import subprocess
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                lines.append("%-8s : %s" % (name, (p.stdout or p.stderr).strip().splitlines()[0]))
            except Exception as e:  # noqa: BLE001
                lines.append("%-8s : 探测失败(%s)" % (name, e))
    return "\n".join(lines)


@srv.tool(
    "python_venv_create",
    "在指定目录创建 Python 虚拟环境（python -m venv）。用途：为项目建立隔离依赖环境。"
    "返回后可用 python_pip_install（传相同 venv 路径）装包。",
    {"type": "object",
     "properties": {"path": {"type": "string", "description": "venv 目录，如 .venv"}},
     "required": ["path"]},
)
def _venv_create(a):
    return run_cmd(["python3", "-m", "venv", a["path"]], timeout=120)


@srv.tool(
    "python_pip_install",
    "在指定 venv（或系统 python）中安装 pip 包。venv 传虚拟环境目录则用其中的 pip。"
    "用途：为项目安装依赖。packages 为包名列表。",
    {"type": "object",
     "properties": {
         "packages": {"type": "array", "items": {"type": "string"}},
         "venv": {"type": "string", "description": "venv 目录，可选；不传则用系统 pip --user"}},
     "required": ["packages"]},
)
def _pip_install(a):
    pkgs = list(a.get("packages") or [])
    if not pkgs:
        return "[参数错误] packages 不能为空"
    if a.get("venv"):
        pip = os.path.join(a["venv"], "bin", "pip")
        return run_cmd([pip, "install"] + pkgs, timeout=600)
    return run_cmd(["python3", "-m", "pip", "install", "--user"] + pkgs, timeout=600)


@srv.tool(
    "python_run",
    "用指定 venv（或系统 python）运行一个 Python 脚本文件。args 为脚本参数。用途：执行项目脚本。",
    {"type": "object",
     "properties": {
         "script": {"type": "string"},
         "venv": {"type": "string"},
         "args": {"type": "array", "items": {"type": "string"}}},
     "required": ["script"]},
)
def _py_run(a):
    py = os.path.join(a["venv"], "bin", "python") if a.get("venv") else "python3"
    return run_cmd([py, a["script"]] + list(a.get("args") or []), timeout=300)


@srv.tool(
    "npm_install",
    "在指定项目目录执行 npm install（无参数时按 package.json 装全部；给 packages 则装指定包）。",
    {"type": "object",
     "properties": {
         "cwd": {"type": "string", "description": "项目目录，默认当前"},
         "packages": {"type": "array", "items": {"type": "string"}},
         "dev": {"type": "boolean", "description": "true 则 --save-dev"}},
     "required": []},
)
def _npm_install(a):
    cmd = ["npm", "install"]
    if a.get("dev"):
        cmd.append("--save-dev")
    cmd += list(a.get("packages") or [])
    return run_cmd(cmd, cwd=a.get("cwd") or ".", timeout=600)


@srv.tool(
    "go_build",
    "在项目目录执行 go build（默认 ./...）。用途：编译校验 Go 项目。",
    {"type": "object",
     "properties": {"cwd": {"type": "string"}, "target": {"type": "string"}}},
)
def _go_build(a):
    return run_cmd(["go", "build", a.get("target", "./...")], cwd=a.get("cwd") or ".", timeout=600)


@srv.tool(
    "cargo_build",
    "在 Rust 项目目录执行 cargo build。release=true 走优化构建。用途：编译 Rust 项目。",
    {"type": "object",
     "properties": {"cwd": {"type": "string"}, "release": {"type": "boolean"}}},
)
def _cargo_build(a):
    cmd = ["cargo", "build"]
    if a.get("release"):
        cmd.append("--release")
    return run_cmd(cmd, cwd=a.get("cwd") or ".", timeout=900)


if __name__ == "__main__":
    srv.run()
