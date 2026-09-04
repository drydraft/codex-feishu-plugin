# Codex Feishu Plugin

让 Codex 通过飞书官方 [`lark-cli`](https://github.com/larksuite/cli) 和其运行时提供的 `lark-*` skills，安全地处理飞书/Lark 文档、云盘、知识库、多维表格、电子表格、消息、日历、审批等工作。

- 公开仓库：<https://github.com/drydraft/codex-feishu-plugin>
- 许可证：[MIT](LICENSE)
- 支持系统：Windows、macOS、Linux
- 安装方式：本地 Codex 插件市场

> 本项目是 Codex 的飞书工作流路由插件，不是独立的飞书 API SDK。实际命令、权限范围和业务能力以本机安装版本的 `lark-cli` 帮助与 skills 为准。

## 最快安装：把下面整段复制给 AI

在 Codex 或其他能操作本机终端的 AI 中，新建任务并完整粘贴下面的提示词。AI 会自动判断当前操作系统，安装插件，然后引导你在浏览器中完成飞书授权。

```text
请帮我从公开仓库 https://github.com/drydraft/codex-feishu-plugin 安装 Codex Feishu Plugin，并完成首次配置和登录。请直接执行，不要只给我步骤说明。

要求：
1. 先检测当前操作系统和终端环境，并检查 git、node、npx、codex、Python 是否可用；Python 必须为 3.9 或更高版本。缺少前置软件时，明确告诉我缺什么以及官方安装方式，不要使用来路不明的安装包。
2. 如果本机还没有仓库，请把它克隆到合适的用户项目目录；如果已经存在同一仓库，请确认工作区没有会被覆盖的修改，再执行 git pull --ff-only。不要删除或覆盖用户现有文件。
3. 进入仓库后按系统运行官方脚本：
   - Windows：powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
   - macOS/Linux：sh ./scripts/install.sh
4. 安装过程中若 lark-cli 尚未安装，允许安装脚本调用官方入口 npx @larksuite/cli@latest install。
5. 安装完成后，阅读仓库中的 docs/deployment.md，以及已安装插件的 feishu-setup 与 feishu-workflow-router skill，再进行配置。不要猜测当前 lark-cli 的参数，先查看当前版本帮助。
6. 先运行 lark-cli config init --new。涉及 App Secret、token 或其他凭据时，只允许我在 CLI 的受保护交互提示或官方网页中亲自输入；不要让我把凭据发送到聊天、写入命令行、.env、日志或仓库。
7. 配置完成后运行 lark-cli auth login，打开或提供官方飞书授权页面并暂停，等我亲自扫码/登录和确认授权后再继续。不要代替我确认账户授权。
8. 授权完成后依次验证：codex plugin list、lark-cli --version、lark-cli skills list、lark-cli profile list、lark-cli auth status --json --verify、lark-cli whoami。
9. 不要复制其他机器的 lark-cli profile、浏览器会话或凭据文件，也不要在验收阶段修改任何飞书业务数据。
10. 最后汇报：插件是否安装成功、lark-cli 版本、当前 profile、用户和机器人身份状态、仍缺少的权限或需要我完成的动作。若中途遇到错误，请先诊断并尝试安全修复；只有需要我输入敏感信息或亲自授权时才暂停。
```

授权完成后，建议重新打开一个 Codex 任务，让新安装的插件和 skills 被完整加载。

## 手动安装

### 前置条件

本机需要以下命令：

- `git`
- `node` 与 `npx`
- `codex`
- Python 3.9 或更高版本：Windows 通常使用 `python`，macOS/Linux 通常使用 `python3`

安装脚本只负责安装官方 `lark-cli`、注册本地插件市场、安装插件并运行验证；不会自动登录飞书，也不会读取或保存你的 App Secret。

### 1. 克隆公开仓库

```bash
git clone https://github.com/drydraft/codex-feishu-plugin.git
cd codex-feishu-plugin
```

### 2. 运行安装脚本

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

macOS/Linux：

```sh
sh ./scripts/install.sh
```

脚本会完成以下工作：

1. 检查必要命令和 Python 版本；
2. 找不到 `lark-cli` 时，通过 `npx @larksuite/cli@latest install` 调用官方安装入口；
3. 将当前仓库注册为名为 `codex-feishu` 的本地 Codex 市场；
4. 安装 `codex-feishu@codex-feishu`；
5. 运行仓库测试、插件结构检查和 `lark-cli` 只读验证。

更完整的分平台说明见 [部署与首次配置指南](docs/deployment.md)。

## 首次配置与飞书授权

插件安装成功不等于飞书账号已经登录。每台机器都要独立完成配置和 OAuth，不要复制其他机器的 profile 或凭据。

```text
lark-cli --version
lark-cli skills list
lark-cli profile list
lark-cli doctor --offline
lark-cli config init --new
```

`lark-cli config init --new` 是交互式配置。App Secret、token 等敏感值只能在 CLI 的受保护提示或飞书官方页面中输入，不要放入命令参数、聊天记录、Issue、日志或仓库。

配置完成后发起用户登录：

```text
lark-cli auth login
```

请在打开的飞书官方页面中亲自登录并确认授权。完成后验证当前 profile 和实际身份：

```text
lark-cli profile list
lark-cli auth status --json --verify
lark-cli whoami
```

`auth status` 用于查看用户与机器人身份是否可用，`whoami` 用于确认当前实际登录人。`lark-cli` 1.0.93 的 `whoami` 不需要额外 JSON 参数；其他版本请以本机 `--help` 为准。

## 可以处理哪些飞书工作

插件会根据请求选择匹配的官方运行时 skill，常见场景包括：

- 飞书文档、知识库和云盘文件；
- 多维表格 Base、电子表格、视图、仪表盘和工作流；
- 即时消息、群聊与卡片；
- 日历、任务、审批与考勤；
- 会议、妙记及其他当前 `lark-cli` 已公开的能力；
- 飞书身份、scope、资源共享和授权问题排查。

安装后可以直接对 Codex 说：

```text
查看我的飞书登录状态，并告诉我用户身份和机器人身份是否都可用。
```

```text
读取这个飞书多维表格，先分析字段和视图，不要修改数据：<粘贴 Base 链接>
```

```text
在执行任何写操作前先给我看 dry-run；涉及删除、覆盖或扩大权限时必须再次向我确认。
```

## 工作原理与信任边界

```text
你的请求
  -> Codex Feishu 路由 skill
  -> 本机官方 lark-cli 与对应 lark-* skill
  -> 本机保存的 profile 和用户亲自完成的 OAuth
  -> 飞书官方接口
```

本仓库只提供插件清单、安装脚本和工作流路由说明：

- 不内置或转存 token、App Secret、`.env`、浏览器会话和私人飞书数据；
- 不复制或修改其他产品的私有配置；
- 不在 CI 中登录飞书或调用飞书业务 API；
- 写操作、高风险操作和所需 scope 由当前 `lark-cli`、对应 skill 及用户授权共同约束；
- 资源访问还取决于飞书应用权限、用户授权、资源共享权限和当前所选 profile。

## 更新

在仓库目录执行：

```text
git pull --ff-only
```

然后重新运行当前系统的安装脚本。安装器会重新校验市场路径并安装最新本地版本；不会迁移或覆盖 OAuth 凭据。

更新后可单独运行验证脚本：

- Windows：[scripts/verify.ps1](scripts/verify.ps1)
- macOS/Linux：[scripts/verify.sh](scripts/verify.sh)

## 卸载

```text
codex plugin remove codex-feishu@codex-feishu
codex plugin marketplace remove codex-feishu
```

这些命令只移除本机 Codex 插件和市场配置，不会删除飞书云端数据，也不会自动撤销飞书 OAuth。确认不再需要仓库后，再用操作系统的常规方式删除本地克隆目录。

## 常见问题

### 找不到 `lark-cli`

先确认 `node --version` 和 `npx --version` 正常，再重新执行安装脚本。若刚完成安装，请关闭并重新打开终端，让 PATH 变化生效。

### 已登录但仍然无权访问文档或 Base

依次检查：当前 profile、实际用户身份、应用 scope、用户授权、资源是否分享给当前用户，以及对应 API 是否支持当前身份。不要通过盲目扩大权限来代替诊断。

### 安装后 Codex 没有识别插件

运行 `codex plugin list` 检查 `codex-feishu`，然后新建或重启 Codex 任务。若市场目录发生过变化，重新运行安装脚本即可修正注册路径。

### 不确定应该用哪个命令

先运行 `lark-cli skills list`，再读取 `lark-shared` 和匹配业务领域的 skill；命令参数始终以当前版本的 `--help` 与 schema 为准。详细排查路径见 [插件故障排查表](plugins/codex-feishu/skills/feishu-setup/references/troubleshooting.md)。

## 开发与验证

仓库测试不需要飞书账号或凭据：

```text
python -m unittest discover -s tests -v
```

CI 在 Windows 与 Ubuntu 上运行确定性测试和脚本语法检查。上游 CLI 的实现、版本和许可证请查看 [`larksuite/cli`](https://github.com/larksuite/cli)。
