import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = process.cwd();
const historyPath = path.join(root, 'data/gate-1/owner-review-history.json');

function cleanText(input, max = 120) {
  return String(input || '').replace(/\s+/g, ' ').trim().slice(0, max);
}

export function normalizeThemeKey(theme) {
  return String(theme || '')
    .toLowerCase()
    .replace(/[\/｜|,，、]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function topicFingerprint(candidate) {
  return cleanText(candidate.description, 80)
    .toLowerCase()
    .replace(/[^\p{Letter}\p{Number}]+/gu, '-')
    .replace(/^-+|-+$/g, '');
}

function angleOf(candidate) {
  if (candidate.radar_angle) return candidate.radar_angle;
  const text = [
    candidate.description,
    ...(candidate.tags || []),
  ].join(' ').toLowerCase();

  if (text.includes('skill') || text.includes('skills') || text.includes('工作流')) return 'Skill工作流';
  if (text.includes('日报') || text.includes('运营系统') || text.includes('真实项目') || text.includes('项目实战') || text.includes('从0到1') || text.includes('从 0 到 1')) return '真实项目';
  if (text.includes('口播') || text.includes('自媒体') || text.includes('内容生产') || text.includes('创作者') || text.includes('做视频') || text.includes('视频全流程')) return '内容生产';
  if (text.includes('教程') || text.includes('新手') || text.includes('保姆级') || text.includes('入门')) return 'Codex教程';
  if (text.includes('复盘') || text.includes('经验') || text.includes('避坑')) return '经验复盘';
  return '综合候选';
}

function recommendation(score = {}) {
  const total = Number(score.total || 0);
  const dimensions = score.dimensions || {};
  const accountFit = Number(dimensions.account_fit || 0);
  const riskPenalty = Number(dimensions.risk_penalty || 0);
  const demand = Number(score.demand_count || 0);
  const comments = Number(score.comments_sample_count || 0);

  if (total >= 85 && accountFit >= 16 && riskPenalty < 10 && (demand >= 2 || comments >= 10)) return 'S';
  if (total >= 75 && accountFit >= 14 && riskPenalty < 12) return 'A';
  if (total >= 60 && accountFit >= 10 && riskPenalty < 18) return 'B';
  if (riskPenalty >= 18) return 'Noise';
  return 'C';
}

function evidenceLine(candidate) {
  return [
    `点赞 ${candidate.like_count || 0}`,
    `评论 ${candidate.comment_count || 0}`,
    `收藏 ${candidate.favorite_count || 0}`,
    `分享 ${candidate.share_count || 0}`,
  ].join(' / ');
}

function reasonLine(candidate) {
  const score = candidate.score || {};
  const dimensions = score.dimensions || {};
  const reasons = [];
  if (Number(dimensions.basic_metrics || 0) >= 20) reasons.push('互动强');
  if (Number(score.demand_count || 0) >= 2) reasons.push(`评论需求 ${score.demand_count}`);
  if (Number(dimensions.account_fit || 0) >= 16) reasons.push('账号适配高');
  if (Number(dimensions.transferability || 0) >= 10) reasons.push('可迁移');
  if (Number(dimensions.risk_penalty || 0) > 0) reasons.push(`风险扣分 ${dimensions.risk_penalty}`);
  return reasons.length ? reasons.join('，') : '数据或评论证据一般，需老板判断';
}

function riskLine(candidate) {
  const missing = candidate.score?.missing_data || [];
  const risk = [];
  if (missing.includes('play_count')) risk.push('缺播放量');
  if (missing.includes('completion_rate')) risk.push('缺完播率');
  if (missing.includes('full_transcript')) risk.push('缺完整字幕');
  if (Number(candidate.score?.comments_sample_count || 0) === 0) risk.push('缺评论样本');
  return risk.length ? risk.join('，') : '风险较低';
}

export function selectOwnerReviewCandidates(candidates, limit = 10, options = {}) {
  const seenCandidateIds = options.seenCandidateIds || new Set();
  const seenTopicFingerprints = options.seenTopicFingerprints || new Set();
  const sorted = [...candidates]
    .filter((candidate) => candidate && candidate.score && recommendation(candidate.score) !== 'Noise')
    .filter((candidate) => !seenCandidateIds.has(candidate.candidate_id || candidate.content_id))
    .filter((candidate) => !seenTopicFingerprints.has(topicFingerprint(candidate)))
    .sort((a, b) => Number(b.score?.total || 0) - Number(a.score?.total || 0));

  const selected = [];
  const usedAngles = new Set();

  for (const candidate of sorted) {
    const angle = angleOf(candidate);
    if (usedAngles.has(angle)) continue;
    selected.push({ ...candidate, radar_angle: angle });
    usedAngles.add(angle);
    if (selected.length >= limit) return selected;
  }

  for (const candidate of sorted) {
    if (selected.some((entry) => entry.candidate_id === candidate.candidate_id)) continue;
    selected.push({ ...candidate, radar_angle: angleOf(candidate) });
    if (selected.length >= limit) return selected;
  }

  return selected;
}

export function buildOwnerReviewMarkdown({ runId, theme, sourceRunId, candidates, history = null }) {
  const themeHistory = history?.themes?.[normalizeThemeKey(theme)] || {};
  const selected = selectOwnerReviewCandidates(candidates, 10, {
    seenCandidateIds: new Set(themeHistory.candidate_ids || []),
    seenTopicFingerprints: new Set(themeHistory.topic_fingerprints || []),
  });
  const now = new Date().toISOString().slice(0, 10);
  const rows = selected.map((candidate, index) => {
    const score = candidate.score || {};
    return [
      index + 1,
      recommendation(score),
      cleanText(candidate.description, 42),
      candidate.radar_angle || angleOf(candidate),
      evidenceLine(candidate),
      `总分 ${score.total ?? ''}；${reasonLine(candidate)}`,
      riskLine(candidate),
      '[ ] 要做  [ ] 可观察  [ ] 不要做',
    ].join(' | ');
  });

  return `# Gate 1A 老板勾选判断表

日期：${now}
阶段：Gate 1A 雷达验证
主题：${theme}
来源运行：${sourceRunId || runId}
历史去重：${history ? '已启用，同主题已返回候选默认排除' : '未启用'}

## 使用方式

老板只需要在每条后面勾选：

- [ ] 要做
- [ ] 可观察
- [ ] 不要做

本表只判断候选选题是否值得做，不生成文案、不进入录制、不做转化设计。

## 判断标准

- 数据表现：点赞、评论、收藏、分享。
- 用户需求：评论里是否有教程、怎么做、能不能、资料、案例等需求。
- 账号适配：是否贴合 AI、Codex、Skill、工作流、真实项目。
- 可迁移性：是否能换成老板自己的项目、经验或方法。
- 风险：缺播放量、缺完播率、缺完整字幕、版权或夸张承诺。

## 候选列表

| 编号 | 推荐 | 候选选题 | 角度 | 数据依据 | 推荐依据 | 风险/缺口 | 老板判断 |
|---:|---|---|---|---|---|---|---|
${rows.map((row) => `| ${row} |`).join('\n')}

${selected.length < 10 ? `\n> 注意：同主题历史去重后，本轮只剩 ${selected.length} 条新候选。建议重新抓取、扩展关键词或放宽主题。` : ''}

## 通过标准

- 10 条里有 3 到 5 条被标为“要做”，本轮有效。
- 连续两轮有效，热点雷达可以固化为稳定 Skill 工作流。
- 如果少于 3 条“要做”，回调关键词和评分权重。
`;
}

function readHistory() {
  if (!fs.existsSync(historyPath)) return { version: 1, themes: {} };
  return JSON.parse(fs.readFileSync(historyPath, 'utf8'));
}

function writeHistory(history) {
  fs.mkdirSync(path.dirname(historyPath), { recursive: true });
  fs.writeFileSync(historyPath, JSON.stringify(history, null, 2));
}

function recordHistory(history, { theme, runId, outputPath, selected }) {
  const key = normalizeThemeKey(theme);
  const entry = history.themes[key] || {
    candidate_ids: [],
    topic_fingerprints: [],
    runs: [],
  };
  const candidateIds = new Set(entry.candidate_ids);
  const fingerprints = new Set(entry.topic_fingerprints);
  for (const candidate of selected) {
    candidateIds.add(candidate.candidate_id || candidate.content_id);
    fingerprints.add(topicFingerprint(candidate));
  }
  entry.candidate_ids = Array.from(candidateIds).filter(Boolean);
  entry.topic_fingerprints = Array.from(fingerprints).filter(Boolean);
  entry.runs.push({
    run_id: runId,
    output_path: outputPath,
    generated_at: new Date().toISOString(),
    selected_count: selected.length,
  });
  history.themes[key] = entry;
  return history;
}

function loadScores(runId) {
  const scoresPath = path.join(root, 'data/gate-1/runs', runId, 'scores/opportunity-scores.json');
  const json = JSON.parse(fs.readFileSync(scoresPath, 'utf8'));
  return {
    theme: json.theme || '',
    candidates: json.selected || json.all_scores || [],
  };
}

function main() {
  const args = process.argv.slice(2);
  const runId = args[0];
  if (!runId) {
    throw new Error('Usage: node scripts/build-gate1a-owner-review.mjs <source-run-id> [output-report-path]');
  }
  const outputPath = args[1] || path.join(root, 'reports/gate-1', `${runId}-owner-review-checklist.md`);
  const { theme, candidates } = loadScores(runId);
  const noHistory = args.includes('--no-history');
  const history = noHistory ? null : readHistory();
  const themeHistory = history?.themes?.[normalizeThemeKey(theme)] || {};
  const selected = selectOwnerReviewCandidates(candidates, 10, {
    seenCandidateIds: new Set(themeHistory.candidate_ids || []),
    seenTopicFingerprints: new Set(themeHistory.topic_fingerprints || []),
  });
  const markdown = buildOwnerReviewMarkdown({
    runId,
    sourceRunId: runId,
    theme,
    candidates,
    history,
  });
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, markdown);
  if (history) {
    recordHistory(history, { theme, runId, outputPath, selected });
    writeHistory(history);
  }
  console.log(JSON.stringify({
    output: outputPath,
    candidates: selected.length,
    history_enabled: Boolean(history),
    history_path: history ? historyPath : null,
  }, null, 2));
}

const isCli = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isCli) main();
