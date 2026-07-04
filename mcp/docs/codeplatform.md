# clenv-codeplatform —— 代码平台访问 MCP

服务器文件：`servers/codeplatform_mcp.py` ｜ 版本：1.0.0

封装 git 本地操作与 GitHub/GitLab 平台访问。**默认只读**；会改变远端状态的写操作
统一需要显式 `allow_write=true`，且不在结果中回显任何令牌。

## 工具清单

| 工具 | 用途 | 关键参数 | 是否写 |
|---|---|---|---|
| `git_status` | 查看仓库状态 | `repo?` | 否 |
| `git_log` | 提交历史 | `repo?`,`n?`,`path?` | 否 |
| `git_diff` | 查看改动 | `repo?`,`staged?`,`ref?` | 否 |
| `git_clone` | 克隆仓库到本地 | `url`,`dest?`,`depth?` | 否（只拉取） |
| `git_push` | 推送到远端 | `remote?`,`branch?`,`allow_write` | **是** |
| `gh_api` | GitHub CLI 调 API | `endpoint`,`method?`,`fields?`,`allow_write?` | GET 否 / 其它是 |
| `gh_repo_view` | 查看仓库概况 | `repo` | 否 |
| `glab_api` | GitLab CLI 调 API | `endpoint`,`method?`,`allow_write?` | GET 否 / 其它是 |
| `http_get` | curl 只读 HTTP GET | `url`,`headers?` | 否 |

## 鉴权

- `gh` / `glab` 沿用本机既有登录态（`gh auth login` / `glab auth login`）。
- `git_push` 使用本机 git 凭证（credential helper / SSH key）。
- 工具**不接受**、也**不回显**任何令牌明文。

## 涉及工具与版本

| 工具 | 说明 | 安装项名 |
|---|---|---|
| git 2.x | 本地版本控制 | `git` |
| GitHub CLI `gh` | GitHub 平台 CLI（含 `gh api`） | `gh` |
| GitLab CLI `glab` 1.44.0 | GitLab 平台 CLI（含 `glab api`） | `glab` |
| curl | 通用 HTTP 客户端 | `curl` |

## 写操作示例（须显式授权）

```json
{"jsonrpc":"2.0","id":9,"method":"tools/call",
 "params":{"name":"git_push","arguments":{"remote":"origin","branch":"main","allow_write":true}}}
```

不带 `allow_write:true` 时会返回拦截提示，不执行任何推送。
