# clenv-codec —— 文件格式编解码 MCP

服务器文件：`servers/codec_mcp.py` ｜ 版本：1.0.0

把常用的「编解码 / 转换 / 探查」命令行封装为结构化工具。全部只依赖对应系统命令。

## 工具清单

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `ffmpeg_probe` | ffprobe 只读探查音视频元信息 | `input` |
| `ffmpeg_convert` | ffmpeg 转码/转封装（后缀定格式） | `input`,`output`,`extra_args?` |
| `image_convert` | ImageMagick 转换/缩放图片 | `input`,`output`,`resize?` |
| `image_identify` | 读取图片尺寸/格式等信息 | `input` |
| `jq_query` | jq 查询/变形 JSON | `filter`,`json_file?`/`json_text?` |
| `yq_query` | yq 查询/转换 YAML（可转 JSON） | `filter?`,`yaml_file?`/`yaml_text?`,`to_json?` |
| `pandoc_convert` | pandoc 文档格式互转 | `input`,`output` |
| `archive_list` | 7z 只读列出压缩包内容 | `archive` |
| `archive_extract` | 7z 解压到目录 | `archive`,`dest?` |
| `protoc_decode_raw` | protoc 无 .proto 解析二进制 protobuf | `bin_file` |
| `pdf_to_text` | poppler 抽取 PDF 文本 | `input`,`layout?` |
| `hexdump` | xxd 生成十六进制视图 | `input`,`length?`,`offset?` |

## 涉及工具与版本

| 工具 | 说明 | 安装项名 |
|---|---|---|
| ffmpeg / ffprobe | 音视频转码与探查 | `ffmpeg` |
| ImageMagick（`magick`/`convert`） | 图像转换与信息 | `imagemagick` |
| jq 1.7+ | JSON 处理器 | `jq` |
| yq（mikefarah，Go 版单文件二进制） | YAML/JSON 处理器 | `yq` |
| pandoc | 通用文档转换 | `pandoc` |
| 7-Zip（`7z`/`7za`/`7zr`） | 压缩包解列 | `7z` |
| protobuf `protoc` | Protobuf 编译/解码 | `protobuf` |
| poppler-utils（`pdftotext` 等） | PDF 工具集 | `poppler` |
| xxd | 十六进制查看 | `xxd` |

## 示例（JSON-RPC 直调）

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call",
 "params":{"name":"jq_query","arguments":{"filter":".name","json_text":"{\"name\":\"demo\"}"}}}
```

返回 `content[0].text` 内含命令、退出码与 stdout。
