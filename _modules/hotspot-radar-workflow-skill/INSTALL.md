# Hotspot Radar Workflow 安装与前置条件

## 这个 Skill 做什么

输入一个内容主题后，热点雷达会抓取抖音对标内容，按点赞、评论、收藏、分享、评论需求、账号适配、可迁移性和风险筛选 10 个候选选题，输出给使用者勾选：

- `要做`
- `可观察`
- `不要做`

它不负责生成完整口播稿，不负责录制、发布、转化或爆款保证。

## 必备条件

1. Node.js 可运行本 Skill 脚本。
2. 有 TikHub API Token。
3. 默认 TikHub API 地址为：`https://api.tikhub.io`
4. 获取 Token 的入口为：`https://user.tikhub.io/dashboard/api`

## 首次保存 Token

建议先运行首次检查：

`node scripts/first-run-check.mjs`

它会检查：

- Node.js 是否可运行；
- TikHub API 地址是否为默认地址；
- 本机是否能读到 Token；
- Skill 必需脚本是否完整。

如果没准备好，它会直接告诉你下一步该做什么。

在项目根目录运行：

`node scripts/setup-tikhub-token.mjs`

看到提示后，粘贴 TikHub API Token 并回车。

在支持的终端里，Token 输入会隐藏，不会在屏幕上回显。

Token 会保存到本机 macOS 钥匙串：

- service：`hotspot_radar_tikhub_api_token`
- account：当前电脑用户

兼容旧配置：

- service：`ai_anget_tikhub_api_token`
- account：`dalin`

## 检查 Token 是否可用

只检查 Token 时运行：

`node scripts/run-gate1-topic-validation.mjs --check-token`

如果返回：

`"ok": true`

说明可以真实抓取。

如果返回：

`"ok": false`

说明当前环境没有读到 Token，需要重新运行首次保存步骤。

## 同关键词历史去重

每次输出 10 个候选选题后，Skill 会把本次返回过的内容记录到：

`data/gate-1/owner-review-history.json`

下一次使用相同或近似主题时，会自动排除：

- 上一次已经返回过的内容 ID；
- 标题/选题高度相似的近重复内容。

如果同主题下新候选不足 10 条，Skill 应该提示候选池不足，而不是为了凑满 10 条把旧内容再拿出来。

只有在复现旧报告或调试时，才使用 `--no-history` 关闭去重。

## 临时使用方式

也可以在当前终端临时设置环境变量 `TIKHUB_API_KEY` 后运行。

这种方式只在当前终端会话有效。终端关闭、Codex 会话切换、系统重启或换用户后可能失效。

## 为什么会觉得 Token 经常掉

常见原因：

1. Token 只放在环境变量里，终端或任务会话结束后就没了。
2. Token 存在旧 service：`ai_anget_tikhub_api_token`，但新 Skill 查的是另一套 service。
3. 钥匙串 account 不一致，例如旧脚本固定查 `dalin`，当前系统用户不是 `dalin`。
4. 换了电脑、换了 macOS 用户、换了 Codex 运行环境。
5. TikHub 后台重置、撤销或轮换了 Token。
6. 供应商额度不足、权限变化或接口限制，看起来像 Token 失效。

本版本已改成：

- 优先读 `TIKHUB_API_KEY`；
- 再读 `hotspot_radar_tikhub_api_token / 当前用户`；
- 再兼容旧的 `ai_anget_tikhub_api_token / dalin`；
- 找不到时输出安装提示，不再直接抛钥匙串错误。

## 安全边界

- 不要把 Token 写进 Skill 包。
- 不要把 Token 写进 README、报告、Git、日志或截图。
- 分享 Skill 时只分享脚本和说明，不分享本机钥匙串内容。
- 如需切换 TikHub API 地址，必须明确确认目标域名，默认只使用 `https://api.tikhub.io`。

## 首次使用清单

1. 安装完整 `hotspot-radar-workflow` Skill 包。这个 GitHub 仓库根目录就是 Skill 根目录，必须能直接看到 `SKILL.md` 和 `scripts/`。
2. 运行 `node scripts/first-run-check.mjs`。
3. 如果提示缺少 Token，打开 `https://user.tikhub.io/dashboard/api` 复制 Token。
4. 运行 `node scripts/setup-tikhub-token.mjs` 保存 Token。
5. 再次运行首次检查，看到“总体状态：可真实抓取”。
6. 输入一个主题，让热点雷达生成候选选题：`node scripts/run-topic-checklist.mjs "AI 自动化真实项目"`。
7. 每次同主题再次运行时，默认不会重复返回上次已经给过的 10 条候选。

## 主题输入与自动扩词

使用者只需要输入一个大方向，不需要自己准备完整关键词表。

例如输入：

`AI 自动化真实项目`

系统会自动扩展为一组相关搜索词，例如：

- `AI 自动化真实项目`
- `AI 做项目`
- `一个人 AI 工作流`
- `AI 项目复盘`
- `AI 工作流 保姆级教程`
- `Codex 项目实战`
- `Codex 工作流`
- `Skill 工作流`

扩词后的关键词会保存到本次运行目录的 `keywords/keyword-nodes.json`，其中只有 `enabled` 状态的关键词会进入真实抓取。
