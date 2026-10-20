---
name: feishu-setup
description: 当需要在新机器上安装、配置、登录或诊断官方飞书/Lark CLI（lark-cli），或飞书调用报认证/scope/分享错误时使用。
---

# 飞书 CLI 安装与诊断

以本机已安装的 `lark-cli` 为事实来源。先做本地只读检查；OAuth 是每台机器的交互边界。不要复用编辑器会话数据，不要把 App Secret 或 token 放到命令行，不要回显凭证，不要创建凭证 `.env`，不要提交本机配置。

## 只读发现

配置或登录前先跑：

```text
lark-cli --version
lark-cli skills list
lark-cli profile list
lark-cli doctor --offline
```

若 `lark-cli` 缺失，先确认 Node.js 前置条件：

```text
node --version
npx --version
```

任一缺失时用该操作系统的官方方式安装 Node.js，开新终端后重跑前置检查。不要假设当前 CLI 未发布的版本约束。两者可用后安装官方运行时，开新终端并重跑发现检查：

```text
npx @larksuite/cli@latest install
```

命令缺失或 flag 不同时，查看已安装的帮助与 `lark-cli skills list`，不要猜新命令。在选择 scope 或领域工作流前先读 `lark-cli skills read lark-shared`。

## 配置与登录

1. 用 `lark-cli config init --new` 创建独立的应用配置。敏感值只允许在它的受保护交互提示里输入；应用权限保持完成目标任务所需的最小集合。
2. 复核所选运行时技能要求的 app scope。没有当前 CLI 帮助、技能或 schema 输出，不要声称某个 scope 或 API 存在。
3. 告知用户登录会在本机打开浏览器交互流程，然后运行 `lark-cli auth login`。不要自动化该浏览器流程，也不要在其完成前继续。
4. 验证所选 profile 与实际身份：

   ```text
   lark-cli profile list
   lark-cli auth status --json --verify
   lark-cli whoami
   ```

在实测的 `lark-cli 1.0.98` 上，`lark-cli whoami` 本身已输出 JSON，不要额外加 JSON flag。运行时版本不同时，以已安装命令的帮助为准。这些检查是只读的，但可能联网校验当前登录；静态检查与 CI 必须在配置、认证或任何远端 API 调用之前停止。

## 先诊断再改动

先重跑 `lark-cli doctor --offline`，然后按 [troubleshooting.md](references/troubleshooting.md) 分类：CLI 缺失、应用配置、登录、scope、资源分享、远端 API。只收集脱敏后的命令输出。业务操作期间先查匹配的 `lark-*` 技能与命令帮助，诊断阶段不做写操作。
