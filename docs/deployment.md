# 部署与首次配置

本指南从一台新机器开始安装公开仓库中的 Codex Feishu Plugin。它只安装官方 `lark-cli`、注册本地 Codex 市场、安装插件并执行本地静态检查；不会登录、不会在命令行要求 App Secret，也不会在验证期间调用任何飞书业务 API。

## 0. 获取公开仓库

仓库为 <https://github.com/drydraft/codex-feishu-plugin>，可以直接通过 HTTPS 克隆，不需要仓库读取授权。不要把 GitHub token、飞书 profile 或私人文件写入仓库。

```text
git clone https://github.com/drydraft/codex-feishu-plugin.git
cd codex-feishu-plugin
```

需要的本机命令为 `git`、`node`、`npx`、`codex` 和 Python（Windows 为 `python`；macOS/Linux 通常为 `python3`）。验证脚本要求 **Python 3.9 或更高版本**；GitHub Actions 使用 Python 3.11。安装器会在 `lark-cli` 不存在时运行官方安装入口 `npx @larksuite/cli@latest install`，但不会自动运行配置或登录。

## 1. 安装插件

### Windows PowerShell

在克隆目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

脚本会检查前置命令、在需要时安装官方 CLI、注册当前目录为 `codex-feishu` 市场、安装 `codex-feishu@codex-feishu`，然后执行 [verify.ps1](../scripts/verify.ps1)。它不会接触飞书账户或业务数据。

### macOS/Linux

在克隆目录运行：

```sh
sh ./scripts/install.sh
```

脚本执行相同的本地步骤，随后运行 [verify.sh](../scripts/verify.sh)。若 shell 报告缺少命令，先按操作系统的正常方式安装对应前置条件、重新打开终端后再运行。

## 2. 每台机器单独配置和 OAuth

安装器不会登录。每台机器及其目标飞书/Lark 身份都要在本机完成交互式配置，不能复制其他机器的 profile、浏览器会话或凭据文件。

1. 先进行本地只读发现：

   ```text
   lark-cli --version
   lark-cli skills list
   lark-cli profile list
   lark-cli doctor --offline
   ```

2. 通过交互提示创建或选择本机应用配置：

   ```text
   lark-cli config init --new
   ```

   仅在 CLI 的受保护交互提示中输入敏感值；不要把 App Secret、token 或任何凭据放到命令行、`.env`、日志或仓库中。按实际业务的最小权限配置应用，并先从 `lark-cli skills list`、`lark-cli skills read lark-shared` 及匹配 skill 的帮助中核实范围要求。

3. 告知用户将打开浏览器，然后在本机发起 OAuth：

   ```text
   lark-cli auth login
   ```

   该命令是交互式步骤。不要让安装脚本、CI 或无人值守任务代替用户完成浏览器授权。

4. OAuth 成功后验证选定 profile 和实际身份：

   ```text
   lark-cli profile list
   lark-cli auth status --json --verify
   lark-cli whoami
   ```

   后两项用于验证当前登录，可能连接飞书；它们不属于静态验证或 CI。已安装的 1.0.93 版本中，`lark-cli whoami` 不带额外 JSON flag 也会输出 JSON；升级后必须以当前运行时帮助为准。业务调用前再由插件路由 skill 选择用户或 bot/app 身份，并确认资源共享与 scope。

## 3. 无凭据验收清单

在不登录、不配置应用、也不访问飞书的情况下，可以确认下列项目：

- `python -m unittest discover -s tests -v` 通过；
- Windows：PowerShell 可解析 `scripts/install.ps1` 与 `scripts/verify.ps1`；
- macOS/Linux：`bash -n scripts/install.sh` 和 `bash -n scripts/verify.sh` 通过；
- `plugins/codex-feishu/.codex-plugin/plugin.json` 与两项 bundled skills 都通过仓库的确定性测试；
- 验证过程中没有执行 `lark-cli auth login`、`lark-cli config init --new` 或任何飞书业务 API。

运行 [README](../README.md) 指定的安装器后，`codex plugin list` 应能列出已安装插件。这个检查无需 Codex 账户、OAuth 或飞书访问；它只确认本机 CLI 的插件配置。

### 验证器位置与覆盖

`verify.ps1` 和 `verify.sh` 会在存在时调用 Codex 安装中 plugin-creator 提供的 `validate_plugin.py`，作为额外的严格检查。默认位置分别是 `$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py`（Windows）和 `$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py`（macOS/Linux）。默认路径不是每台机器都必然存在：未设置覆盖且默认路径缺失时，验证器会输出 `Codex plugin validator is not installed; skipping the optional external validator.`，随后继续运行仓库 contract tests。

在 Windows 上，可先确认默认位置，再将环境变量指向实际验证器后运行验证：

```powershell
$defaultValidator = "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py"
Test-Path $defaultValidator
$env:CODEX_PLUGIN_VALIDATOR = "D:\tools\codex\validate_plugin.py"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1
```

在 macOS/Linux 上，先检查默认位置；若本机验证器在其他位置，使用同一环境变量覆盖：

```sh
test -f "$HOME/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py"
CODEX_PLUGIN_VALIDATOR="/opt/codex/validate_plugin.py" sh ./scripts/verify.sh
```

仅在路径实际指向可信的本机 `validate_plugin.py` 时才设置覆盖值；一旦显式设置 `CODEX_PLUGIN_VALIDATOR`，该路径缺失或该验证器失败都会以非零状态结束验证。不要下载未知脚本，也不要将验证器路径与任何凭据一起保存到仓库。

## 4. 更新、卸载与故障排查

更新时在克隆目录执行 `git pull --ff-only`，然后重新运行本平台安装脚本。它不会迁移或共享 OAuth；如 identity 已失效，回到本页的交互式步骤。

卸载本机插件和市场使用：

```text
codex plugin remove codex-feishu@codex-feishu
codex plugin marketplace remove codex-feishu
```

这些命令不删除远端飞书数据，也不撤销应用授权。认证、scope、资源共享或远端服务问题应先运行 `lark-cli doctor --offline`，再按 [插件故障排查](../plugins/codex-feishu/skills/feishu-setup/references/troubleshooting.md) 分类；不要将登录错误误判为 scope 或共享权限问题。

如需某一业务命令，始终先读取当前安装的 `lark-cli` skill 和帮助。官方来源为 [larksuite/cli](https://github.com/larksuite/cli)；本仓库不承诺尚未由当前运行时公开的 API、参数或能力。
