#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reverse_mcp —— 应用/二进制「逆向工程 & 静态分析」工具的 MCP 服务器。

覆盖（全部免费/开源）：
  Android  apktool（资源+smali）、jadx（Dex→Java）、dex2jar（Dex→Jar）
  ELF/PE   radare2、readelf、objdump、nm（binutils）、checksec、gdb（批处理）
  固件     binwalk
  动态     frida（设备/进程枚举）

⚠️ 合规：仅用于你有**合法授权**的安全研究、CTF、教学、互操作/兼容性分析。本服务器只是
把命令行封装为 MCP 工具，是否合规、是否获授权由使用者负责。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd, which  # noqa: E402

RO = {"readOnlyHint": True, "openWorldHint": False}
WRITE = {"readOnlyHint": False, "destructiveHint": False}

srv = MCPServer(
    "clenv-reverse", "2.0.0",
    instructions=(
        "APP/二进制逆向与静态分析工具集，仅限授权场景。典型顺序：先 file_type/elf_info 摸清"
        "目标格式 → 再 strings/objdump/jadx 深入 → 需要动态时用 frida。所有工具默认只读分析。"),
)


# ============================ Android ============================
@srv.tool(
    "apktool_decode",
    "反编译 APK：还原资源、AndroidManifest.xml 与 smali（apktool）。no_src=true 只解资源、更快。",
    {"type": "object",
     "properties": {
         "apk": {"type": "string", "description": "APK 文件路径"},
         "out_dir": {"type": "string", "description": "输出目录，默认同名目录"},
         "no_src": {"type": "boolean", "description": "true 则不反汇编 smali", "default": False}},
     "required": ["apk"]},
    annotations=dict(WRITE, title="反编译 APK"),
    examples=[
        {"desc": "只看资源与 Manifest", "arguments": {"apk": "app.apk", "no_src": True}},
        {"desc": "完整反编译到目录", "arguments": {"apk": "app.apk", "out_dir": "app_src"}},
    ],
)
def _apktool_d(a):
    cmd = ["apktool", "d", "-f", a["apk"]]
    if a.get("out_dir"):
        cmd += ["-o", a["out_dir"]]
    if a.get("no_src"):
        cmd.append("-s")
    return run_cmd(cmd, check_paths=[a["apk"]], timeout=600)


@srv.tool(
    "apktool_build",
    "把反编译目录重新打包为 APK（apktool b，未签名）。用途：改动资源/smali 后回编译。",
    {"type": "object",
     "properties": {"src_dir": {"type": "string"}, "out_apk": {"type": "string"}},
     "required": ["src_dir"]},
    annotations=dict(WRITE, title="回编译 APK"),
    examples=[{"desc": "回编译", "arguments": {"src_dir": "app_src", "out_apk": "patched.apk"}}],
)
def _apktool_b(a):
    cmd = ["apktool", "b", a["src_dir"]]
    if a.get("out_apk"):
        cmd += ["-o", a["out_apk"]]
    return run_cmd(cmd, check_paths=[a["src_dir"]], timeout=600)


@srv.tool(
    "jadx_decompile",
    "把 APK/DEX/JAR 反编译为可读 Java 源码（jadx）。比 smali 易读，是读逻辑首选。",
    {"type": "object",
     "properties": {
         "input": {"type": "string", "description": "apk/dex/jar 路径"},
         "out_dir": {"type": "string", "description": "输出目录，默认 <input>-jadx"}},
     "required": ["input"]},
    annotations=dict(WRITE, title="反编译为 Java"),
    examples=[{"desc": "反编译 APK", "arguments": {"input": "app.apk"}}],
)
def _jadx(a):
    out = a.get("out_dir") or (a["input"] + "-jadx")
    return run_cmd(["jadx", "-d", out, a["input"]], check_paths=[a["input"]], timeout=600)


@srv.tool(
    "dex2jar",
    "把 .dex/.apk 转成标准 .jar（dex2jar），便于用 Java 工具查看。",
    {"type": "object",
     "properties": {"input": {"type": "string"}, "out_jar": {"type": "string"}},
     "required": ["input"]},
    annotations=dict(WRITE, title="Dex 转 Jar"),
    examples=[{"desc": "转 jar", "arguments": {"input": "classes.dex", "out_jar": "classes.jar"}}],
)
def _d2j(a):
    cmd = ["d2j-dex2jar", a["input"]]
    if a.get("out_jar"):
        cmd += ["-o", a["out_jar"]]
    return run_cmd(cmd, check_paths=[a["input"]], timeout=300)


# ============================ ELF/PE 静态分析 ============================
@srv.tool(
    "elf_info",
    "查看 ELF 文件头/节区/动态段/依赖（readelf）。sections 选择要看的部分。用途：了解 ELF 结构、架构、是否动态链接、导入库。只读。",
    {"type": "object",
     "properties": {
         "binary": {"type": "string"},
         "sections": {"type": "string",
                      "description": "readelf 选项组合，默认 '-hSd'（头+节区+动态段）；可传 '-a' 看全部",
                      "default": "-hSd"}},
     "required": ["binary"]},
    annotations=dict(RO, title="ELF 信息"),
    examples=[
        {"desc": "看头/节区/动态段", "arguments": {"binary": "a.out"}},
        {"desc": "看全部", "arguments": {"binary": "a.out", "sections": "-a"}},
    ],
)
def _elf(a):
    opt = a.get("sections", "-hSd")
    return run_cmd(["readelf"] + opt.split() + [a["binary"]], check_paths=[a["binary"]])


@srv.tool(
    "objdump_disasm",
    "反汇编二进制（objdump -d，Intel 语法）。symbol 可只反汇编某个函数。用途：读汇编、定位逻辑。只读。",
    {"type": "object",
     "properties": {
         "binary": {"type": "string"},
         "symbol": {"type": "string", "description": "只反汇编该符号/函数，可选"}},
     "required": ["binary"]},
    annotations=dict(RO, title="反汇编"),
    examples=[
        {"desc": "反汇编整个文件", "arguments": {"binary": "a.out"}},
        {"desc": "只看 main", "arguments": {"binary": "a.out", "symbol": "main"}},
    ],
)
def _objdump(a):
    cmd = ["objdump", "-d", "-M", "intel"]
    if a.get("symbol"):
        cmd += ["--disassemble=" + a["symbol"]]
    cmd.append(a["binary"])
    return run_cmd(cmd, check_paths=[a["binary"]])


@srv.tool(
    "nm_symbols",
    "列出二进制的符号表（nm），含函数/变量与是否已定义。用途：找入口/导出/未定义符号。只读。",
    {"type": "object",
     "properties": {
         "binary": {"type": "string"},
         "dynamic": {"type": "boolean", "description": "true 用 -D 看动态符号", "default": False}},
     "required": ["binary"]},
    annotations=dict(RO, title="符号表"),
    examples=[{"desc": "看动态符号", "arguments": {"binary": "libfoo.so", "dynamic": True}}],
)
def _nm(a):
    cmd = ["nm", "-C"]
    if a.get("dynamic"):
        cmd.append("-D")
    cmd.append(a["binary"])
    return run_cmd(cmd, check_paths=[a["binary"]])


@srv.tool(
    "checksec",
    "检查二进制的安全加固属性（checksec）：RELRO/Canary/NX/PIE/Fortify。用途：评估利用难度/加固情况。只读。",
    {"type": "object", "properties": {"binary": {"type": "string"}}, "required": ["binary"]},
    annotations=dict(RO, title="安全加固检查"),
    examples=[{"desc": "检查加固", "arguments": {"binary": "a.out"}}],
)
def _checksec(a):
    return run_cmd(["checksec", "--file=" + a["binary"]], check_paths=[a["binary"]])


@srv.tool(
    "radare2_analyze",
    "用 radare2 批处理分析二进制并执行命令序列（r2 -q -c）。commands 以分号分隔。用途：一站式静态分析。只读（不改文件）。",
    {"type": "object",
     "properties": {
         "binary": {"type": "string"},
         "commands": {"type": "string",
                      "description": "r2 命令，默认 'iI'。常用：'aaa;afl' 列函数、'izz' 全字符串、'pdf @ main' 反汇编 main",
                      "default": "iI"}},
     "required": ["binary"]},
    annotations=dict(RO, title="radare2 分析"),
    examples=[
        {"desc": "文件信息", "arguments": {"binary": "a.out"}},
        {"desc": "分析并列函数", "arguments": {"binary": "a.out", "commands": "aaa;afl"}},
    ],
)
def _r2(a):
    exe = "r2" if which("r2") else "radare2"
    return run_cmd([exe, "-q", "-c", a.get("commands", "iI"), a["binary"]],
                   check_paths=[a["binary"]], timeout=300)


@srv.tool(
    "gdb_batch",
    "用 gdb 批处理模式运行一串命令（gdb -batch）。用途：静态查看反汇编/信息，如 'disassemble main'、'info functions'。"
    "注意：这里不启动/附加进程，只对文件做静态检视（如需运行请自行在命令里 run，风险自负）。只读为主。",
    {"type": "object",
     "properties": {
         "binary": {"type": "string"},
         "commands": {"type": "array", "items": {"type": "string"},
                      "description": "gdb 命令列表，如 ['disassemble main','info functions']"}},
     "required": ["binary", "commands"]},
    annotations=dict(RO, title="gdb 批处理"),
    examples=[{"desc": "反汇编 main", "arguments": {"binary": "a.out", "commands": ["disassemble main"]}}],
)
def _gdb(a):
    cmd = ["gdb", "-batch", "-nx"]
    for c in (a.get("commands") or []):
        cmd += ["-ex", c]
    cmd.append(a["binary"])
    return run_cmd(cmd, check_paths=[a["binary"]], timeout=180)


# ============================ 固件 ============================
@srv.tool(
    "binwalk_scan",
    "扫描文件中嵌入的已知签名（binwalk），extract=true 时雕刻提取。用途：固件里找文件系统/压缩块/证书。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "extract": {"type": "boolean", "description": "是否 -e 自动提取", "default": False}},
     "required": ["input"]},
    annotations={"readOnlyHint": False, "destructiveHint": False, "title": "固件扫描"},
    examples=[
        {"desc": "只扫描", "arguments": {"input": "firmware.bin"}},
        {"desc": "扫描并提取", "arguments": {"input": "firmware.bin", "extract": True}},
    ],
)
def _binwalk(a):
    cmd = ["binwalk"]
    if a.get("extract"):
        cmd.append("-e")
    cmd.append(a["input"])
    return run_cmd(cmd, check_paths=[a["input"]], timeout=600)


# ============================ 动态（frida） ============================
@srv.tool(
    "frida_list_devices",
    "列出可用的 frida 设备（本地/USB/远程）（frida-ls-devices）。动态插桩前确认设备连接。只读。",
    {"type": "object", "properties": {}},
    annotations=dict(RO, title="frida 设备列表"),
    examples=[{"desc": "列设备", "arguments": {}}],
)
def _frida_dev(_a):
    return run_cmd(["frida-ls-devices"], timeout=60)


@srv.tool(
    "frida_ps",
    "列出目标设备上的进程（frida-ps）。usb=true 走 USB，remote 指定 host:port。用途：定位目标进程名/PID。只读。",
    {"type": "object",
     "properties": {
         "usb": {"type": "boolean", "default": False},
         "remote": {"type": "string", "description": "远程 frida-server，如 127.0.0.1:27042"}},
     "required": []},
    annotations=dict(RO, title="frida 进程列表"),
    examples=[{"desc": "USB 设备进程", "arguments": {"usb": True}}],
)
def _frida_ps(a):
    cmd = ["frida-ps"]
    if a.get("usb"):
        cmd.append("-U")
    if a.get("remote"):
        cmd += ["-H", a["remote"]]
    return run_cmd(cmd, timeout=60)


if __name__ == "__main__":
    srv.run()
