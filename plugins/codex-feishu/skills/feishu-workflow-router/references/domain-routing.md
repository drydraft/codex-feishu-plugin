# Feishu domain routing index

Use this index only after `lark-cli skills list`. Match the requested resource and intent to a currently listed `lark-*` skill, then read that skill. The labels below are selectors, not hard-coded command or skill names.

| Domain | Route from the current runtime |
| --- | --- |
| docs | Select the listed skill whose current documentation covers documents. |
| drive | Select the listed skill whose current documentation covers Drive files or folders. |
| wiki | Select the listed skill whose current documentation covers Wiki spaces or nodes. |
| sheets | Select the listed skill whose current documentation covers spreadsheets. |
| base | Select the listed skill whose current documentation covers Base/Bitable records or tables. |
| slides | Select the listed skill whose current documentation covers slides or presentations. |
| whiteboard | Select the listed skill whose current documentation covers whiteboards. |
| im | Select the listed skill whose current documentation covers chats, messages, or IM. |
| calendar | Select the listed skill whose current documentation covers calendars or events. |
| mail | Select the listed skill whose current documentation covers mail. |
| task | Select the listed skill whose current documentation covers tasks. |
| approval | Select the listed skill whose current documentation covers approvals. |
| attendance | Select the listed skill whose current documentation covers attendance. |
| okr | Select the listed skill whose current documentation covers OKRs. |
| meeting | From the current `lark-cli skills list`, select and read the listed meeting-related skill; never substitute a remembered legacy alias. |
| contact | Select the listed skill whose current documentation covers contacts or users. |
| event | Select the listed skill whose current documentation covers events. |

If more than one listed skill plausibly matches, inspect each candidate's current description and read the one whose documented resource and operation match the request. If none matches, inspect the runtime's documented raw API route only after reading `lark-shared`; otherwise report that the current installation does not expose a supported route.
