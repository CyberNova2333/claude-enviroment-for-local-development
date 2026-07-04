#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codec_mcp —— 文件格式「编解码 / 转换 / 探查」工具的 MCP 服务器。

覆盖：ffmpeg（音视频）、ImageMagick（图像）、jq（JSON）、yq（YAML）、
pandoc（文档）、7z（压缩包）、protoc（Protobuf）、poppler（PDF）、xxd（十六进制）。

每个工具都以「一个语义清晰的 MCP 工具」暴露，参数与用途见各 @tool 的中文描述。
底层统一走 run_cmd() 调用系统命令，未安装时返回明确的安装指引。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd  # noqa: E402

srv = MCPServer(
    "clenv-codec", "1.0.0",
    instructions="文件编解码/转换工具集。调用前可先用各工具的 *_probe/version 类工具确认可用。",
)


@srv.tool(
    "ffmpeg_probe",
    "用 ffprobe 探查音视频文件的封装、流、时长、编码等元信息（只读，不修改文件）。"
    "用途：转码前先了解源文件参数。",
    {"type": "object",
     "properties": {"input": {"type": "string", "description": "输入文件路径"}},
     "required": ["input"]},
)
def _ffprobe(a):
    return run_cmd(["ffprobe", "-hide_banner", "-v", "error", "-show_format",
                    "-show_streams", a["input"]])


@srv.tool(
    "ffmpeg_convert",
    "用 ffmpeg 转码/转封装音视频。output 后缀决定目标格式（如 .mp4/.mkv/.mp3/.gif）。"
    "extra_args 可传额外参数（如 ['-vf','scale=1280:-1','-crf','23']）。用途：格式转换、抽音轨、压制。",
    {"type": "object",
     "properties": {
         "input": {"type": "string", "description": "输入文件路径"},
         "output": {"type": "string", "description": "输出文件路径（后缀即目标格式）"},
         "extra_args": {"type": "array", "items": {"type": "string"},
                        "description": "透传给 ffmpeg 的额外参数，可选"}},
     "required": ["input", "output"]},
)
def _ffmpeg(a):
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", a["input"]]
    cmd += list(a.get("extra_args") or [])
    cmd.append(a["output"])
    return run_cmd(cmd)


@srv.tool(
    "image_convert",
    "用 ImageMagick 转换/缩放图片。resize 形如 '50%' 或 '800x600'。"
    "用途：格式转换（png↔jpg↔webp）、批量缩放、生成缩略图。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "output": {"type": "string", "description": "输出路径，后缀决定格式"},
         "resize": {"type": "string", "description": "缩放规格，可选，如 '800x600' 或 '50%'"}},
     "required": ["input", "output"]},
)
def _image(a):
    base = "magick" if _has("magick") else "convert"
    cmd = [base, a["input"]]
    if a.get("resize"):
        cmd += ["-resize", a["resize"]]
    cmd.append(a["output"])
    return run_cmd(cmd)


@srv.tool(
    "image_identify",
    "用 ImageMagick identify 读取图片的尺寸/格式/色彩深度等信息（只读）。",
    {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
)
def _identify(a):
    base = "magick" if _has("magick") else "identify"
    args = [base, "identify", a["input"]] if base == "magick" else [base, a["input"]]
    return run_cmd(args)


@srv.tool(
    "jq_query",
    "用 jq 对 JSON 做查询/过滤/变形。filter 为 jq 表达式（如 '.items[].name'）。"
    "二选一提供 json_file 或 json_text。用途：从 JSON 中抽取字段、重塑结构。",
    {"type": "object",
     "properties": {
         "filter": {"type": "string", "description": "jq 过滤表达式"},
         "json_file": {"type": "string", "description": "JSON 文件路径，可选"},
         "json_text": {"type": "string", "description": "直接给出的 JSON 文本，可选"}},
     "required": ["filter"]},
)
def _jq(a):
    if a.get("json_file"):
        return run_cmd(["jq", a["filter"], a["json_file"]])
    return run_cmd(["jq", a["filter"]], input_text=a.get("json_text", ""))


@srv.tool(
    "yq_query",
    "用 yq(mikefarah) 查询/转换 YAML。filter 形如 '.services.web.image'。"
    "to_json=true 时把 YAML 转成 JSON 输出。用途：读取/改写 YAML 配置。",
    {"type": "object",
     "properties": {
         "filter": {"type": "string", "description": "yq 表达式，默认 '.'"},
         "yaml_file": {"type": "string"},
         "yaml_text": {"type": "string"},
         "to_json": {"type": "boolean"}},
     "required": []},
)
def _yq(a):
    cmd = ["yq"]
    if a.get("to_json"):
        cmd += ["-o=json"]
    cmd.append(a.get("filter", "."))
    if a.get("yaml_file"):
        cmd.append(a["yaml_file"])
        return run_cmd(cmd)
    return run_cmd(cmd, input_text=a.get("yaml_text", ""))


@srv.tool(
    "pandoc_convert",
    "用 pandoc 在文档格式间转换（md/html/docx/pdf/rst/epub 等），output 后缀决定目标格式。"
    "用途：Markdown 转 HTML/Word、文档格式互转。",
    {"type": "object",
     "properties": {"input": {"type": "string"}, "output": {"type": "string"}},
     "required": ["input", "output"]},
)
def _pandoc(a):
    return run_cmd(["pandoc", a["input"], "-o", a["output"]])


@srv.tool(
    "archive_list",
    "用 7z 列出压缩包内容（zip/7z/rar/tar/gz 等），只读不解压。用途：查看包内文件清单。",
    {"type": "object", "properties": {"archive": {"type": "string"}}, "required": ["archive"]},
)
def _arc_list(a):
    return run_cmd([_sevenz(), "l", a["archive"]])


@srv.tool(
    "archive_extract",
    "用 7z 解压压缩包到指定目录（默认当前目录）。用途：解包分析素材/APK/固件等。",
    {"type": "object",
     "properties": {"archive": {"type": "string"},
                    "dest": {"type": "string", "description": "输出目录，可选"}},
     "required": ["archive"]},
)
def _arc_extract(a):
    cmd = [_sevenz(), "x", "-y", a["archive"]]
    if a.get("dest"):
        cmd.append("-o" + a["dest"])
    return run_cmd(cmd)


@srv.tool(
    "protoc_decode_raw",
    "用 protoc --decode_raw 把二进制 Protobuf 消息解成可读的字段树（无需 .proto）。"
    "用途：逆向/调试未知 protobuf 报文。bin_file 为二进制文件路径。",
    {"type": "object", "properties": {"bin_file": {"type": "string"}}, "required": ["bin_file"]},
)
def _protoc(a):
    try:
        with open(a["bin_file"], "rb") as f:
            data = f.read()
    except Exception as e:  # noqa: BLE001
        return "[读取失败] %s：%s" % (a["bin_file"], e)
    import subprocess
    try:
        p = subprocess.run(["protoc", "--decode_raw"], input=data,
                           capture_output=True, timeout=60)
        return "exit=%d\n%s\n%s" % (p.returncode,
                                     p.stdout.decode("utf-8", "replace"),
                                     p.stderr.decode("utf-8", "replace"))
    except FileNotFoundError:
        return "[未安装] protoc，请运行：clenv env install protobuf"


@srv.tool(
    "pdf_to_text",
    "用 poppler 的 pdftotext 抽取 PDF 文本。layout=true 尽量保留版面。用途：读取 PDF 内容做分析。",
    {"type": "object",
     "properties": {"input": {"type": "string"}, "layout": {"type": "boolean"}},
     "required": ["input"]},
)
def _pdf(a):
    cmd = ["pdftotext"]
    if a.get("layout"):
        cmd.append("-layout")
    cmd += [a["input"], "-"]  # 输出到 stdout
    return run_cmd(cmd)


@srv.tool(
    "hexdump",
    "用 xxd 生成文件的十六进制视图。可用 length 限制字节数、offset 指定起始偏移。"
    "用途：查看文件魔数/头部、二进制排查。",
    {"type": "object",
     "properties": {"input": {"type": "string"},
                    "length": {"type": "integer", "description": "读取字节数，可选"},
                    "offset": {"type": "integer", "description": "起始偏移，可选"}},
     "required": ["input"]},
)
def _hex(a):
    cmd = ["xxd"]
    if a.get("length") is not None:
        cmd += ["-l", str(a["length"])]
    if a.get("offset") is not None:
        cmd += ["-s", str(a["offset"])]
    cmd.append(a["input"])
    return run_cmd(cmd)


def _has(name):
    import shutil
    return shutil.which(name) is not None


def _sevenz():
    import shutil
    for n in ("7z", "7za", "7zr"):
        if shutil.which(n):
            return n
    return "7z"


if __name__ == "__main__":
    srv.run()
