# dsh-feishu — 飞书/Lark 路由插件（DeepSeek Harness）

`dsh-feishu` 是 **DSH（DeepSeek Harness）** 的原生 bundle：把飞书/Lark 工作路由到本机安装的官方 [`lark-cli`](https://github.com/larksuite/cli) 及其内嵌 `lark-*` 技能。

它与同仓库的 Codex 插件共享安全边界与路由顺序，但注册方式不同：

| | Codex 版 | DSH 版 |
| --- | --- | --- |
| 载体 | `.codex-plugin/plugin.json` + `agents/openai.yaml` | `package.json` 的 `dsh.bundle.patch` + Cordis `apply()` |
| 技能注册 | Codex 显式调用（`$codex-feishu:<skill>`） | `ctx.skills.register()`，模型目录可调用 |
| 业务执行 | 本机 `lark-cli` | 本机 `lark-cli` |

插件**不含**飞书 API 封装、**不含**凭证、**不预置** secret，也**不内置** 28 个 `lark-*` 技能正文——那些始终由 `lark-cli skills read` 按需读取，跟随 CLI 版本走。

## 安装（桌面端 DSH）

把本目录加入当前 profile 的 bundle 依赖，然后重启客户端：

```powershell
# 1. 复制到本地插件目录
Copy-Item -Recurse .\plugins\dsh-feishu "$env:USERPROFILE\.dsh\local-plugins\dsh-feishu"

# 2. 在 profile 的 package.json dependencies 增加
#    "dsh-feishu": "link:C:/Users/<you>/.dsh/local-plugins/dsh-feishu"
# 3. 在 profile 的 dsh.profile.bundles 增加 "dsh-feishu"
# 4. 安装并重启
```

仓库根目录的 `scripts/install-dsh.ps1` 会自动完成第 2–4 步并保留备份。

不想重启也能用：把 `~/.dsh/skills/<skill>` 建成指向 bundle `skills/<skill>` 的目录联接（Windows Junction），Watcher 会在数秒内把技能加入当前会话目录；重启后 bundle 的运行时注册优先，同名同内容。

## 技能

| 技能 | 用途 |
| --- | --- |
| `feishu-workflow-router` | 识别飞书资源与意图，按读/写风险选择领域技能并执行；写入前 dry-run，高风险写操作强制确认。 |
| `feishu-setup` | 安装、配置、登录与排障 `lark-cli`（OAuth 交互边界、身份核验、失败分类）。 |

## 本地验证

```bash
python -m unittest tests.test_dsh_plugin -v
```

或直接加载模块（无需宿主）：

```bash
node --check plugins/dsh-feishu/index.js
```
