# lark-cli 技能同步记录（2026-10-20）

> 时间：2026-10-20（Asia/Shanghai）  
> 动作：用本机已装 **lark-cli 1.0.98** 内嵌技能，刷新 `C:\Users\Administrator\.agents\skills\lark-*`  
> 结论：技能内容已对齐 1.0.98；**这不等于 Trae 插件升级**（见末尾）。

## 一、三方状态对比

| 来源 | 版本 | 内置 lark-cli | 技能数量 | 说明 |
| --- | --- | --- | --- | --- |
| Trae 插件 `trae-remote-official:lark` | 1.0.5 | 1.0.94（`bin\lark-cli.exe --version`） | 27（467 个 .md） | Trae 市场最新，仍落后 |
| 本机已装 lark-cli | **1.0.98**（npm `latest`） | — | 28（492 个 .md 内嵌） | 本次同步的权威来源 |
| `~/.agents/skills` | 1.0.94 时期内容 | — | 28（544 文件 / 509 .md） | 同步前现状 |

同步后 `~/.agents/skills`：**28 技能 / 547 文件 / 512 .md**。

## 二、逐技能对比

| 技能名 | 同步前版本 | CLI 1.0.98 版本 | 变化 | 文件数变化 |
| --- | --- | --- | --- | --- |
| lark-approval | 1.2.0 | 1.2.0 | 相同 | 17 → 17 |
| lark-apps | 1.0.0 | 1.0.0 | 内容更新（9 篇改写，+1 新增 `references/lark-apps-export.md`，-2 删除） | 55 → 54 |
| lark-attendance | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-base | **1.2.21** | **1.2.23** | 升级（13 篇改写，+1 新增 `references/lark-base-view.md`） | 26 → 27 |
| lark-calendar | 1.0.0 | 1.0.0 | 内容更新（4 篇改写，+1 新增 `references/lark-calendar-meeting-relation.md`） | 14 → 15 |
| lark-contact | 1.0.0 | 1.0.0 | 相同 | 4 → 4 |
| lark-doc | 无 version 字段 | 无 version 字段 | 内容更新（7 篇改写） | 44 → 44 |
| lark-drive | 1.0.0 | 1.0.0 | 内容更新（28 篇改写） | 61 → 61 |
| lark-event | 1.0.0 | 1.0.0 | 相同 | 8 → 8 |
| lark-im | 1.0.0 | 1.0.0 | 内容更新（24 篇改写） | 61 → 61 |
| lark-mail | 1.0.0 | 1.0.0 | 内容更新（10 篇改写，+2 新增 `thread-modify` / `thread-trash`） | 34 → 36 |
| lark-markdown | 1.2.2 | 1.2.2 | 内容更新（5 篇改写） | 6 → 6 |
| lark-meeting | 1.0.0 | 1.0.0 | 内容更新（8 篇改写） | 30 → 30 |
| lark-minutes | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-note | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-okr | 1.0.0 | 1.0.0 | 相同 | 26 → 26 |
| lark-openapi-explorer | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-shared | 1.1.0 | 1.1.0 | 内容更新（1 篇改写） | 7 → 7 |
| lark-sheets | **3.1.8** | **3.5.2** | 升级（19 篇改写，-1 删除 `references/lark-sheets-legacy-command-migration.md`） | 29 → 28 |
| lark-skill-maker | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-slides | 1.0.0 | 1.0.0 | 内容更新（16 篇改写） | 50 → 50 |
| lark-task | 1.0.0 | 1.0.0 | 内容更新（18 篇改写，+1 新增 `references/lark-task-sections.md`） | 18 → 19 |
| lark-vc | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-vc-agent | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-whiteboard | 1.0.0 | 1.0.0 | 相同（24 篇逐字一致；7 篇 `elements/*.md` 仅本地保留） | 31 → 31 |
| lark-wiki | 1.0.3 | 1.0.3 | 内容更新（7 篇改写） | 14 → 14 |
| lark-workflow-meeting-summary | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| lark-workflow-standup-report | 1.0.0 | 1.0.0 | 相同 | 1 → 1 |
| **合计** | — | — | 2 个版本升级，14 个技能内容有变化，14 个完全未变 | **544 → 547** |

## 三、变化结论

- **版本升级（2 个）**：`lark-base 1.2.21 → 1.2.23`、`lark-sheets 3.1.8 → 3.5.2`（与实测一致）。
- **内容有变化（14 个技能，合计 169 个 .md 文件被改写，含上面 2 个版本升级）**：lark-apps、lark-base、lark-calendar、lark-doc、lark-drive、lark-im、lark-mail、lark-markdown、lark-meeting、lark-shared、lark-sheets、lark-slides、lark-task、lark-wiki。可见 1.0.94 → 1.0.98 的 CLI 迭代大量落在文档/路由上，而非版本号。
- **新增 .md（6 个）**：`lark-apps/references/lark-apps-export.md`、`lark-base/references/lark-base-view.md`、`lark-calendar/references/lark-calendar-meeting-relation.md`、`lark-mail/references/lark-mail-thread-modify.md`、`lark-mail/references/lark-mail-thread-trash.md`、`lark-task/references/lark-task-sections.md`。
- **删除 .md（3 个，CLI 1.0.98 不再提供且无任何引用）**：
  - `lark-apps/creative-design/agents/fork-verifier-agent.md`
  - `lark-apps/creative-design/agents/vision-probe-agent.md`
  - `lark-sheets/references/lark-sheets-legacy-command-migration.md`
- **保留的“CLI 未内嵌但仍被引用”文件（20 个，未删）**：`lark-apps/creative-design/*` 13 篇 + `lark-whiteboard/elements/*` 7 篇。1.0.98 的 `lark-apps/SKILL.md` 仍链接 `creative-design/creative-design.md`，`lark-whiteboard` 仍链接 `elements/schema.md` 等；删掉会留下断链，故保留并在此登记。若后续确认上游已废弃，可再清理。
- **非 .md 资源（35 个）**：脚本、HTML 模板、PNG、XML、JSON 全部原样保留，逐文件 SHA-256 与备份完全一致（0 变更）。CLI 不内嵌机器资源，本地副本仍是权威。

## 四、调用策略

- 28 个 `SKILL.md` 的 YAML frontmatter 均保留 `disable-model-invocation: true`（本次 28 个全部由脚本补插，置于 frontmatter 内、闭合 `---` 之前），**模型侧不注入任何 lark 技能描述**，避免 28 条长描述撑爆每次请求。
- 需要时显式调用，文档通过 CLI 按需读取：`lark-cli skills list`、`lark-cli skills read <path>`。

## 五、备份与回滚

- 备份：`C:\Users\Administrator\.agents\skills.backup-20261020`（完整 `skills` 树，593 文件 / 6.7 MB）
- 回滚（git-bash）：
  ```bash
  cd /c/Users/Administrator/.agents
  rm -rf skills && cp -a skills.backup-20261020 skills
  ```
- 回滚（PowerShell）：
  ```powershell
  Set-Location C:\Users\Administrator\.agents
  Remove-Item -Recurse -Force skills
  Copy-Item -Recurse skills.backup-20261020 skills
  ```

## 六、校验结果

| 校验项 | 结果 |
| --- | --- |
| 技能数量 | 28（CLI 28 / 本地 28，无 cli-only、无 local-only） |
| 写入 .md 文件 | 492 |
| 与 `lark-cli skills read` 内容差异（仅允许插入 disable-model-invocation 一行） | **0 处不一致** |
| SKILL.md frontmatter（name / description / 唯一 flag） | 28/28 通过 |
| 版本一致性（CLI 报版本 vs 安装版 SKILL.md） | 27/27 一致（lark-doc 无版本字段） |
| 非 .md 资源保留 | 35/35，0 变更 |
| 记忆体策略 | 全部 `disable-model-invocation: true` |

## 七、重要边界

**本次同步不等于 Trae 插件升级。** Trae 市场里的 `trae-remote-official:lark` 仍是 **1.0.5**，其内置 `lark-cli.exe` 为 **1.0.94**、27 个技能，已落后于 npm `latest` 的 **1.0.98**（28 个技能）。要升级 Trae 侧需要等 Trae 插件发布新版本，本次仅刷新了 `~/.agents/skills` 这一份共享技能副本。
