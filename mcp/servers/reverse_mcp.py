#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reverse_mcp —— 各平台应用/APP「逆向工程」工具的 MCP 服务器。

覆盖：apktool（APK 反编译资源/smali）、jadx（Dex→Java 反编译）、
dex2jar（Dex→Jar）、radare2（二进制分析）、binwalk（固件/文件雕刻）、
frida（动态插桩，需目标进程/设备）。

⚠️ 合规提示：这些工具仅用于**你有合法授权**的安全研究、CTF、教学、兼容性分析等场景。
本服务器只是把命令行封装为 MCP 工具，是否合规由使用者负责。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd  # noqa: E402

srv = MCPServer(
    "clenv-reverse", "1.0.0",
    instructions="APP/二进制逆向工具集，仅限授权场景使用。",
)


@srv.tool(
    "apktool_decode",
    "用 apktool 反编译 APK：还原资源文件、AndroidManifest.xml 与 smali 代码到输出目录。"
    "用途：分析 Android 应用的资源与逻辑结构。",
    {"type": "object",
     "properties": {
         "apk": {"type": "string", "description": "APK 文件路径"},
         "out_dir": {"type": "string", "description": "输出目录，可选，默认同名目录"},
         "no_src": {"type": "boolean", "description": "true 则只解资源不反汇编 smali，加快速度"}},
     "required": ["apk"]},
)
def _apktool_d(a):
    cmd = ["apktool", "d", "-f", a["apk"]]
    if a.get("out_dir"):
        cmd += ["-o", a["out_dir"]]
    if a.get("no_src"):
        cmd.append("-s")
    return run_cmd(cmd, timeout=600)


@srv.tool(
    "apktool_build",
    "用 apktool b 把反编译目录重新打包成 APK（未签名）。用途：改动资源/smali 后回编译。",
    {"type": "object",
     "properties": {"src_dir": {"type": "string"}, "out_apk": {"type": "string"}},
     "required": ["src_dir"]},
)
def _apktool_b(a):
    cmd = ["apktool", "b", a["src_dir"]]
    if a.get("out_apk"):
        cmd += ["-o", a["out_apk"]]
    return run_cmd(cmd, timeout=600)


@srv.tool(
    "jadx_decompile",
    "用 jadx 把 APK/DEX/JAR 反编译为可读的 Java 源码到输出目录。"
    "用途：直接阅读接近原始 Java 的反编译结果（比 smali 易读）。",
    {"type": "object",
     "properties": {
         "input": {"type": "string", "description": "apk/dex/jar 路径"},
         "out_dir": {"type": "string", "description": "输出目录，默认 <input>-jadx"}},
     "required": ["input"]},
)
def _jadx(a):
    out = a.get("out_dir") or (a["input"] + "-jadx")
    return run_cmd(["jadx", "-d", out, a["input"]], timeout=600)


@srv.tool(
    "dex2jar",
    "用 dex2jar 把 .dex/.apk 转换为标准 .jar（便于用 JD-GUI/其它 Java 工具查看）。",
    {"type": "object",
     "properties": {"input": {"type": "string"}, "out_jar": {"type": "string"}},
     "required": ["input"]},
)
def _d2j(a):
    cmd = ["d2j-dex2jar", a["input"]]
    if a.get("out_jar"):
        cmd += ["-o", a["out_jar"]]
    return run_cmd(cmd, timeout=300)


@srv.tool(
    "radare2_analyze",
    "用 radare2（r2）以批处理模式分析二进制并执行给定命令序列。"
    "commands 形如 'aaa;afl'（分析后列出函数）或 'iI'（文件信息）、'izz'（字符串）。"
    "用途：静态分析 ELF/PE/Mach-O，无需进入交互界面。",
    {"type": "object",
     "properties": {
         "binary": {"type": "string", "description": "二进制文件路径"},
         "commands": {"type": "string", "description": "以分号分隔的 r2 命令，默认 'iI'"}},
     "required": ["binary"]},
)
def _r2(a):
    cmds = a.get("commands", "iI")
    exe = "r2" if _has("r2") else "radare2"
    return run_cmd([exe, "-q", "-c", cmds, a["binary"]], timeout=300)


@srv.tool(
    "binwalk_scan",
    "用 binwalk 扫描文件中嵌入的已知签名（固件常见）。extract=true 时同时雕刻提取。"
    "用途：分析固件/未知二进制里嵌套的文件系统、压缩块、证书等。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "extract": {"type": "boolean", "description": "是否 -e 自动提取"}},
     "required": ["input"]},
)
def _binwalk(a):
    cmd = ["binwalk"]
    if a.get("extract"):
        cmd.append("-e")
    cmd.append(a["input"])
    return run_cmd(cmd, timeout=600)


@srv.tool(
    "frida_list_devices",
    "用 frida-ls-devices 列出当前可用的 frida 设备（本地/USB/远程）。"
    "用途：动态插桩前确认目标设备连接情况。（需已安装 frida-tools；操作真机还需目标端 frida-server）",
    {"type": "object", "properties": {}},
)
def _frida_dev(_a):
    return run_cmd(["frida-ls-devices"], timeout=60)


@srv.tool(
    "frida_ps",
    "用 frida-ps 列出目标设备上的进程。usb=true 走 USB 设备，remote 指定 host:port 远程。"
    "用途：动态分析前定位目标进程名/PID。",
    {"type": "object",
     "properties": {
         "usb": {"type": "boolean"},
         "remote": {"type": "string", "description": "远程 frida-server，如 127.0.0.1:27042"}},
     "required": []},
)
def _frida_ps(a):
    cmd = ["frida-ps"]
    if a.get("usb"):
        cmd.append("-U")
    if a.get("remote"):
        cmd += ["-H", a["remote"]]
    return run_cmd(cmd, timeout=60)


def _has(name):
    import shutil
    return shutil.which(name) is not None


if __name__ == "__main__":
    srv.run()
