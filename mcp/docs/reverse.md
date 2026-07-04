# clenv-reverse —— 应用/二进制逆向 MCP

服务器文件：`servers/reverse_mcp.py` ｜ 版本：1.0.0

> ⚠️ **合规提示**：以下工具仅用于**你拥有合法授权**的安全研究、CTF、教学、
> 互操作性/兼容性分析等场景。本服务器只是把命令行封装成 MCP 工具，
> 是否合规、是否获得授权由使用者自行负责。

## 工具清单

| 工具 | 用途 | 关键参数 |
|---|---|---|
| `apktool_decode` | 反编译 APK：资源 + Manifest + smali | `apk`,`out_dir?`,`no_src?` |
| `apktool_build` | 把反编译目录回编译为 APK（未签名） | `src_dir`,`out_apk?` |
| `jadx_decompile` | 把 APK/DEX/JAR 反编译为 Java 源码 | `input`,`out_dir?` |
| `dex2jar` | 把 .dex/.apk 转成标准 .jar | `input`,`out_jar?` |
| `radare2_analyze` | r2 批处理分析二进制并执行命令序列 | `binary`,`commands?` |
| `binwalk_scan` | 扫描/雕刻嵌入文件（固件分析） | `input`,`extract?` |
| `frida_list_devices` | 列出可用 frida 设备 | 无 |
| `frida_ps` | 列出目标设备进程 | `usb?`,`remote?` |

### radare2 常用 `commands`
- `iI` 文件信息；`izz` 全部字符串；`aaa;afl` 分析后列函数；`pdf @ main` 反汇编 main。

## 涉及工具与版本

| 工具 | 说明 | 安装项名 | 备注 |
|---|---|---|---|
| apktool 2.9.3 | APK 资源/smali 反编译 | `apktool` | 需 Java |
| jadx 1.5.0 | Dex→Java 反编译 | `jadx` | 需 Java |
| dex2jar 2.4 | Dex→Jar | `dex2jar` | 需 Java，`d2j-*` 系列命令 |
| radare2 | 逆向工程框架（`r2`） | `radare2` | 发行版包 |
| binwalk | 固件/文件签名扫描与雕刻 | `binwalk` | 发行版包或 pip |
| frida-tools | 动态插桩（`frida`/`frida-ps`/`frida-ls-devices`） | `frida` | pip 安装；操作真机需目标端 frida-server |

## 一次典型流程（分析某 APK）

1. `apktool_decode`（先 `no_src=true` 快速看资源与 Manifest）→ 找到入口/权限。
2. `jadx_decompile` → 阅读接近原始的 Java 逻辑。
3. 如需动态验证：`frida_ps`（`usb=true`）定位进程 → 自行编写 frida 脚本插桩。
