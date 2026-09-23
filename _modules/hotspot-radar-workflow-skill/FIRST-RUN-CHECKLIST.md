# 热点雷达 Skill 首次使用清单

这份清单给新安装用户使用。目标是先确认本机能安全读取 TikHub Token，再开始真实抓取。

## 1. 安装 Skill

确认本机已经安装完整 `hotspot-radar-workflow` Skill 包，并且包含：

- `SKILL.md`
- `README.md`
- `INSTALL.md`
- `scripts/first-run-check.mjs`
- `scripts/setup-tikhub-token.mjs`
- `scripts/run-topic-checklist.mjs`
- `scripts/run-gate1-topic-validation.mjs`
- `scripts/build-gate1a-owner-review.mjs`
- `scripts/tikhub-token.mjs`

注意：这个 GitHub 仓库根目录就是 Skill 根目录，不需要再进入额外的 `skills/` 子目录。

## 2. 运行首次检查

在项目根目录运行：

`node scripts/first-run-check.mjs`

如果显示“总体状态：可真实抓取”，可以进入主题抓取。

如果显示“尚未就绪”，按检查结果里的“下一步”处理。

## 3. 配置 TikHub Token

打开 TikHub 后台：

`https://user.tikhub.io/dashboard/api`

复制 API Token 后运行：

`node scripts/setup-tikhub-token.mjs`

看到提示后粘贴 Token 并回车。支持的终端会隐藏输入，不会把 Token 显示在屏幕上。

Token 会保存到本机 macOS 钥匙串，不会进入 Skill 包、项目文件、报告、日志或 Git。

## 4. 再次检查

运行：

`node scripts/first-run-check.mjs`

通过后再开始真实抓取。

## 5. 输入主题

最简单用法：

`node scripts/run-topic-checklist.mjs "AI 自动化真实项目"`

示例主题：

- `AI 自动化真实项目`
- `Codex Skill 工作流`
- `AI 内容生产线`

你只需要给一个大方向或关键词。系统会自动扩展成一组搜索词，再去抖音抓候选内容。

例如你输入：

`AI 自动化真实项目`

系统可能扩展为：

- `AI 自动化真实项目`
- `AI 做项目`
- `一个人 AI 工作流`
- `AI 项目复盘`
- `AI 工作流 保姆级教程`
- `Codex 项目实战`
- `Codex 工作流`
- `Skill 工作流`

热点雷达会输出 10 条候选选题，供你判断：

- `要做`
- `可观察`
- `不要做`

## 6. 同主题去重

同一个主题第二次运行时，系统会默认排除上一次已经返回过的候选内容和相似选题。

历史记录保存在：

`data/gate-1/owner-review-history.json`

如果新候选不足 10 条，系统会提示候选不足，不会用旧候选凑数。
