# 飞书 CLI 排障

先跑 `lark-cli doctor --offline`，只保留脱敏输出。它不会认证，也不会调用远端 API。在实测的 `lark-cli 1.0.98` 上，`lark-cli whoami` 已输出 JSON；其他运行时版本以已安装命令的帮助为准。

| 类别 | 证据 | 安全的下一步 |
| --- | --- | --- |
| CLI 缺失 | 命令不存在，或 `--version` 失败 | 用 `npx @larksuite/cli@latest install` 安装；开新终端后重跑本地检查。 |
| 应用配置 | `config init --new` 未完成，或所选 profile 不是预期的 | 交互式创建或选择目标应用；密钥不要进入 shell、文件、日志或提交。 |
| 登录 | `auth status --json --verify` 报告无有效登录 | 请用户在本机浏览器完成 `auth login`，然后核验身份。 |
| scope | CLI 或 API 报告权限不足 | 读当前相关 `lark-*` 技能、命令帮助与 schema，只向应用负责人申请缺失的最小 scope。 |
| 资源分享 | 身份有效，但指定的文档、空间、群或记录不可访问 | 用 `lark-cli whoami` 确认实际身份，再让资源所有者只把必要资源分享给该身份。 |
| 远端 API | 认证、scope、分享都已确认，但调用返回服务错误 | 记录脱敏后的状态码、request id 与时间；查官方 CLI 帮助/状态，只有用户授权该业务操作时才重试。 |

不要把一类问题当成另一类的证据：有效登录不代表有 app scope 或资源分享，远端报错也不构成更换凭证的理由。
