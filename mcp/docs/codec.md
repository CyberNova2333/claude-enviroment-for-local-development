# clenv-codec —— 文件格式编解码 / 探查 / 取证 MCP

服务器文件：`servers/codec_mcp.py` ｜ 版本：2.0.0 ｜ 工具数：20

把常用「编解码 / 转换 / 探查 / 取证」命令行封装为结构化工具。每个工具都带**只读/写标注**
（`annotations.readOnlyHint`）与**结构化调用示例**（自动拼进 description），便于模型正确调用。

## 选择原则

- 只想**了解**文件 → 用只读工具：`ffmpeg_probe`/`mediainfo`/`image_identify`/`file_type`/
  `exif_read`/`hash_file`/`strings_extract`/`hexdump`/`pdf_to_text`。
- 要**产出**新文件 → 用写工具：`ffmpeg_convert`/`image_convert`/`pandoc_convert`/
  `archive_extract`/`ocr_image`。

## 工具清单

| 工具 | 用途 | 只读 | 关键参数 |
|---|---|:--:|---|
| `ffmpeg_probe` | 探查音视频元信息 | ✓ | `input` |
| `ffmpeg_convert` | 转码/转封装/抽轨/截取 | | `input`,`output`,`extra_args?` |
| `mediainfo` | 更可读的媒体技术元数据 | ✓ | `input` |
| `image_convert` | 图片格式转换/缩放 | | `input`,`output`,`resize?` |
| `image_identify` | 图片尺寸/格式/EXIF 摘要 | ✓ | `input` |
| `ocr_image` | 图片 OCR 文字识别 | ✓ | `input`,`lang?` |
| `jq_query` | 查询/变形 JSON | ✓ | `filter`,`json_file?`/`json_text?` |
| `yq_query` | 查询/转换 YAML（可转 JSON） | ✓ | `filter?`,`yaml_file?`/`yaml_text?`,`to_json?` |
| `sqlite_query` | 查询 SQLite（写需 allow_write） | | `db`,`sql`,`allow_write?` |
| `pandoc_convert` | 文档格式互转 | | `input`,`output` |
| `archive_list` | 列出压缩包内容 | ✓ | `archive` |
| `archive_extract` | 解压到目录 | | `archive`,`dest?` |
| `file_type` | 按魔数识别真实类型 | ✓ | `input` |
| `strings_extract` | 抽取可见字符串 | ✓ | `input`,`min_len?` |
| `hexdump` | 十六进制视图 | ✓ | `input`,`length?`,`offset?` |
| `protoc_decode_raw` | 无 .proto 解析 protobuf | ✓ | `bin_file` |
| `base64_transform` | Base64 编/解码文本 | ✓ | `text`,`mode?` |
| `hash_file` | 文件哈希（md5/sha1/256/512） | ✓ | `input`,`algo?` |
| `pdf_to_text` | 抽取 PDF 文本 | ✓ | `input`,`layout?` |
| `exif_read` | 读取 EXIF/元数据（取证） | ✓ | `input` |

## 涉及工具与版本

| 工具 | 说明 | 安装项名 |
|---|---|---|
| ffmpeg / ffprobe | 音视频转码与探查 | `ffmpeg` |
| mediainfo | 媒体技术元数据 | `mediainfo` |
| ImageMagick（`magick`/`convert`/`identify`） | 图像转换与信息 | `imagemagick` |
| tesseract | OCR 文字识别 | `tesseract` |
| jq 1.7+ | JSON 处理器 | `jq` |
| yq（mikefarah） | YAML/JSON 处理器 | `yq` |
| sqlite3 | SQLite 命令行 | `sqlite3` |
| pandoc | 通用文档转换 | `pandoc` |
| 7-Zip（`7z`/`7za`/`7zr`） | 压缩包解列 | `7z` |
| file | 魔数类型识别 | `file` |
| binutils（`strings`） | 可见字符串抽取 | `binutils` |
| protobuf `protoc` | Protobuf 解码 | `protobuf` |
| poppler-utils（`pdftotext`） | PDF 工具集 | `poppler` |
| exiftool | 元数据/取证 | `exiftool` |
| xxd | 十六进制 | `xxd` |
| base64 / 哈希 | 内置于 python 标准库，无需额外安装 | — |
