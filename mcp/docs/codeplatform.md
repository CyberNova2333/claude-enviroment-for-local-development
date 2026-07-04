# clenv-codeplatform —— 代码平台访问 MCP

服务器文件：`servers/codeplatform_mcp.py` ｜ 版本：2.0.0 ｜ 工具数：15

封装 git 本地操作与 GitHub/GitLab 平台访问。**默认只读**；会改变本地历史或远端状态的写操作
统一需要显式 `allow_write=true`，且不接受、不回显任何令牌。每个工具带只读/写标注与调用示例。

## 工具清单

| 工具 | 用途 | 关键参数 | 是否写 |
|---|---|---|:--:|
| `git_status` | 仓库状态 | `repo?` | 否 |
| `git_log` | 提交历史 | `repo?`,`n?`,`path?` | 否 |
| `git_diff` | 查看改动 | `repo?`,`staged?`,`ref?` | 否 |
| `git_show` | 某提交详情/历史文件内容 | `repo?`,`target?` | 否 |
| `git_blame` | 逐行追溯作者/提交 | `path`,`start?`,`end?` | 否 |
| `git_grep` | 已跟踪文件中正则搜索 | `pattern`,`repo?` | 否 |
| `git_branch_list` | 本地/远端分支 | `repo?` | 否 |
| `git_clone` | 克隆仓库到本地 | `url`,`dest?`,`depth?` | 否（只拉取） |
| `git_commit` | 创建提交 | `message`,`add_all?`,`allow_write` | **是** |
| `git_push` | 推送到远端 | `remote?`,`branch?`,`allow_write` | **是** |
| `gh_repo_view` | GitHub 仓库概况 | `repo` | 否 |
| `gh_list` | 列 Issue/PR | `repo`,`kind?`,`state?`,`limit?` | 否 |
| `gh_api` | GitHub REST/GraphQL | `endpoint`,`method?`,`fields?`,`allow_write?` | GET 否/其它是 |
| `glab_api` | GitLab API | `endpoint`,`method?`,`allow_write?` | GET 否/其它是 |
| `http_get` | 只读 HTTP GET | `url`,`headers?` | 否 |

## 鉴权

- `gh`/`glab` 沿用本机既有登录态（`gh auth login` / `glab auth login`）。
- `git_commit`/`git_push` 使用本机 git 凭证（credential helper / SSH key）。
- 工具**不接受**、也**不回显**任何令牌明文。

## 涉及工具与版本

| 工具 | 说明 | 安装项名 |
|---|---|---|
| git 2.x | 本地版本控制 | `git` |
| GitHub CLI `gh` | GitHub 平台 CLI | `gh` |
| GitLab CLI `glab` 1.44.0 | GitLab 平台 CLI | `glab` |
| curl | 通用 HTTP 客户端 | `curl` |

## 写操作示例（须显式授权）

```json
{"jsonrpc":"2.0","id":9,"method":"tools/call",
 "params":{"name":"git_commit","arguments":{"message":"修复空指针","add_all":true,"allow_write":true}}}
```

不带 `allow_write:true` 时会返回拦截提示，不执行任何写动作。
