#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codec_mcp —— 文件格式「编解码 / 转换 / 探查 / 取证」工具的 MCP 服务器。

覆盖（全部为免费/开源工具）：
  音视频   ffmpeg / ffprobe / mediainfo
  图像     ImageMagick、tesseract(OCR)
  文本数据 jq(JSON)、yq(YAML)、pandoc(文档)、sqlite3(数据库)
  压缩     7z
  二进制   xxd(十六进制)、file(类型识别)、strings(可见字符串)、protoc(protobuf)
  编码/散列 base64、openssl/sha*sum(哈希)
  PDF      poppler(pdftotext/pdfinfo)、exiftool(元数据)

每个工具都带：清晰用途说明、结构化调用示例、只读/危险标注，命令缺失时给出安装指引。
"""
import os
import sys
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcpbase import MCPServer, run_cmd, which  # noqa: E402

RO = {"readOnlyHint": True, "openWorldHint": False}          # 只读
WRITE = {"readOnlyHint": False, "destructiveHint": False}    # 产出新文件，不破坏输入

srv = MCPServer(
    "clenv-codec", "2.0.0",
    instructions=(
        "文件编解码/转换/探查工具集。选择原则：只想了解文件→用 *_probe/identify/info/"
        "file_type/mediainfo（只读）；要产出新文件→用 *_convert/extract（写）。"
        "所有路径都相对 MCP 进程的当前工作目录。"),
)


# ============================ 音视频 ============================
@srv.tool(
    "ffmpeg_probe",
    "只读探查音视频的封装、时长、分辨率、码率、编码等元信息（ffprobe）。转码前先用它了解源文件。",
    {"type": "object",
     "properties": {"input": {"type": "string", "description": "输入媒体文件路径"}},
     "required": ["input"]},
    annotations=dict(RO, title="探查音视频信息"),
    examples=[{"desc": "查看某视频信息", "arguments": {"input": "clip.mp4"}}],
)
def _ffprobe(a):
    return run_cmd(["ffprobe", "-hide_banner", "-v", "error", "-show_format",
                    "-show_streams", a["input"]], check_paths=[a["input"]])


@srv.tool(
    "ffmpeg_convert",
    "转码/转封装音视频（ffmpeg）。output 后缀决定目标格式；extra_args 传编码参数。"
    "常见用途：格式转换、抽音轨、调分辨率、压制、截取片段。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "output": {"type": "string", "description": "输出路径，后缀即目标格式（.mp4/.mkv/.mp3/.gif/.webm）"},
         "extra_args": {"type": "array", "items": {"type": "string"},
                        "description": "透传给 ffmpeg 的额外参数（放在 -i 之后、输出之前）"}},
     "required": ["input", "output"]},
    annotations=dict(WRITE, title="转码音视频"),
    examples=[
        {"desc": "mp4 转 mp3（抽音轨）", "arguments": {"input": "a.mp4", "output": "a.mp3"}},
        {"desc": "压制并缩放到 720p", "arguments":
            {"input": "a.mp4", "output": "b.mp4", "extra_args": ["-vf", "scale=-2:720", "-crf", "23"]}},
        {"desc": "截取前 10 秒", "arguments":
            {"input": "a.mp4", "output": "c.mp4", "extra_args": ["-t", "10", "-c", "copy"]}},
    ],
)
def _ffmpeg(a):
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", a["input"]]
    cmd += [str(x) for x in (a.get("extra_args") or [])]
    cmd.append(a["output"])
    return run_cmd(cmd, check_paths=[a["input"]], timeout=600)


@srv.tool(
    "mediainfo",
    "读取音视频/容器的详尽技术元数据（mediainfo，比 ffprobe 更人类可读）。只读。",
    {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
    annotations=dict(RO, title="媒体元数据"),
    examples=[{"desc": "查看 mkv 详细信息", "arguments": {"input": "movie.mkv"}}],
)
def _mediainfo(a):
    return run_cmd(["mediainfo", a["input"]], check_paths=[a["input"]])


# ============================ 图像 / OCR ============================
@srv.tool(
    "image_convert",
    "转换/缩放图片（ImageMagick）。output 后缀决定格式；resize 形如 '800x600' 或 '50%'。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "output": {"type": "string", "description": "输出路径，后缀决定格式（.png/.jpg/.webp/.gif）"},
         "resize": {"type": "string", "description": "缩放规格，可选"}},
     "required": ["input", "output"]},
    annotations=dict(WRITE, title="转换图片"),
    examples=[
        {"desc": "png 转 webp", "arguments": {"input": "a.png", "output": "a.webp"}},
        {"desc": "缩放到宽 800", "arguments": {"input": "a.jpg", "output": "s.jpg", "resize": "800x"}},
    ],
)
def _image(a):
    base = "magick" if which("magick") else "convert"
    cmd = [base, a["input"]]
    if a.get("resize"):
        cmd += ["-resize", a["resize"]]
    cmd.append(a["output"])
    return run_cmd(cmd, check_paths=[a["input"]])


@srv.tool(
    "image_identify",
    "读取图片尺寸/格式/色深/EXIF 摘要（ImageMagick identify）。只读。",
    {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
    annotations=dict(RO, title="识别图片"),
    examples=[{"desc": "查看图片信息", "arguments": {"input": "a.png"}}],
)
def _identify(a):
    if which("magick"):
        return run_cmd(["magick", "identify", "-verbose", a["input"]], check_paths=[a["input"]])
    return run_cmd(["identify", "-verbose", a["input"]], check_paths=[a["input"]])


@srv.tool(
    "ocr_image",
    "对图片做 OCR 文字识别（tesseract），返回识别出的纯文本。lang 如 'eng'、'chi_sim'（需装对应语言包）。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "lang": {"type": "string", "description": "语言，默认 eng；中文用 chi_sim", "default": "eng"}},
     "required": ["input"]},
    annotations=dict(RO, title="图片 OCR"),
    examples=[
        {"desc": "英文截图识别", "arguments": {"input": "shot.png"}},
        {"desc": "简体中文识别", "arguments": {"input": "shot.png", "lang": "chi_sim"}},
    ],
)
def _ocr(a):
    return run_cmd(["tesseract", a["input"], "stdout", "-l", a.get("lang", "eng")],
                   check_paths=[a["input"]])


# ============================ 文本 / 数据 ============================
@srv.tool(
    "jq_query",
    "用 jq 查询/过滤/变形 JSON。filter 为 jq 表达式；json_file 与 json_text 二选一。只读。",
    {"type": "object",
     "properties": {
         "filter": {"type": "string", "description": "jq 表达式，如 '.items[].name'、'keys'、'length'"},
         "json_file": {"type": "string"},
         "json_text": {"type": "string"}},
     "required": ["filter"]},
    annotations=dict(RO, title="查询 JSON"),
    examples=[
        {"desc": "取字段", "arguments": {"filter": ".name", "json_text": "{\"name\":\"demo\"}"}},
        {"desc": "对文件取数组长度", "arguments": {"filter": ".data | length", "json_file": "d.json"}},
    ],
)
def _jq(a):
    if a.get("json_file"):
        return run_cmd(["jq", a["filter"], a["json_file"]], check_paths=[a["json_file"]])
    return run_cmd(["jq", a["filter"]], input_text=a.get("json_text", ""))


@srv.tool(
    "yq_query",
    "用 yq(mikefarah) 查询/转换 YAML；to_json=true 转成 JSON。yaml_file 与 yaml_text 二选一。只读。",
    {"type": "object",
     "properties": {
         "filter": {"type": "string", "description": "yq 表达式，默认 '.'", "default": "."},
         "yaml_file": {"type": "string"},
         "yaml_text": {"type": "string"},
         "to_json": {"type": "boolean", "default": False}},
     "required": []},
    annotations=dict(RO, title="查询 YAML"),
    examples=[
        {"desc": "读取镜像名", "arguments": {"filter": ".services.web.image", "yaml_file": "docker-compose.yml"}},
        {"desc": "整份转 JSON", "arguments": {"to_json": True, "yaml_file": "conf.yml"}},
    ],
)
def _yq(a):
    cmd = ["yq"]
    if a.get("to_json"):
        cmd += ["-o=json"]
    cmd.append(a.get("filter", "."))
    if a.get("yaml_file"):
        cmd.append(a["yaml_file"])
        return run_cmd(cmd, check_paths=[a["yaml_file"]])
    return run_cmd(cmd, input_text=a.get("yaml_text", ""))


@srv.tool(
    "sqlite_query",
    "对 SQLite 数据库文件执行只读 SQL 查询（sqlite3）。默认拒绝写语句（INSERT/UPDATE/DELETE/DROP…）"
    "除非 allow_write=true。用途：查看/分析 .db/.sqlite/.sqlite3。",
    {"type": "object",
     "properties": {
         "db": {"type": "string", "description": "数据库文件路径"},
         "sql": {"type": "string", "description": "SQL 语句，如 'SELECT name FROM sqlite_master'"},
         "allow_write": {"type": "boolean", "default": False}},
     "required": ["db", "sql"]},
    annotations={"readOnlyHint": False, "destructiveHint": True, "title": "查询 SQLite"},
    examples=[
        {"desc": "列出所有表", "arguments": {"db": "app.db", "sql": "SELECT name FROM sqlite_master WHERE type='table'"}},
        {"desc": "查前 5 行", "arguments": {"db": "app.db", "sql": "SELECT * FROM users LIMIT 5"}},
    ],
)
def _sqlite(a):
    sql = a["sql"]
    lowered = sql.lower()
    danger = ("insert", "update", "delete", "drop", "alter", "create", "replace", "attach")
    if not a.get("allow_write") and any(w in lowered.split() or (w + " ") in lowered for w in danger):
        return "[已拦截] 检测到可能的写/DDL 语句。若确认要改库，请传 allow_write=true。"
    args = ["sqlite3", "-header", "-column", a["db"], sql]
    return run_cmd(args, check_paths=[a["db"]])


@srv.tool(
    "pandoc_convert",
    "文档格式互转（pandoc）：md/html/docx/rst/epub/pdf 等，output 后缀决定目标格式。",
    {"type": "object",
     "properties": {"input": {"type": "string"}, "output": {"type": "string"}},
     "required": ["input", "output"]},
    annotations=dict(WRITE, title="转换文档"),
    examples=[{"desc": "Markdown 转 HTML", "arguments": {"input": "README.md", "output": "README.html"}}],
)
def _pandoc(a):
    return run_cmd(["pandoc", a["input"], "-o", a["output"]], check_paths=[a["input"]])


# ============================ 压缩包 ============================
@srv.tool(
    "archive_list",
    "只读列出压缩包内容（7z，支持 zip/7z/rar/tar/gz 等）。",
    {"type": "object", "properties": {"archive": {"type": "string"}}, "required": ["archive"]},
    annotations=dict(RO, title="列出压缩包"),
    examples=[{"desc": "查看 zip 内容", "arguments": {"archive": "pkg.zip"}}],
)
def _arc_list(a):
    return run_cmd([_sevenz(), "l", a["archive"]], check_paths=[a["archive"]])


@srv.tool(
    "archive_extract",
    "解压压缩包到目录（7z）。dest 缺省为当前目录。用途：解包素材/APK/固件等。",
    {"type": "object",
     "properties": {"archive": {"type": "string"}, "dest": {"type": "string"}},
     "required": ["archive"]},
    annotations=dict(WRITE, title="解压压缩包"),
    examples=[{"desc": "解压到 out/", "arguments": {"archive": "pkg.zip", "dest": "out"}}],
)
def _arc_extract(a):
    cmd = [_sevenz(), "x", "-y", a["archive"]]
    if a.get("dest"):
        cmd.append("-o" + a["dest"])
    return run_cmd(cmd, check_paths=[a["archive"]])


# ============================ 二进制 / 识别 ============================
@srv.tool(
    "file_type",
    "识别文件真实类型/魔数（file 命令），不看后缀。用途：判断未知文件到底是什么。只读。",
    {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
    annotations=dict(RO, title="识别文件类型"),
    examples=[{"desc": "识别未知文件", "arguments": {"input": "blob.bin"}}],
)
def _filetype(a):
    return run_cmd(["file", a["input"]], check_paths=[a["input"]])


@srv.tool(
    "strings_extract",
    "抽取文件中的可见字符串（strings）。min_len 控制最短长度。用途：快速看二进制里的 URL/提示/密钥痕迹。只读。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "min_len": {"type": "integer", "description": "最短字符串长度，默认 4", "default": 4}},
     "required": ["input"]},
    annotations=dict(RO, title="抽取字符串"),
    examples=[{"desc": "抽取长度≥6 的串", "arguments": {"input": "app.bin", "min_len": 6}}],
)
def _strings(a):
    return run_cmd(["strings", "-n", str(a.get("min_len", 4)), a["input"]], check_paths=[a["input"]])


@srv.tool(
    "hexdump",
    "生成文件十六进制视图（xxd）。length 限制字节数、offset 指定起始偏移。用途：看文件头/魔数。只读。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "length": {"type": "integer", "description": "读取字节数，默认 256", "default": 256},
         "offset": {"type": "integer", "description": "起始偏移，默认 0"}},
     "required": ["input"]},
    annotations=dict(RO, title="十六进制视图"),
    examples=[{"desc": "看前 64 字节", "arguments": {"input": "a.png", "length": 64}}],
)
def _hex(a):
    cmd = ["xxd", "-l", str(a.get("length", 256))]
    if a.get("offset") is not None:
        cmd += ["-s", str(a["offset"])]
    cmd.append(a["input"])
    return run_cmd(cmd, check_paths=[a["input"]])


@srv.tool(
    "protoc_decode_raw",
    "无需 .proto，把二进制 Protobuf 消息解成字段树（protoc --decode_raw）。用途：逆向未知 protobuf 报文。只读。",
    {"type": "object", "properties": {"bin_file": {"type": "string"}}, "required": ["bin_file"]},
    annotations=dict(RO, title="解析 protobuf"),
    examples=[{"desc": "解析抓包得到的消息", "arguments": {"bin_file": "msg.bin"}}],
)
def _protoc(a):
    if which("protoc") is None:
        from mcpbase import not_installed_msg
        return not_installed_msg("protoc")
    try:
        with open(a["bin_file"], "rb") as f:
            data = f.read()
    except Exception as e:  # noqa: BLE001
        return "[读取失败] %s：%s" % (a["bin_file"], e)
    try:
        p = subprocess.run(["protoc", "--decode_raw"], input=data,
                           capture_output=True, timeout=60)
        return "exit=%d\n%s\n%s" % (p.returncode,
                                     p.stdout.decode("utf-8", "replace"),
                                     p.stderr.decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        return "[执行失败] %s" % e


# ============================ 编码 / 散列 ============================
@srv.tool(
    "base64_transform",
    "Base64 编码或解码文本（mode=encode/decode）。用途：处理 data URI、token、配置里的 base64 串。只读计算。",
    {"type": "object",
     "properties": {
         "text": {"type": "string", "description": "要处理的文本"},
         "mode": {"type": "string", "enum": ["encode", "decode"], "default": "encode"}},
     "required": ["text"]},
    annotations=dict(RO, title="Base64 编解码"),
    examples=[
        {"desc": "编码", "arguments": {"text": "hello", "mode": "encode"}},
        {"desc": "解码", "arguments": {"text": "aGVsbG8=", "mode": "decode"}},
    ],
)
def _b64(a):
    import base64
    try:
        if a.get("mode", "encode") == "encode":
            return base64.b64encode(a["text"].encode("utf-8")).decode("ascii")
        return base64.b64decode(a["text"]).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return "[处理失败] %s" % e


@srv.tool(
    "hash_file",
    "计算文件哈希（md5/sha1/sha256）。用途：校验完整性、比对样本。只读。",
    {"type": "object",
     "properties": {
         "input": {"type": "string"},
         "algo": {"type": "string", "enum": ["md5", "sha1", "sha256", "sha512"], "default": "sha256"}},
     "required": ["input"]},
    annotations=dict(RO, title="文件哈希"),
    examples=[{"desc": "算 sha256", "arguments": {"input": "app.apk", "algo": "sha256"}}],
)
def _hash(a):
    import hashlib
    algo = a.get("algo", "sha256")
    try:
        h = hashlib.new(algo)
        with open(a["input"], "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return "%s(%s) = %s" % (algo, a["input"], h.hexdigest())
    except FileNotFoundError:
        return "[路径不存在] %s" % a["input"]
    except Exception as e:  # noqa: BLE001
        return "[计算失败] %s" % e


# ============================ PDF ============================
@srv.tool(
    "pdf_to_text",
    "抽取 PDF 文本（poppler pdftotext）。layout=true 尽量保留版面。只读。",
    {"type": "object",
     "properties": {"input": {"type": "string"}, "layout": {"type": "boolean", "default": False}},
     "required": ["input"]},
    annotations=dict(RO, title="PDF 转文本"),
    examples=[{"desc": "抽取文本", "arguments": {"input": "doc.pdf"}}],
)
def _pdf(a):
    cmd = ["pdftotext"]
    if a.get("layout"):
        cmd.append("-layout")
    cmd += [a["input"], "-"]
    return run_cmd(cmd, check_paths=[a["input"]])


@srv.tool(
    "exif_read",
    "读取文件（图片/PDF/音视频/文档）的 EXIF/元数据（exiftool）。用途：取证、查拍摄设备/GPS/创建时间。只读。",
    {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
    annotations=dict(RO, title="读取元数据"),
    examples=[{"desc": "看照片 EXIF", "arguments": {"input": "photo.jpg"}}],
)
def _exif(a):
    return run_cmd(["exiftool", a["input"]], check_paths=[a["input"]])


def _sevenz():
    for n in ("7z", "7za", "7zr"):
        if which(n):
            return n
    return "7z"


if __name__ == "__main__":
    srv.run()
