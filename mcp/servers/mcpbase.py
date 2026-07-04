#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcpbase —— 纯标准库实现的极简 MCP（Model Context Protocol）服务器框架。

为什么要自己写：本项目要求 MCP 服务器**零第三方依赖**即可运行，只依赖系统自带的
Python 3。这里实现 MCP 的 stdio 传输 + JSON-RPC 2.0 核心方法，足够 Claude Code /
任何 MCP 客户端发现并调用工具。

传输：stdio，按「一行一条 JSON-RPC 消息」（换行分隔）收发。
支持的方法：initialize、notifications/initialized、tools/list、tools/call、ping。

各分类服务器只需：
    srv = MCPServer("clenv-codec", "1.0.0")

    @srv.tool("ffmpeg_convert", "用 ffmpeg 转码音视频…", {输入 JSON Schema})
    def _(args):
        return run_cmd(["ffmpeg", "-i", args["input"], args["output"]])

    srv.run()
"""
import sys
import os
import json
import shutil
import subprocess

PROTOCOL_VERSION = "2024-11-05"


def run_cmd(cmd, timeout=180, input_text=None, cwd=None):
    """执行命令并返回适合放进 MCP 文本结果的字符串。

    cmd 传 list（避免 shell 注入）。返回包含退出码、stdout、stderr 的汇总文本。
    """
    exe = cmd[0]
    if shutil.which(exe) is None:
        return ("[未安装] 命令 `%s` 不在 PATH 中。\n"
                "请先运行：setup-environments.sh %s   或   clenv env install %s"
                % (exe, exe, exe))
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            input=input_text, cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return "[超时] 命令执行超过 %ds：%s" % (timeout, " ".join(cmd))
    except Exception as e:  # noqa: BLE001
        return "[执行失败] %s：%s" % (" ".join(cmd), e)
    out = []
    out.append("$ " + " ".join(cmd))
    out.append("exit=%d" % p.returncode)
    if p.stdout:
        out.append("--- stdout ---\n" + p.stdout.rstrip())
    if p.stderr:
        out.append("--- stderr ---\n" + p.stderr.rstrip())
    return "\n".join(out)


class MCPServer:
    def __init__(self, name, version, instructions=""):
        self.name = name
        self.version = version
        self.instructions = instructions
        self._tools = []  # [{name, description, inputSchema, handler}]

    def tool(self, name, description, input_schema=None):
        """装饰器：注册一个工具。input_schema 为 JSON Schema（object）。"""
        if input_schema is None:
            input_schema = {"type": "object", "properties": {}}

        def deco(fn):
            self._tools.append({
                "name": name,
                "description": description,
                "inputSchema": input_schema,
                "handler": fn,
            })
            return fn
        return deco

    # ---- JSON-RPC 分发 ----
    def _handle(self, msg):
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}

        # 通知（无 id）：仅 initialized，不回响应
        if method == "notifications/initialized":
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
            return self._ok(mid, {"tools": [
                {"name": t["name"], "description": t["description"],
                 "inputSchema": t["inputSchema"]}
                for t in self._tools
            ]})
        if method == "tools/call":
            return self._call_tool(mid, params)
        # 未知方法
        if mid is None:
            return None
        return self._err(mid, -32601, "未知方法：%s" % method)

    def _call_tool(self, mid, params):
        name = params.get("name")
        args = params.get("arguments") or {}
        tool = next((t for t in self._tools if t["name"] == name), None)
        if tool is None:
            return self._err(mid, -32602, "未知工具：%s" % name)
        try:
            text = tool["handler"](args)
            is_error = False
        except Exception as e:  # noqa: BLE001
            text = "[工具内部错误] %s：%s" % (name, e)
            is_error = True
        return self._ok(mid, {
            "content": [{"type": "text", "text": str(text)}],
            "isError": is_error,
        })

    @staticmethod
    def _ok(mid, result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    @staticmethod
    def _err(mid, code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    def run(self):
        """stdio 主循环：逐行读 JSON-RPC，逐行写响应。"""
        stdout = sys.stdout
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            # 支持批量（数组）
            batch = msg if isinstance(msg, list) else [msg]
            for one in batch:
                resp = self._handle(one)
                if resp is not None:
                    stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                    stdout.flush()
