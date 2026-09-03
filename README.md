# Codex Feishu Plugin

这是一个面向 Codex 的本地插件：它通过官方 [`larksuite/cli`](https://github.com/larksuite/cli)（命令名 `lark-cli`）及其当前安装的 `lark-*` skills，路由飞书/Lark 的工作请求。

本仓库采用 MIT 许可证，仓库地址为 <https://github.com/drydraft/codex-feishu-plugin>。该地址是私有仓库：克隆前，GitHub 帐户必须已经被授予该仓库读取权限；无法访问时请向仓库所有者申请权限，而不是复制其他机器的配置或凭据。

## 它能做什么

- 将文档、云盘、知识库、表格、Base、IM、日历、审批、考勤等请求交给当前安装的官方 `lark-cli` skills；实际可用的领域和命令以运行时 `lark-cli skills list`、skill 内容、帮助和 schema 输出为准。
- 在业务调用前引导检查 CLI、已选 profile 和用户或机器人身份；支持时先进行 `--dry-run`，高风险写操作先要求明确确认。
- 提供 Windows PowerShell 与 macOS/Linux shell 的安装和只读验证脚本。

## 它不是什么

这是 Codex 的包装与路由 skills，**不是** Trae 代码、不是复制的 Trae 插件、不是凭据桥接器，也没有打包或 vendoring 一整套官方 Feishu skills。它不直接调用飞书 API、不保存 token、App Secret、`.env` 凭据或私人飞书数据；这些认证信息由本机的 `lark-cli` 管理。

## 架构与信任边界

```text
Codex 请求
  -> codex-feishu 路由 skill
  -> 已安装的官方 lark-cli 与 lark-* skills
  -> 用户在本机完成的交互式 OAuth
  -> 官方 CLI 执行经运行时帮助确认的业务命令
```

插件只提供本仓库中的指令与路由索引。业务能力、参数、scope 与 API 是否存在不能从本文猜测，必须由所安装版本的 `lark-cli` 说明确认。静态测试和 CI 不会认证，也不会调用业务 API。

## 前置条件

安装机器需要能使用 `git`、`node`、`npx`、`python`（或 macOS/Linux 的 `python3`）以及 `codex`。Python 需为 **Python 3.9 或更高版本**；CI 使用 Python 3.11。安装脚本会在找不到 `lark-cli` 时调用官方 CLI 安装入口；不会替你创建飞书应用或登录。

请先克隆私有仓库，然后按平台执行安装：

```text
git clone https://github.com/drydraft/codex-feishu-plugin.git
cd codex-feishu-plugin
```

- Windows：`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1`
- macOS/Linux：`sh ./scripts/install.sh`

安装后按 [部署与首次配置指南](docs/deployment.md) 在每台机器上单独配置应用并完成 OAuth。

## 首次认证与身份确认

安装完成不等于已登录。先使用 `lark-cli config init --new` 通过受保护的交互提示建立本机应用配置，再执行 `lark-cli auth login` 完成浏览器 OAuth。随后以 `lark-cli auth status --json --verify` 和 `lark-cli whoami` 确认实际身份。已安装的 1.0.93 版本会在不带额外 JSON flag 时输出 JSON；升级后仍应以当前运行时帮助为准。完整的分平台步骤与无凭据验收清单在 [docs/deployment.md](docs/deployment.md)。

## 更新

在克隆目录更新到已审阅的提交，再重新运行对应平台的安装脚本；它会检查市场是否已注册并重新安装插件：

```text
git pull --ff-only
```

不要把别的机器的 `lark-cli` profile、浏览器会话或凭据文件复制到此仓库。更新后，重新执行本机只读验证脚本：Windows 使用 [scripts/verify.ps1](scripts/verify.ps1)，macOS/Linux 使用 [scripts/verify.sh](scripts/verify.sh)。

## 卸载

以下命令只移除本机 Codex 插件及市场配置；不会撤销飞书应用授权或删除远端业务数据：

```text
codex plugin remove codex-feishu@codex-feishu
codex plugin marketplace remove codex-feishu
```

确认不再需要本地副本后，再用操作系统的常规方式删除克隆目录。若还要撤销 OAuth 或删除 profile，请先查看已安装 `lark-cli` 的当前帮助，按该版本提供的本机管理流程操作。

## 常见问题与安全

- 找不到 `lark-cli`：确认 `node --version` 与 `npx --version`，再运行官方安装入口并打开新终端。
- 已登录但无法访问：不要盲目换账号或加大 scope；先区分 profile/身份、应用 scope、资源共享与远端 API 错误。可参考插件内的 [故障排查表](plugins/codex-feishu/skills/feishu-setup/references/troubleshooting.md)。
- 不确定命令或字段：运行 `lark-cli skills list`，阅读 `lark-cli skills read lark-shared` 与匹配领域 skill 的当前帮助；不要根据旧教程编造业务命令。

不要在命令行、Issue、日志或提交中放入 App Secret、token、会话文件、私人文档导出或 `.env` 凭据。上游项目与许可证信息请以 [`larksuite/cli`](https://github.com/larksuite/cli) 为准。
