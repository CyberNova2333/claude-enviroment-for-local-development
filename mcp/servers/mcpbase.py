#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcpbase —— 纯标准库实现的 MCP（Model Context Protocol）服务器框架。

为什么自己写：本项目要求 MCP 服务器**零第三方依赖**，只依赖系统自带的 python3。
这里实现 MCP 的 stdio 传输 + JSON-RPC 2.0，并额外做了「让模型更容易正确调用工具」
与「健壮性」两方面的增强：

1. 让模型更好调用：
   - 每个工具可带结构化 `examples`（会自动拼进 description，模型能看到具体入参 JSON）；
   - 每个工具可带 `annotations`（readOnlyHint / destructiveHint / idempotentHint 等），
     客户端据此判断是否只读、是否危险；
   - inputSchema 建议给每个字段写 description / examples / default / enum。

2. 健壮性：
   - tools/call 前按 inputSchema.required 校验必填参数，缺失即返回清晰错误（不抛栈）；
   - run_cmd 统一：命令未安装给出安装指引、输入路径不存在提前拦截、超时可控、
     输出超长自动截断（避免刷爆上下文）、异常一律兜底为文本；
   - 主循环对 BrokenPipe / 非法 JSON / 非字符串返回值都做兜底，服务器不因单条消息崩溃。
"""
import sys
import os
import io
import json
import shutil
import subprocess

PROTOCOL_VERSION = "2024-11-05"

# 单条工具结果最大字符数（超出截断）。可用环境变量覆盖。
MAX_OUTPUT_CHARS = int(os.environ.get("CLENV_MCP_MAX_OUTPUT", "40000"))

# 命令名 -> 安装用的 clenv/ setup 项名（供未安装时给出精准指引）
INSTALL_HINT = {
    "ffprobe": "ffmpeg", "ffmpeg": "ffmpeg",
    "magick": "imagemagick", "convert": "imagemagick", "identify": "imagemagick",
    "jq": "jq", "yq": "yq", "pandoc": "pandoc",
    "7z": "7z", "7za": "7z", "7zr": "7z",
    "protoc": "protobuf", "pdftotext": "poppler", "pdfinfo": "poppler",
    "xxd": "xxd", "exiftool": "exiftool", "tesseract": "tesseract",
    "sqlite3": "sqlite3", "mediainfo": "mediainfo", "file": "file",
    "strings": "binutils", "objdump": "binutils", "nm": "binutils", "readelf": "binutils",
    "gdb": "gdb", "checksec": "checksec",
    "apktool": "apktool", "jadx": "jadx", "d2j-dex2jar": "dex2jar",
    "r2": "radare2", "radare2": "radare2", "binwalk": "binwalk", "frida": "frida",
    "git": "git", "gh": "gh", "glab": "glab", "curl": "curl", "wget": "wget",
    "go": "go", "cargo": "rust", "rustc": "rust", "node": "node", "npm": "node",
    "python3": "python", "ruby": "ruby", "java": "java", "javac": "java",
    "shellcheck": "shellcheck", "ruff": "ruff",
}


def which(name):
    return shutil.which(name)


def not_installed_msg(exe):
    item = INSTALL_HINT.get(exe, exe)
    return ("[未安装] 命令 `%s` 不在 PATH 中。\n"
            "安装：clenv env install %s   或   setup-environments.sh %s\n"
            "装好后如仍找不到，执行 `source ~/.bashrc` 或重开终端。"
            % (exe, item, item))


def run_cmd(cmd, timeout=180, input_text=None, cwd=None, check_paths=None,
            max_chars=None, env_extra=None):
    """执行命令并返回适合放进 MCP 文本结果的字符串。

    cmd        list 形式（避免 shell 注入）。
    check_paths 需在执行前存在的输入文件/目录列表；缺失则提前返回清晰错误。
    max_chars  输出截断阈值，默认 MAX_OUTPUT_CHARS。
    """
    if not cmd:
        return "[参数错误] 空命令。"
    exe = cmd[0]
    if which(exe) is None:
        return not_installed_msg(exe)
    # 输入路径预检
    for p in (check_paths or []):
        if p and not os.path.exists(p):
            return "[路径不存在] %s\n（请确认路径相对当前工作目录 %s 是否正确）" % (p, os.getcwd())
    if cwd and not os.path.isdir(cwd):
        return "[目录不存在] cwd=%s" % cwd
    env = None
    if env_extra:
        env = dict(os.environ)
        env.update({k: str(v) for k, v in env_extra.items()})
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            input=input_text, cwd=cwd, env=env, errors="replace",
        )
    except subprocess.TimeoutExpired:
        return "[超时] 命令执行超过 %ds 被终止：%s" % (timeout, " ".join(map(str, cmd)))
    except FileNotFoundError:
        return not_installed_msg(exe)
    except Exception as e:  # noqa: BLE001
        return "[执行失败] %s：%s" % (" ".join(map(str, cmd)), e)

    out = ["$ " + " ".join(map(str, cmd)), "exit=%d" % p.returncode]
    if p.stdout:
        out.append("--- stdout ---\n" + p.stdout.rstrip())
    if p.stderr:
        out.append("--- stderr ---\n" + p.stderr.rstrip())
    if p.returncode != 0 and not p.stdout and not p.stderr:
        out.append("（命令无输出，退出码非 0；可能是参数不被接受或目标为空）")
    return _truncate("\n".join(out), max_chars or MAX_OUTPUT_CHARS)


def _truncate(text, limit):
    if len(text) <= limit:
        return text
    head = text[: int(limit * 0.85)]
    tail = text[-int(limit * 0.1):]
    omitted = len(text) - len(head) - len(tail)
    return ("%s\n\n... [输出过长，已省略中间 %d 字符；如需完整结果请缩小范围或加过滤条件] ...\n\n%s"
            % (head, omitted, tail))


class MCPServer:
    def __init__(self, name, version, instructions=""):
        self.name = name
        self.version = version
        self.instructions = instructions
        self._tools = []  # [{name, description, inputSchema, annotations, handler}]

    def tool(self, name, description, input_schema=None, annotations=None, examples=None):
        """注册工具（装饰器）。

        description  自然语言用途；建议写清「做什么/何时用/注意点」。
        input_schema JSON Schema（object）；给每个字段写 description / default / enum / examples。
        annotations  dict，可含 readOnlyHint/destructiveHint/idempotentHint/openWorldHint/title。
        examples     [{"desc": "...", "arguments": {...}}]；会自动拼进 description，
                     让模型看到具体入参 JSON，显著降低调用出错率。
        """
        if input_schema is None:
            input_schema = {"type": "object", "properties": {}}
        full_desc = description
        if examples:
            lines = ["", "调用示例："]
            for ex in examples:
                lines.append("· %s → %s" % (
                    ex.get("desc", ""),
                    json.dumps(ex.get("arguments", {}), ensure_ascii=False)))
            full_desc = description + "\n" + "\n".join(lines)

        def deco(fn):
            entry = {
                "name": name,
                "description": full_desc,
                "inputSchema": input_schema,
                "handler": fn,
            }
            if annotations:
                entry["annotations"] = annotations
            self._tools.append(entry)
            return fn
        return deco

    # ---- JSON-RPC 分发 ----
    def _handle(self, msg):
        if not isinstance(msg, dict):
            return None
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}

        if method == "notifications/initialized":
            return None
        if isinstance(method, str) and method.startswith("notifications/"):
            return None
        if method == "initialize":
            return self._ok(mid, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.name, "version": self.version},
                "instructions": self.instructions,
            })
        if method == "ping":
            return self._ok(mid, {})
        if method == "tools/list":
            listed = []
            for t in self._tools:
                item = {"name": t["name"], "description": t["description"],
                        "inputSchema": t["inputSchema"]}
                if "annotations" in t:
                    item["annotations"] = t["annotations"]
                listed.append(item)
            return self._ok(mid, {"tools": listed})
        if method == "tools/call":
            return self._call_tool(mid, params)
        if mid is None:
            return None
        return self._err(mid, -32601, "未知方法：%s" % method)

    def _call_tool(self, mid, params):
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            return self._tool_error(mid, "arguments 必须是对象（键值对），实际为 %s" % type(args).__name__)
        tool = next((t for t in self._tools if t["name"] == name), None)
        if tool is None:
            names = ", ".join(t["name"] for t in self._tools)
            return self._tool_error(mid, "未知工具：%s。本服务器可用工具：%s" % (name, names))
        # 必填参数校验
        required = (tool["inputSchema"] or {}).get("required") or []
        missing = [k for k in required if k not in args or args[k] in (None, "")]
        if missing:
            return self._tool_error(
                mid, "缺少必填参数：%s。请对照该工具 inputSchema 补全后重试。" % ", ".join(missing))
        try:
            text = tool["handler"](args)
            is_error = False
        except Exception as e:  # noqa: BLE001
            text = "[工具内部错误] %s：%s" % (name, e)
            is_error = True
        if not isinstance(text, str):
            try:
                text = json.dumps(text, ensure_ascii=False, indent=2)
            except Exception:  # noqa: BLE001
                text = str(text)
        text = _truncate(text, MAX_OUTPUT_CHARS)
        return self._ok(mid, {"content": [{"type": "text", "text": text}], "isError": is_error})

    def _tool_error(self, mid, message):
        # 以「工具结果 isError」而非 JSON-RPC error 返回，模型能读到并自我纠正
        return self._ok(mid, {"content": [{"type": "text", "text": "[参数错误] " + message}],
                              "isError": True})

    @staticmethod
    def _ok(mid, result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    @staticmethod
    def _err(mid, code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    def run(self):
        """stdio 主循环：逐行读 JSON-RPC，逐行写响应；单条异常不影响整体。"""
        # 确保 UTF-8 输出
        try:
            out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", write_through=True)
        except Exception:  # noqa: BLE001
            out = sys.stdout
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            batch = msg if isinstance(msg, list) else [msg]
            for one in batch:
                try:
                    resp = self._handle(one)
                except Exception as e:  # noqa: BLE001
                    mid = one.get("id") if isinstance(one, dict) else None
                    resp = self._err(mid, -32603, "内部错误：%s" % e) if mid is not None else None
                if resp is not None:
                    try:
                        out.write(json.dumps(resp, ensure_ascii=False) + "\n")
                        out.flush()
                    except BrokenPipeError:
                        return
