#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lang_mcp —— 编程语言开发环境的 MCP 服务器。

面向「无头」语言环境的日常操作：查版本、跑内联代码、建虚拟环境、装依赖、编译、测试、
静态检查。覆盖（全部免费/开源）：python(venv/pip/pytest/ruff)、node(npm)、go、rust(cargo)、
以及通用「内联代码执行」。

设计原则：只做项目级、可复现的操作；跑代码/装依赖有副作用，故都显式命名清楚并标注。
"""
import os
import sys
import shutil
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd, which  # noqa: E402

RO = {"readOnlyHint": True, "openWorldHint": False}
EXEC = {"readOnlyHint": False, "destructiveHint": False}  # 有副作用但不破坏

srv = MCPServer(
    "clenv-lang", "2.0.0",
    instructions=(
        "语言开发环境工具集。先用 versions 看装了什么；跑一小段逻辑用 run_code；"
        "项目级构建/测试用对应 *_build / *_test / pytest_run。装依赖优先在 venv 内。"),
)

# 内联执行支持的语言 -> (可执行, 文件后缀, 运行方式)
_RUNNERS = {
    "python": ("python3", ".py", lambda exe, f: [exe, f]),
    "node": ("node", ".js", lambda exe, f: [exe, f]),
    "ruby": ("ruby", ".rb", lambda exe, f: [exe, f]),
    "bash": ("bash", ".sh", lambda exe, f: [exe, f]),
}


@srv.tool(
    "versions",
    "汇总报告本机各语言工具链版本（python/pip、node/npm、go、cargo/rustc、java、ruby）。开工前核对环境。只读。",
    {"type": "object", "properties": {}},
    annotations=dict(RO, title="工具链版本"),
    examples=[{"desc": "查看全部版本", "arguments": {}}],
)
def _versions(_a):
    probes = [
        ("python3", ["python3", "-V"]), ("pip3", ["pip3", "--version"]),
        ("node", ["node", "-v"]), ("npm", ["npm", "-v"]),
        ("go", ["go", "version"]), ("cargo", ["cargo", "--version"]),
        ("rustc", ["rustc", "--version"]), ("java", ["java", "-version"]),
        ("ruby", ["ruby", "-v"]), ("ruff", ["ruff", "--version"]),
        ("pytest", ["pytest", "--version"]),
    ]
    lines = []
    for name, cmd in probes:
        if which(cmd[0]) is None:
            lines.append("%-8s : 未安装" % name)
            continue
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, errors="replace")
            txt = (p.stdout or p.stderr).strip().splitlines()
            lines.append("%-8s : %s" % (name, txt[0] if txt else "?"))
        except Exception as e:  # noqa: BLE001
            lines.append("%-8s : 探测失败(%s)" % (name, e))
    return "\n".join(lines)


@srv.tool(
    "run_code",
    "把一小段内联代码写入临时文件并执行，返回 stdout/stderr。支持 python/node/ruby/bash。"
    "用途：快速验证一段逻辑、做计算、跑一次性脚本，无需先落文件。stdin 可选传标准输入。",
    {"type": "object",
     "properties": {
         "lang": {"type": "string", "enum": ["python", "node", "ruby", "bash"]},
         "code": {"type": "string", "description": "源码文本"},
         "stdin": {"type": "string", "description": "喂给程序的标准输入，可选"},
         "timeout": {"type": "integer", "description": "秒，默认 30", "default": 30}},
     "required": ["lang", "code"]},
    annotations=dict(EXEC, title="执行内联代码"),
    examples=[
        {"desc": "python 计算", "arguments": {"lang": "python", "code": "print(sum(range(10)))"}},
        {"desc": "node 打印", "arguments": {"lang": "node", "code": "console.log(process.version)"}},
    ],
)
def _run_code(a):
    lang = a["lang"]
    spec = _RUNNERS.get(lang)
    if not spec:
        return "[参数错误] 不支持的语言：%s（可选 %s）" % (lang, "/".join(_RUNNERS))
    exe, suffix, build = spec
    if which(exe) is None:
        from mcpbase import not_installed_msg
        return not_installed_msg(exe)
    fd, path = tempfile.mkstemp(suffix=suffix, prefix="clenv_run_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(a["code"])
        return run_cmd(build(exe, path), input_text=a.get("stdin"),
                       timeout=int(a.get("timeout", 30)))
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@srv.tool(
    "python_venv_create",
    "创建 Python 虚拟环境（python -m venv）。之后 python_pip_install/python_run 传相同 venv 复用。",
    {"type": "object",
     "properties": {"path": {"type": "string", "description": "venv 目录，如 .venv"}},
     "required": ["path"]},
    annotations=dict(EXEC, title="创建 venv"),
    examples=[{"desc": "建 .venv", "arguments": {"path": ".venv"}}],
)
def _venv_create(a):
    return run_cmd(["python3", "-m", "venv", a["path"]], timeout=120)


@srv.tool(
    "python_pip_install",
    "在指定 venv（或系统 pip --user）安装 pip 包。venv 传虚拟环境目录则用其中的 pip。",
    {"type": "object",
     "properties": {
         "packages": {"type": "array", "items": {"type": "string"}},
         "venv": {"type": "string", "description": "venv 目录，可选"}},
     "required": ["packages"]},
    annotations=dict(EXEC, title="pip 安装"),
    examples=[{"desc": "在 venv 装 requests", "arguments": {"packages": ["requests"], "venv": ".venv"}}],
)
def _pip_install(a):
    pkgs = [str(x) for x in (a.get("packages") or [])]
    if not pkgs:
        return "[参数错误] packages 不能为空"
    if a.get("venv"):
        pip = os.path.join(a["venv"], "bin", "pip")
        return run_cmd([pip, "install"] + pkgs, timeout=600)
    return run_cmd(["python3", "-m", "pip", "install", "--user"] + pkgs, timeout=600)


@srv.tool(
    "python_run",
    "用指定 venv（或系统 python）运行一个 Python 脚本文件。args 为脚本参数。",
    {"type": "object",
     "properties": {
         "script": {"type": "string"},
         "venv": {"type": "string"},
         "args": {"type": "array", "items": {"type": "string"}}},
     "required": ["script"]},
    annotations=dict(EXEC, title="运行 Python 脚本"),
    examples=[{"desc": "在 venv 里跑", "arguments": {"script": "main.py", "venv": ".venv"}}],
)
def _py_run(a):
    py = os.path.join(a["venv"], "bin", "python") if a.get("venv") else "python3"
    return run_cmd([py, a["script"]] + [str(x) for x in (a.get("args") or [])],
                   check_paths=[a["script"]], timeout=300)


@srv.tool(
    "pytest_run",
    "在项目目录运行 pytest（可指定路径/表达式）。用途：跑单元测试。",
    {"type": "object",
     "properties": {
         "cwd": {"type": "string", "default": "."},
         "target": {"type": "string", "description": "测试路径或节点，如 tests/ 或 tests/test_x.py::test_a"},
         "k": {"type": "string", "description": "-k 表达式，按名过滤"}},
     "required": []},
    annotations=dict(EXEC, title="运行 pytest"),
    examples=[
        {"desc": "跑全部", "arguments": {}},
        {"desc": "只跑某目录", "arguments": {"target": "tests/"}},
    ],
)
def _pytest(a):
    cmd = ["pytest", "-q"]
    if a.get("target"):
        cmd.append(a["target"])
    if a.get("k"):
        cmd += ["-k", a["k"]]
    return run_cmd(cmd, cwd=a.get("cwd") or ".", timeout=600)


@srv.tool(
    "python_lint",
    "用 ruff 对 Python 代码做静态检查（ruff check）。fix=true 时自动修可修项。用途：查风格/潜在错误。",
    {"type": "object",
     "properties": {
         "path": {"type": "string", "default": "."},
         "fix": {"type": "boolean", "default": False}},
     "required": []},
    annotations={"readOnlyHint": False, "destructiveHint": False, "title": "ruff 检查"},
    examples=[{"desc": "检查当前目录", "arguments": {}}],
)
def _lint(a):
    cmd = ["ruff", "check"]
    if a.get("fix"):
        cmd.append("--fix")
    cmd.append(a.get("path", "."))
    return run_cmd(cmd, timeout=180)


@srv.tool(
    "npm_install",
    "在项目目录执行 npm install（无 packages 时按 package.json 装全部）。",
    {"type": "object",
     "properties": {
         "cwd": {"type": "string", "default": "."},
         "packages": {"type": "array", "items": {"type": "string"}},
         "dev": {"type": "boolean", "default": False, "description": "true 则 --save-dev"}},
     "required": []},
    annotations=dict(EXEC, title="npm 安装"),
    examples=[{"desc": "装开发依赖", "arguments": {"packages": ["eslint"], "dev": True}}],
)
def _npm_install(a):
    cmd = ["npm", "install"]
    if a.get("dev"):
        cmd.append("--save-dev")
    cmd += [str(x) for x in (a.get("packages") or [])]
    return run_cmd(cmd, cwd=a.get("cwd") or ".", timeout=600)


@srv.tool(
    "npm_script",
    "运行 package.json 里的某个 npm 脚本（npm run <script>）。用途：build/test/lint 等。",
    {"type": "object",
     "properties": {"cwd": {"type": "string", "default": "."}, "script": {"type": "string"}},
     "required": ["script"]},
    annotations=dict(EXEC, title="npm run"),
    examples=[{"desc": "跑 build", "arguments": {"script": "build"}}],
)
def _npm_script(a):
    return run_cmd(["npm", "run", a["script"]], cwd=a.get("cwd") or ".", timeout=600)


@srv.tool(
    "go_build",
    "在项目目录执行 go build（默认 ./...）。用途：编译校验 Go 项目。",
    {"type": "object",
     "properties": {"cwd": {"type": "string", "default": "."}, "target": {"type": "string", "default": "./..."}}},
    annotations=dict(EXEC, title="go build"),
    examples=[{"desc": "编译全部", "arguments": {}}],
)
def _go_build(a):
    return run_cmd(["go", "build", a.get("target", "./...")], cwd=a.get("cwd") or ".", timeout=600)


@srv.tool(
    "go_test",
    "在项目目录执行 go test（默认 ./...）。用途：跑 Go 测试。",
    {"type": "object",
     "properties": {"cwd": {"type": "string", "default": "."}, "target": {"type": "string", "default": "./..."}}},
    annotations=dict(EXEC, title="go test"),
    examples=[{"desc": "测全部", "arguments": {}}],
)
def _go_test(a):
    return run_cmd(["go", "test", a.get("target", "./...")], cwd=a.get("cwd") or ".", timeout=600)


@srv.tool(
    "cargo_build",
    "在 Rust 项目目录执行 cargo build。release=true 走优化构建。",
    {"type": "object",
     "properties": {"cwd": {"type": "string", "default": "."}, "release": {"type": "boolean", "default": False}}},
    annotations=dict(EXEC, title="cargo build"),
    examples=[{"desc": "release 构建", "arguments": {"release": True}}],
)
def _cargo_build(a):
    cmd = ["cargo", "build"]
    if a.get("release"):
        cmd.append("--release")
    return run_cmd(cmd, cwd=a.get("cwd") or ".", timeout=900)


@srv.tool(
    "cargo_test",
    "在 Rust 项目目录执行 cargo test。用途：跑 Rust 测试。",
    {"type": "object", "properties": {"cwd": {"type": "string", "default": "."}}},
    annotations=dict(EXEC, title="cargo test"),
    examples=[{"desc": "跑测试", "arguments": {}}],
)
def _cargo_test(a):
    return run_cmd(["cargo", "test"], cwd=a.get("cwd") or ".", timeout=900)


if __name__ == "__main__":
    srv.run()
