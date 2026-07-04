# clenv-reverse —— 应用/二进制逆向 & 静态分析 MCP

服务器文件：`servers/reverse_mcp.py` ｜ 版本：2.0.0 ｜ 工具数：13

> ⚠️ **合规提示**：以下工具仅用于**你拥有合法授权**的安全研究、CTF、教学、
> 互操作/兼容性分析等场景。是否合规、是否获授权由使用者自行负责。

每个工具带只读/写标注与调用示例。典型顺序：先 `file_type`（codec）/`elf_info` 摸清目标格式
→ 再 `strings`/`objdump`/`jadx` 深入 → 需要动态时用 `frida`。

## 工具清单

| 工具 | 用途 | 只读 | 关键参数 |
|---|---|:--:|---|
| `apktool_decode` | 反编译 APK（资源+smali） | | `apk`,`out_dir?`,`no_src?` |
| `apktool_build` | 回编译目录为 APK | | `src_dir`,`out_apk?` |
| `jadx_decompile` | APK/DEX/JAR → Java 源码 | | `input`,`out_dir?` |
| `dex2jar` | .dex/.apk → .jar | | `input`,`out_jar?` |
| `elf_info` | ELF 头/节区/动态段/依赖（readelf） | ✓ | `binary`,`sections?` |
| `objdump_disasm` | 反汇编（Intel 语法） | ✓ | `binary`,`symbol?` |
| `nm_symbols` | 符号表（含动态符号） | ✓ | `binary`,`dynamic?` |
| `checksec` | 安全加固检查（RELRO/Canary/NX/PIE） | ✓ | `binary` |
| `radare2_analyze` | r2 批处理分析 | ✓ | `binary`,`commands?` |
| `gdb_batch` | gdb 批处理静态检视 | ✓ | `binary`,`commands` |
| `binwalk_scan` | 固件签名扫描/雕刻 | | `input`,`extract?` |
| `frida_list_devices` | 列出 frida 设备 | ✓ | 无 |
| `frida_ps` | 列出目标进程 | ✓ | `usb?`,`remote?` |

### 常用命令片段
- `elf_info` 的 `sections`：`-h` 只头、`-hSd` 头+节区+动态段（默认）、`-a` 全部。
- `objdump_disasm` 的 `symbol`：只反汇编某函数，如 `main`。
- `radare2_analyze` 的 `commands`：`iI` 文件信息、`izz` 全字符串、`aaa;afl` 列函数、`pdf @ main`。
- `gdb_batch` 的 `commands`：`["disassemble main","info functions"]`。

## 涉及工具与版本

| 工具 | 说明 | 安装项名 | 备注 |
|---|---|---|---|
| apktool 2.9.3 | APK 资源/smali 反编译 | `apktool` | 需 Java |
| jadx 1.5.0 | Dex→Java 反编译 | `jadx` | 需 Java |
| dex2jar 2.4 | Dex→Jar | `dex2jar` | 需 Java，`d2j-*` 命令 |
| radare2 | 逆向框架（`r2`） | `radare2` | 发行版包 |
| binutils | `readelf`/`objdump`/`nm`/`strings` | `binutils` | 发行版包 |
| checksec | 二进制加固检查 | `checksec` | 发行版包或官方脚本兜底 |
| gdb | 调试器（此处仅批处理静态检视） | `gdb` | 发行版包 |
| binwalk | 固件签名扫描与雕刻 | `binwalk` | 发行版包或 pip |
| frida-tools | 动态插桩（`frida`/`frida-ps`/`frida-ls-devices`） | `frida` | pip；操作真机需目标端 frida-server |

## 一次典型流程（分析某 ELF）

1. `file_type`（codec）确认是 ELF 及架构 → `elf_info` 看结构与依赖。
2. `checksec` 评估加固；`nm_symbols`/`strings_extract` 找入口与线索。
3. `objdump_disasm`（或 `radare2_analyze aaa;afl` + `pdf @ 函数`）读关键逻辑。
