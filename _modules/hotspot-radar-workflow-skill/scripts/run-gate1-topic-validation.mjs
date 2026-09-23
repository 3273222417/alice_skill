import fs from 'node:fs';
import path from 'node:path';

import {
  buildMissingTikHubTokenMessage,
  findTikHubToken,
} from './tikhub-token.mjs';

const root = process.cwd();
const args = process.argv.slice(2);
const keywordOnly = args.includes('--keyword-only');
const checkTokenOnly = args.includes('--check-token');
const positionalArgs = args.filter((arg) => !arg.startsWith('--'));
const runId = positionalArgs[0] || `gate1-topic-ai-automation-real-project-${new Date().toISOString().slice(0, 10)}`;
const theme = positionalArgs.slice(1).join(' ') || 'AI 自动化真实项目';
const baseDir = path.join(root, 'data/gate-1/runs', runId);
const rawSearchDir = path.join(baseDir, 'raw/search');
const rawCommentsDir = path.join(baseDir, 'raw/comments');
const normalizedDir = path.join(baseDir, 'normalized');
const scoresDir = path.join(baseDir, 'scores');
const briefsDir = path.join(baseDir, 'briefs');
const analysesDir = path.join(baseDir, 'analyses');
const keywordsDir = path.join(baseDir, 'keywords');
const reportsDir = path.join(root, 'reports/gate-1');
const reportPath = path.join(reportsDir, `${runId}-candidate-selection-report.md`);
const briefsReportPath = path.join(reportsDir, `${runId}-creation-briefs-and-recording-packages.md`);
const runLogPath = path.join(baseDir, 'logs/run-log.json');

const requestBudget = 25;
const runLog = {
  run_id: runId,
  theme,
  started_at: new Date().toISOString(),
  scope: 'gate1_new_topic_validation_candidate_selection',
  base_url: process.env.TIKHUB_BASE_URL || 'https://api.tikhub.io',
  request_budget: requestBudget,
  ai_analysis_enabled: process.env.HOTSPOT_AI_ANALYSIS === '1' || args.includes('--ai-analysis'),
  requests: [],
  ai_requests: [],
};

const tokenResult = findTikHubToken();
if (checkTokenOnly) {
  console.log(JSON.stringify({
    ok: Boolean(tokenResult.token),
    source: tokenResult.source || null,
    base_url: process.env.TIKHUB_BASE_URL || 'https://api.tikhub.io',
    setup_hint: tokenResult.token ? null : 'node scripts/setup-tikhub-token.mjs',
  }, null, 2));
  process.exit(tokenResult.token ? 0 : 1);
}

for (const dir of [rawSearchDir, rawCommentsDir, normalizedDir, scoresDir, briefsDir, analysesDir, keywordsDir, path.dirname(runLogPath), reportsDir]) {
  fs.mkdirSync(dir, { recursive: true });
}

function unique(items) {
  const seen = new Set();
  const result = [];
  for (const item of items) {
    const normalized = String(item.keyword || item).trim().replace(/\s+/g, ' ');
    if (!normalized || seen.has(normalized.toLowerCase())) continue;
    seen.add(normalized.toLowerCase());
    if (typeof item === 'string') result.push(normalized);
    else result.push({ ...item, keyword: normalized });
  }
  return result;
}

function keywordNode(keyword, type, reason, status = 'candidate') {
  return {
    keyword,
    type,
    status,
    reason,
    source: 'rule_based_theme_expansion_v0.2',
  };
}

function expandKeywords(inputTheme) {
  const t = String(inputTheme || '').trim();
  const lower = t.toLowerCase();
  const nodes = [
    keywordNode(t, 'core', '老板输入主题', 'enabled'),
  ];

  const aiTrack = lower.includes('ai') || t.includes('人工智能') || lower.includes('codex') || lower.includes('skill');
  const codexTrack = lower.includes('codex') || t.includes('编程') || t.includes('项目');
  const skillTrack = lower.includes('skill') || t.includes('工作流') || t.includes('技能');
  const contentTrack = t.includes('内容') || t.includes('口播') || t.includes('自媒体') || t.includes('短视频') || t.includes('生产线');

  if (aiTrack) {
    nodes.push(
      keywordNode('AI 自动化真实项目', 'core', 'AI 真实落地方向'),
      keywordNode('AI 做项目', 'core', '从工具使用扩展到项目落地'),
      keywordNode('一个人 AI 工作流', 'audience', '匹配个人创作者和小团队场景'),
      keywordNode('AI 项目复盘', 'scenario', '寻找项目经验和踩坑内容'),
      keywordNode('AI 工作流 保姆级教程', 'pain', '捕捉小白教程和评论需求'),
    );
  }
  if (codexTrack) {
    nodes.push(
      keywordNode('Codex 项目实战', 'tool', 'Codex 与真实项目强相关'),
      keywordNode('Codex 真实案例', 'scenario', '寻找可借鉴案例'),
      keywordNode('Codex 工作流', 'tool', '连接工具和流程'),
      keywordNode('Codex 教程', 'pain', '捕捉新手安装与使用需求'),
      keywordNode('Codex 做运营系统', 'scenario', '贴合已验证运营日报方向'),
    );
  }
  if (skillTrack) {
    nodes.push(
      keywordNode('Skill 工作流', 'tool', 'Skill 是当前核心概念'),
      keywordNode('AI Skill 教程', 'pain', '寻找教程型需求'),
      keywordNode('Codex Skill', 'tool', '匹配 Codex 与 Skill 组合'),
      keywordNode('工作流 自动化', 'scenario', '扩展到可执行流程'),
    );
  }
  if (contentTrack) {
    nodes.push(
      keywordNode('AI 内容生产线', 'scenario', '匹配短视频内容生产链路'),
      keywordNode('AI 自媒体运营流程', 'scenario', '寻找内容运营候选'),
      keywordNode('AI 口播 工作流', 'scenario', '匹配口播生产链路'),
      keywordNode('AI 视频 内容生产', 'scenario', '补充视频内容方向'),
    );
  }

  nodes.push(
    keywordNode(`${t} 教程`, 'pain', '寻找学习和上手需求'),
    keywordNode(`${t} 新手`, 'audience', '寻找新手和入门需求'),
    keywordNode(`${t} 案例`, 'scenario', '寻找可拆解案例'),
    keywordNode(`${t} 经验`, 'scenario', '寻找经验分享内容'),
    keywordNode(`${t} 避坑`, 'pain', '寻找评论需求和反差点'),
  );

  const cleaned = unique(nodes).sort((a, b) => keywordPriority(a.keyword) - keywordPriority(b.keyword));
  function keywordPriority(keyword) {
    const text = keyword.toLowerCase();
    if (keyword === t) return 0;
    if (codexTrack && text.includes('codex')) return 1;
    if (skillTrack && (text.includes('skill') || keyword.includes('工作流'))) return 2;
    if (contentTrack && (keyword.includes('内容') || keyword.includes('自媒体') || keyword.includes('口播') || keyword.includes('视频'))) return 3;
    if (aiTrack && (text.includes('ai') || keyword.includes('人工智能'))) return 4;
    if (keyword.includes('教程') || keyword.includes('新手') || keyword.includes('避坑')) return 5;
    return 6;
  }
  const forbidden = ['月入', '暴富', '稳赚', '副业暴利', '一键变现'];
  const safeNodes = cleaned.map((node) => ({
    ...node,
    status: forbidden.some((term) => node.keyword.includes(term)) ? 'paused' : node.status,
  }));
  let enabledCount = 0;
  const limited = safeNodes.map((node) => {
    if (node.status === 'paused') return node;
    if (enabledCount < 8) {
      enabledCount += 1;
      return { ...node, status: 'enabled' };
    }
    return { ...node, status: 'candidate' };
  });
  return limited;
}

const keywordNodes = expandKeywords(theme);
const keywords = keywordNodes.filter((node) => node.status === 'enabled').map((node) => node.keyword);
fs.writeFileSync(path.join(keywordsDir, 'keyword-nodes.json'), JSON.stringify({
  generated_at: new Date().toISOString(),
  run_id: runId,
  theme,
  enabled_count: keywords.length,
  candidate_count: keywordNodes.filter((node) => node.status === 'candidate').length,
  keyword_nodes: keywordNodes,
}, null, 2));

if (keywordOnly) {
  console.log(JSON.stringify({
    run_id: runId,
    theme,
    keyword_only: true,
    enabled_keywords: keywords,
    keyword_nodes: `data/gate-1/runs/${runId}/keywords/keyword-nodes.json`,
  }, null, 2));
  process.exit(0);
}

if (!tokenResult.token) {
  console.error(buildMissingTikHubTokenMessage());
  process.exit(2);
}
const token = tokenResult.token;
const baseUrl = process.env.TIKHUB_BASE_URL || 'https://api.tikhub.io';

function slug(input) {
  return input.toLowerCase().replace(/\s+/g, '-').replace(/[^\p{Letter}\p{Number}-]+/gu, '').replace(/-+/g, '-');
}

async function apiPost(router, body) {
  const url = `${baseUrl}${router}`;
  const started = Date.now();
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    const text = await response.text();
    let json = null;
    try {
      json = JSON.parse(text);
    } catch (error) {
      json = { parse_error: String(error), text: text.slice(0, 1000) };
    }
    return { statusCode: response.status, ms: Date.now() - started, bytes: Buffer.byteLength(text), json };
  } catch (error) {
    return { statusCode: 0, ms: Date.now() - started, bytes: 0, json: { network_error: String(error), router } };
  }
}

async function apiGet(router, params) {
  const url = new URL(`${baseUrl}${router}`);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value);
  const started = Date.now();
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    const text = await response.text();
    let json = null;
    try {
      json = JSON.parse(text);
    } catch (error) {
      json = { parse_error: String(error), text: text.slice(0, 1000) };
    }
    return { statusCode: response.status, ms: Date.now() - started, bytes: Buffer.byteLength(text), json };
  } catch (error) {
    return { statusCode: 0, ms: Date.now() - started, bytes: 0, json: { network_error: String(error), router } };
  }
}

function searchItems(raw) {
  const list = raw?.data?.business_data || [];
  return list
    .map((entry) => entry?.data?.aweme_info || entry?.aweme_info || entry?.data)
    .filter((item) => item?.aweme_id || item?.group_id);
}

function classifyRequest(result, parsedCount = 0, expectedShape = 'generic') {
  const json = result?.json || {};
  if (result.statusCode === 0 || json.network_error) {
    return { ok: false, category: 'network_error', summary: cleanText(json.network_error || 'network request failed', 180) };
  }
  if (result.statusCode >= 400) {
    return { ok: false, category: 'http_error', summary: `HTTP ${result.statusCode}` };
  }
  if (json.parse_error) {
    return { ok: false, category: 'parse_error', summary: cleanText(json.parse_error, 180) };
  }
  if (typeof json.code !== 'undefined' && ![0, 200].includes(Number(json.code))) {
    return { ok: false, category: 'api_error', summary: cleanText(json.message || json.msg || `API code ${json.code}`, 180) };
  }
  if (expectedShape === 'search' && !Array.isArray(json?.data?.business_data)) {
    return { ok: false, category: 'field_shape_changed', summary: 'missing data.business_data array' };
  }
  if (expectedShape === 'comments' && !Array.isArray(json?.data?.comments)) {
    return { ok: false, category: 'field_shape_changed', summary: 'missing data.comments array' };
  }
  if (parsedCount === 0) {
    return { ok: false, category: 'empty_result', summary: 'request succeeded but parsed zero usable items' };
  }
  return { ok: true, category: 'ok', summary: 'ok' };
}

function summarizeFailures(requests) {
  const failures = requests.filter((request) => !request.ok);
  const byCategory = failures.reduce((acc, request) => {
    acc[request.error_category] = (acc[request.error_category] || 0) + 1;
    return acc;
  }, {});
  return {
    failure_count: failures.length,
    by_category: byCategory,
    failures: failures.map((request) => ({
      type: request.type,
      keyword: request.keyword,
      content_id: request.content_id,
      statusCode: request.statusCode,
      apiCode: request.apiCode,
      error_category: request.error_category,
      error_summary: request.error_summary,
      file: request.file,
    })),
  };
}

function normalizeAweme(item, sourceKeyword, rawPath) {
  const stats = item.statistics || {};
  const author = item.author || {};
  const awemeId = String(item.aweme_id || item.group_id || '');
  const tags = Array.isArray(item.text_extra)
    ? item.text_extra.filter((tag) => tag?.hashtag_name).map((tag) => tag.hashtag_name)
    : [];
  return {
    candidate_id: `douyin-${awemeId}`,
    platform: 'douyin',
    source_keyword: sourceKeyword,
    source_interface: 'fetch_general_search_v2',
    content_id: awemeId,
    content_url: `https://www.douyin.com/video/${awemeId}`,
    description: item.desc || '',
    author_id: String(author.uid || author.sec_uid || ''),
    author_name: author.nickname || '',
    published_at: item.create_time || null,
    duration: item.duration || item.video?.duration || null,
    like_count: Number(stats.digg_count ?? item.digg_count ?? 0),
    comment_count: Number(stats.comment_count ?? item.comment_count ?? 0),
    favorite_count: Number(stats.collect_count ?? item.collect_count ?? 0),
    share_count: Number(stats.share_count ?? item.share_count ?? 0),
    play_count: Number(stats.play_count ?? 0),
    author_follower_count: Number(author.follower_count ?? 0),
    tags,
    cover_url: item.video?.cover?.url_list?.[0] || item.video?.origin_cover?.url_list?.[0] || '',
    raw_json_path: rawPath,
    metrics_availability: {
      play_count: Number(stats.play_count ?? 0) > 0 ? 'available' : 'returned_zero_or_missing',
      author_follower_count: Number(author.follower_count ?? 0) > 0 ? 'available' : 'returned_zero_or_missing',
      like_count: 'available',
      comment_count: 'available',
      favorite_count: 'available',
      share_count: 'available',
    },
    evidence_level: 'metadata',
    source_keywords: [sourceKeyword],
  };
}

function mergeCandidates(items) {
  const byId = new Map();
  for (const item of items) {
    const existing = byId.get(item.content_id);
    if (!existing) {
      byId.set(item.content_id, item);
      continue;
    }
    existing.source_keywords = Array.from(new Set([...(existing.source_keywords || []), ...(item.source_keywords || [])]));
    existing.source_keyword = existing.source_keywords.join(', ');
  }
  return Array.from(byId.values());
}

function textOf(candidate) {
  return [
    candidate.description,
    candidate.source_keyword,
    ...(candidate.source_keywords || []),
    ...(candidate.tags || []),
  ].join(' ').toLowerCase();
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function logScore(value) {
  return Math.log10(Math.max(0, Number(value) || 0) + 1);
}

function termScore(text, terms, max) {
  const sum = terms.reduce((acc, [term, weight]) => acc + (text.includes(term) ? weight : 0), 0);
  return clamp(sum, 0, max);
}

function demandFromComments(comments) {
  const demandTerms = ['怎么', '如何', '教程', '求', '想学', '不会', '能不能', '可以吗', '哪里', '配置', '安装', '报错', '链接', '模板', '资料', '实战', '案例'];
  return comments.filter((comment) => demandTerms.some((term) => comment.text?.includes(term))).length;
}

function scoreCandidate(candidate, comments = []) {
  const text = textOf(candidate);
  const positiveTerms = [
    ['codex', 10], ['skill', 10], ['工作流', 10], ['项目', 9], ['实战', 8],
    ['教程', 6], ['ai编程', 8], ['ai 编程', 8], ['自动化', 7], ['内容生产', 8],
    ['真实案例', 8], ['复盘', 7], ['搭建', 5], ['实测', 5], ['网站', 5],
    ['知识库', 4], ['mcp', 4], ['视觉', 4], ['截图', 4], ['页面', 4],
  ];
  const negativeTerms = [
    ['商机', 10], ['变现', 9], ['赚钱', 8], ['暴富', 10], ['副业', 7],
    ['替代', 8], ['取代', 8], ['影视', 7], ['剪辑', 5], ['广告大片', 7],
    ['焦虑', 6], ['风口', 5], ['复刻', 10], ['搬运', 10],
  ];
  const interactionRaw =
    logScore(candidate.like_count) * 0.25 +
    logScore(candidate.comment_count) * 0.2 +
    logScore(candidate.favorite_count) * 0.35 +
    logScore(candidate.share_count) * 0.2;
  const basicMetrics = clamp(Math.round((interactionRaw / 5.5) * 25), 0, 25);
  const trackRelevance = termScore(text, positiveTerms, 20);
  const riskPenalty = termScore(text, negativeTerms, 30);
  const accountFit = clamp(trackRelevance + (text.includes('项目') || text.includes('工作流') || text.includes('skill') || text.includes('codex') ? 8 : 0) - (riskPenalty ? 8 : 0), 0, 20);
  const transferability = termScore(text, [
    ['流程', 6], ['工作流', 8], ['教程', 5], ['项目', 7], ['实战', 6],
    ['搭建', 4], ['实测', 4], ['skill', 5], ['codex', 5], ['内容生产', 5],
  ], 15);
  const structureClarity = termScore(text, [
    ['教程', 3], ['保姆级', 2], ['手把手', 2], ['步骤', 2],
    ['怎么', 2], ['实测', 2], ['复盘', 2], ['全流程', 3],
  ], 8);
  const demandCount = demandFromComments(comments);
  const userDemand = clamp(Math.round(Math.min(demandCount, 8) / 8 * 15), 0, 15);
  const freshness = 4;
  const evidenceCompleteness = comments.length ? 3 : 1;
  const total = clamp(basicMetrics + userDemand + trackRelevance + accountFit + transferability + structureClarity + freshness + evidenceCompleteness - riskPenalty, 0, 100);
  let tier = 'C 观察池';
  let recommendedAction = '观察，不进入文案';
  if (total >= 75 && accountFit >= 14 && riskPenalty < 12) {
    tier = 'A 自动优先候选';
    recommendedAction = '进入候选选题与原创简报';
  } else if (total >= 60 && accountFit >= 10 && riskPenalty < 18) {
    tier = 'B 可研究候选';
    recommendedAction = '补证据或老板最终确认';
  } else if (riskPenalty >= 18) {
    tier = 'D 风险/噪音候选';
    recommendedAction = '降权或淘汰';
  }
  return {
    total,
    tier,
    dimensions: {
      basic_metrics: basicMetrics,
      user_demand: userDemand,
      track_relevance: trackRelevance,
      account_fit: accountFit,
      transferability,
      structure_clarity: structureClarity,
      freshness,
      evidence_completeness: evidenceCompleteness,
      risk_penalty: riskPenalty,
    },
    demand_count: demandCount,
    comments_sample_count: comments.length,
    recommended_action: recommendedAction,
    missing_data: ['play_count', 'completion_rate', 'author_follower_count', 'full_transcript', 'ocr'],
  };
}

function parseComments(raw) {
  return (raw?.data?.comments || [])
    .map((comment) => ({
      cid: comment.cid,
      text: comment.text || '',
      digg_count: comment.digg_count || 0,
      create_time: comment.create_time || null,
    }))
    .filter((comment) => comment.text);
}

function cleanText(input, max = 120) {
  return String(input || '').replace(/\s+/g, ' ').trim().slice(0, max);
}

function metricsLine(candidate) {
  return `点赞 ${candidate.like_count}，评论 ${candidate.comment_count}，收藏 ${candidate.favorite_count}，分享 ${candidate.share_count}`;
}

function includesAny(text, terms) {
  return terms.some((term) => text.includes(term));
}

function isPoorAccountFit(candidate) {
  const text = textOf(candidate);
  return includesAny(text, ['服装厂', '制衣厂', '机器人', '军事', '战场', '月入', '收入翻倍', '暴富', '副业', '变现']);
}

function recordingEvidence(candidate) {
  const score = candidate.score || {};
  const comments = score.comments_sample_count || 0;
  const demand = score.demand_count || 0;
  const strongInteraction =
    candidate.like_count >= 1000 ||
    candidate.favorite_count >= 1000 ||
    candidate.share_count >= 200 ||
    candidate.comment_count >= 100;
  const veryStrongInteraction =
    candidate.like_count >= 10000 ||
    candidate.favorite_count >= 10000 ||
    candidate.share_count >= 1000 ||
    candidate.comment_count >= 500;
  const hasCommentEvidence = comments >= 5;
  const hasDemandEvidence = demand >= 2;
  const confidenceEstimate = hasCommentEvidence ? 0.62 : 0.46;
  const eligible =
    !isPoorAccountFit(candidate) &&
    score.total >= 75 &&
    strongInteraction &&
    (hasDemandEvidence || veryStrongInteraction) &&
    confidenceEstimate >= 0.55;
  const reason = [];
  if (!strongInteraction) reason.push('互动未达录制样本门槛');
  if (!hasCommentEvidence) reason.push('缺少评论证据');
  if (!hasDemandEvidence && !veryStrongInteraction) reason.push('需求评论不足且互动未达到强爆发');
  if (confidenceEstimate < 0.55) reason.push('结构化分析置信度预估低');
  if (isPoorAccountFit(candidate)) reason.push('账号适配风险');
  if ((score.total || 0) < 75) reason.push('机会分低于 A 层门槛');
  return {
    eligible,
    confidence_estimate: confidenceEstimate,
    comments,
    demand,
    strong_interaction: strongInteraction,
    very_strong_interaction: veryStrongInteraction,
    reason: reason.length ? reason : ['满足录制样本证据门槛'],
  };
}

function recordingPriority(candidate) {
  const score = candidate.score || {};
  const evidence = recordingEvidence(candidate);
  return (
    (score.total || 0) * 2 +
    Math.min(evidence.demand, 10) * 8 +
    Math.min(evidence.comments, 20) * 2 +
    logScore(candidate.like_count) * 5 +
    logScore(candidate.favorite_count) * 6 +
    logScore(candidate.share_count) * 5 +
    logScore(candidate.comment_count) * 4 +
    (evidence.very_strong_interaction ? 20 : 0)
  );
}

function recordingAngleKey(candidate) {
  const text = textOf(candidate);
  if (includesAny(text, ['视频', '口播', '自媒体', '内容生产', '创作者', '创作'])) return 'content_workflow';
  if (includesAny(text, ['skill', 'skills'])) return 'skill_workflow';
  if (includesAny(text, ['日报', '运营系统', '真实项目', '从0到1', '从 0 到 1'])) return 'real_project';
  if (includesAny(text, ['codex', 'ai编程', 'vibecoding'])) return 'codex_usage';
  return 'general_workflow';
}

function chooseRecordingCandidates(selectedItems) {
  const preferred = selectedItems
    .filter((item) => !isPoorAccountFit(item))
    .filter((item) => includesAny(textOf(item), ['codex', 'skill', '工作流', '内容生产', '自媒体', '运营', '项目', '实战']))
    .map((item) => ({
      ...item,
      recording_evidence: recordingEvidence(item),
      recording_priority: recordingPriority(item),
    }))
    .filter((item) => item.recording_evidence.eligible)
    .sort((a, b) => b.recording_priority - a.recording_priority);
  const buckets = [
    (item) => includesAny(textOf(item), ['skill', '工作流']),
    (item) => includesAny(textOf(item), ['codex', 'ai编程', 'vibecoding']),
    (item) => includesAny(textOf(item), ['自媒体', '内容生产线', '口播', '视频', '创作者', '创作']),
    (item) => includesAny(textOf(item), ['日报', '运营系统', '真实项目', '从0到1', '从 0 到 1']),
  ];
  const chosen = [];
  const used = new Set();
  const usedAngles = new Set();
  for (const matches of buckets) {
    const item = preferred.find((candidate) => {
      const angleKey = recordingAngleKey(candidate);
      return !used.has(candidate.content_id) && !usedAngles.has(angleKey) && matches(candidate);
    });
    if (!item) continue;
    chosen.push(item);
    used.add(item.content_id);
    usedAngles.add(recordingAngleKey(item));
    if (chosen.length >= 3) return chosen;
  }
  for (const item of preferred) {
    if (used.has(item.content_id)) continue;
    const angleKey = recordingAngleKey(item);
    if (usedAngles.has(angleKey) && preferred.some((candidate) => !used.has(candidate.content_id) && !usedAngles.has(recordingAngleKey(candidate)))) continue;
    chosen.push(item);
    used.add(item.content_id);
    usedAngles.add(angleKey);
    if (chosen.length >= 3) break;
  }
  return chosen;
}

function inferAngle(candidate, index) {
  const text = textOf(candidate);
  if (text.includes('日报') || text.includes('运营')) {
    return {
      title: '我用 Codex 做项目，第一步不是写代码',
      cover: '先验证，再开发',
      route: '热点与真实项目嫁接',
      pain: '很多人一上来就让 Codex 写代码，结果做出的是演示，不是能跑的流程。',
      view: '复杂项目第一步不是写代码，而是先把目标、边界、验收标准和停止条件讲清楚。',
      ownerCase: '热点雷达本身：先 Gate 0 验证数据，再 Gate 1 跑 Skill 工作流，最后才考虑 Web 和软件。',
      borrow: ['从 0 到 1 做真实系统的结构', '用具体业务场景承接 AI 能力', '把自动读取、分析、生成报告这类链路讲清楚'],
      avoid: ['不复制原项目设计', '不展示内部真实数据', '不承诺一条视频教完整系统开发', '不把项目讲成已经商业化交付'],
    };
  }
  if (text.includes('自媒体') || text.includes('内容生产线') || text.includes('口播')) {
    return {
      title: '做短视频最该交给 AI 的，不是拍摄',
      cover: '别让重复流程拖住你',
      route: '同痛点，换自有流程',
      pain: '做内容最消耗人的，常常不是拍摄，而是选题、拆解、标题、复盘这些反复出现的流程。',
      view: 'AI 做内容最有价值的地方，不是一键生成，而是把重复流程变成可执行、可复盘的 Skill。',
      ownerCase: '热点雷达加短视频运营 Skill：先找候选，再看数据和评论，再生成原创方向和录制包。',
      borrow: ['把内容运营流程拆成多个步骤', '强调重复流程的真实痛点', '把 Codex/Skill 接到创作者日常工作'],
      avoid: ['不复制原作者自媒体流程', '不展示对方视频画面或文案', '不承诺自动发布或代运营', '不说 Codex 可以解决全部运营问题'],
    };
  }
  if (text.includes('工作流') || text.includes('全流程') || text.includes('流程')) {
    return {
      title: '普通人用 AI，真正该学的是工作流',
      cover: '别只收藏教程',
      route: '同痛点，换自有流程',
      pain: '很多人收藏了很多 AI 教程，但真正做事时还是不知道第一步该怎么开始。',
      view: 'AI 工作流的价值，不是把步骤堆满，而是把输入、输出、检查点和人工判断门讲清楚。',
      ownerCase: '热点雷达工作流：主题、扩词、抓取、评分、简报、人工确认，再进入口播生产。',
      borrow: ['用保姆级教程承接小白需求', '把复杂 AI 使用变成流程', '强调普通人可理解、可执行的步骤'],
      avoid: ['不复刻原教程步骤', '不展示原作者素材', '不承诺学完立刻提升效率', '不把流程包装成万能答案'],
    };
  }
  if (text.includes('skill')) {
    return {
      title: '装了很多 Skill，为什么还是用不起来？',
      cover: 'Skill 不是清单',
      route: '同结构，换自有案例',
      pain: '很多人以为装了 Skill 就能变强，但真正卡住的是自己的流程没有定义清楚。',
      view: 'Skill 的价值不是多，而是能不能承接一个反复发生、标准明确、可以检查的任务。',
      ownerCase: '热点雷达工作流：主题、扩词、抓取、评分、简报、人工确认，每一步都有边界。',
      borrow: ['工具加 Skill 的传播点', '从工具转向流程的认知差', '用真实工作流解释 Skill 的价值'],
      avoid: ['不推荐未经验证的插件清单', '不做工具测评', '不展示内部报告', '不承诺装完马上提升效率'],
    };
  }
  if (text.includes('codex')) {
    return {
      title: index === 0 ? 'Codex 新手真正该学的，不是按钮' : '别把 Codex 当成自动写代码机器',
      cover: index === 0 ? '别只学按钮' : '先讲清楚任务',
      route: '同痛点，换观点',
      pain: '很多新手先找安装教程和按钮教程，但真正不会的是怎么把真实任务交给 Codex。',
      view: 'Codex 真正有用的地方，不是替你按按钮，而是帮你把模糊想法推进成能检查、能修改、能落地的结果。',
      ownerCase: '老板用 Codex 做项目时，会先定义目标、边界、验收标准和人工检查点。',
      borrow: ['零基础、上手、速通的入口', '评论区安装、账号、使用场景需求', '把 Codex 和真实项目连接起来'],
      avoid: ['不复刻原教程步骤', '不展示原作者画面', '不承诺解决账号或外部环境问题', '不做完整安装售后'],
    };
  }
  return {
    title: `这个 ${theme} 选题，真正值得讲的是流程`,
    cover: '别只看热度',
    route: '同痛点，换观点',
    pain: '高互动内容不一定适合直接跟拍，关键是能不能转成自己的真实案例。',
    view: '我们借鉴的是问题、结构和需求，不复制表达、画面和案例。',
    ownerCase: '老板自己的 AI 项目、Codex 工作流和内容生产流程。',
    borrow: ['选题背后的用户问题', '可迁移的信息结构', '评论区暴露的真实需求'],
    avoid: ['不复制原表达', '不使用原素材', '不夸大效果', '不承诺爆款'],
  };
}

function buildVoiceoverScript(angle) {
  return [
    angle.pain,
    '',
    '这件事我最近体感很强。',
    '',
    angle.view,
    '',
    '比如我们现在做一个真实项目，第一步不是追求看起来很厉害。',
    '',
    '而是先把问题讲清楚。',
    '',
    '这个东西给谁用？',
    '',
    '它到底解决什么问题？',
    '',
    '哪些地方不能乱改？',
    '',
    '最后怎么判断它是真的有用？',
    '',
    `我现在会把这套判断放进流程里：${angle.ownerCase}`,
    '',
    '这样 AI 做出来的东西，才不是演示。',
    '',
    '它有来源，有边界，有检查点，也能继续复盘。',
    '',
    '所以我不太建议一上来就追求一键生成。',
    '',
    '先把一个小但真实的问题跑通。',
    '',
    '再把稳定步骤封装成 Skill。',
    '',
    '这才是 AI 真正能落地的地方。',
  ].join('\n');
}

function heuristicStructuredAnalysis(candidate, index, reason = 'heuristic_fallback') {
  const angle = inferAngle(candidate, index);
  const comments = Array.isArray(candidate.comment_samples) ? candidate.comment_samples : [];
  const demandComments = comments
    .filter((comment) => ['怎么', '教程', '求', '想学', '不会', '配置', '安装', '报错', '案例'].some((term) => comment.text?.includes(term)))
    .slice(0, 5)
    .map((comment) => cleanText(comment.text, 80));
  return {
    analysis_id: `${runId}-analysis-${index + 1}`,
    source_candidate_id: candidate.candidate_id,
    source_content_id: candidate.content_id,
    provider: reason,
    model: null,
    confidence: comments.length ? 0.62 : 0.46,
    confidence_reason: comments.length
      ? '有标题、互动数据和评论样本，但缺少完整字幕、画面 OCR、完播率和粉丝量级。'
      : '只有标题和互动指标，缺少评论、字幕、画面 OCR、完播率和粉丝量级。',
    user_problem: angle.pain,
    retention_reason: '用具体痛点或反常识判断建立停留理由，避免只讲工具名和功能点。',
    borrowable_structure: angle.borrow,
    do_not_copy: angle.avoid,
    original_angle: angle.view,
    owner_owned_case: angle.ownerCase,
    three_routes: [
      {
        route: '同痛点，换观点',
        direction: angle.view,
        why_fit: '借的是用户问题，不借原作者表达。',
      },
      {
        route: '同结构，换自有案例',
        direction: angle.ownerCase,
        why_fit: '用老板自己的项目过程替换来源内容里的案例。',
      },
      {
        route: '热点与真实项目嫁接',
        direction: '从一个高互动话题切到热点雷达、Codex 或 Skill 的真实流程。',
        why_fit: '更符合账号“AI 真实落地”的定位。',
      },
    ],
    title_options: [
      angle.title,
      angle.title.replace('Codex', 'AI 工具'),
      '别再把 AI 当成一个按钮工具',
    ],
    cover_copy_options: [
      angle.cover,
      '先验证，再放大',
      '流程比工具重要',
    ],
    evidence_used: {
      description: cleanText(candidate.description, 180),
      metrics: metricsLine(candidate),
      comments: demandComments,
    },
    evidence_limitations: candidate.score?.missing_data || ['play_count', 'completion_rate', 'author_follower_count', 'full_transcript', 'ocr'],
    risk_notes: [
      '不能称为爆款预测，只能称为内容机会候选。',
      '不能逐句改写来源内容。',
      '不能展示热点雷达内部报告、原作者素材、评论身份或 API 原始数据。',
    ],
  };
}

function extractJsonObject(text) {
  const input = String(text || '').trim();
  if (!input) return null;
  try {
    return JSON.parse(input);
  } catch {
    const match = input.match(/\{[\s\S]*\}/);
    if (!match) return null;
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
  }
}

function normalizeStringArray(value, fallback = []) {
  if (!Array.isArray(value)) return fallback;
  return value.map((item) => cleanText(item, 120)).filter(Boolean).slice(0, 8);
}

async function aiStructuredAnalysis(candidate, index) {
  const fallback = heuristicStructuredAnalysis(candidate, index);
  const enabled = runLog.ai_analysis_enabled;
  const apiKey = process.env.OPENAI_API_KEY;
  if (!enabled || !apiKey) {
    return {
      ...fallback,
      provider: enabled ? 'heuristic_fallback_openai_key_missing' : 'heuristic_fallback_ai_disabled',
    };
  }

  const model = process.env.OPENAI_MODEL || 'gpt-4o-mini';
  const payload = {
    model,
    temperature: 0.3,
    messages: [
      {
        role: 'system',
        content: [
          '你是短视频选题拆解助手，只输出 JSON。',
          '你不能逐句改写原文，不能承诺爆款，不能建议展示内部报告或原作者素材。',
          '你只能基于给定标题、互动数据、评论样本和缺失证据做保守分析。',
        ].join('\n'),
      },
      {
        role: 'user',
        content: JSON.stringify({
          theme,
          owner_positioning: '用 AI、Codex、Skill 和工作流完成真实有用的小项目，解决真实问题。',
          candidate: {
            description: candidate.description,
            source_keyword: candidate.source_keyword,
            metrics: {
              like_count: candidate.like_count,
              comment_count: candidate.comment_count,
              favorite_count: candidate.favorite_count,
              share_count: candidate.share_count,
            },
            score: candidate.score,
            comments: (candidate.comment_samples || []).slice(0, 8).map((comment) => cleanText(comment.text, 100)),
          },
          required_json_fields: [
            'user_problem',
            'retention_reason',
            'borrowable_structure',
            'do_not_copy',
            'original_angle',
            'owner_owned_case',
            'three_routes',
            'title_options',
            'cover_copy_options',
            'confidence',
            'confidence_reason',
            'risk_notes',
          ],
        }),
      },
    ],
  };

  const started = Date.now();
  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    const text = await response.text();
    const parsed = extractJsonObject(JSON.parse(text)?.choices?.[0]?.message?.content);
    runLog.ai_requests.push({
      type: 'structured_analysis',
      content_id: candidate.content_id,
      ok: response.ok && Boolean(parsed),
      statusCode: response.status,
      ms: Date.now() - started,
      model,
      error_summary: response.ok ? (parsed ? 'ok' : 'model returned non-json content') : cleanText(text, 180),
    });
    if (!response.ok || !parsed) {
      return {
        ...fallback,
        provider: 'heuristic_fallback_openai_failed',
        model,
        confidence_reason: `${fallback.confidence_reason} OpenAI 分析失败，已使用规则兜底。`,
      };
    }
    return {
      ...fallback,
      ...parsed,
      analysis_id: `${runId}-analysis-${index + 1}`,
      source_candidate_id: candidate.candidate_id,
      source_content_id: candidate.content_id,
      provider: 'openai_structured_analysis_v0.1',
      model,
      confidence: clamp(Number(parsed.confidence ?? fallback.confidence), 0, 1),
      borrowable_structure: normalizeStringArray(parsed.borrowable_structure, fallback.borrowable_structure),
      do_not_copy: normalizeStringArray(parsed.do_not_copy, fallback.do_not_copy),
      title_options: normalizeStringArray(parsed.title_options, fallback.title_options).slice(0, 5),
      cover_copy_options: normalizeStringArray(parsed.cover_copy_options, fallback.cover_copy_options).slice(0, 3),
      risk_notes: normalizeStringArray(parsed.risk_notes, fallback.risk_notes),
      evidence_used: fallback.evidence_used,
      evidence_limitations: fallback.evidence_limitations,
    };
  } catch (error) {
    runLog.ai_requests.push({
      type: 'structured_analysis',
      content_id: candidate.content_id,
      ok: false,
      statusCode: 0,
      ms: Date.now() - started,
      model,
      error_summary: cleanText(error, 180),
    });
    return {
      ...fallback,
      provider: 'heuristic_fallback_openai_exception',
      model,
      confidence_reason: `${fallback.confidence_reason} OpenAI 请求异常，已使用规则兜底。`,
    };
  }
}

function buildCreationBrief(candidate, index, analysis = heuristicStructuredAnalysis(candidate, index)) {
  return {
    brief_id: `${runId}-brief-${index + 1}`,
    source_candidate_id: candidate.candidate_id,
    source_content_id: candidate.content_id,
    source_url: candidate.content_url,
    source_rank: index + 1,
    source_summary: cleanText(candidate.description, 180),
    source_metrics: {
      like_count: candidate.like_count,
      comment_count: candidate.comment_count,
      favorite_count: candidate.favorite_count,
      share_count: candidate.share_count,
      comments_sample_count: candidate.score?.comments_sample_count || 0,
      demand_count: candidate.score?.demand_count || 0,
      missing_data: candidate.score?.missing_data || [],
    },
    analysis_id: analysis.analysis_id,
    analysis_provider: analysis.provider,
    analysis_model: analysis.model,
    recording_evidence: candidate.recording_evidence || recordingEvidence(candidate),
    recording_priority: candidate.recording_priority || recordingPriority(candidate),
    confidence: analysis.confidence,
    confidence_reason: analysis.confidence_reason,
    route: analysis.three_routes?.[0]?.route || '同痛点，换观点',
    user_problem: analysis.user_problem,
    retention_reason: analysis.retention_reason,
    original_angle: analysis.original_angle,
    owner_owned_case: analysis.owner_owned_case,
    borrowable_structure: analysis.borrowable_structure,
    do_not_copy: analysis.do_not_copy,
    three_routes: analysis.three_routes,
    title_options: analysis.title_options,
    cover_copy_options: analysis.cover_copy_options,
    evidence_used: analysis.evidence_used,
    evidence_limitations: analysis.evidence_limitations,
    risk_notes: analysis.risk_notes,
  };
}

function buildRecordingPackage(brief, index) {
  const angle = {
    pain: brief.user_problem,
    view: brief.original_angle,
    ownerCase: brief.owner_owned_case,
  };
  return {
    package_id: `${runId}-recording-${index + 1}`,
    brief_id: brief.brief_id,
    source_candidate_id: brief.source_candidate_id,
    recommended_title: brief.title_options[0],
    cover_copy: brief.cover_copy_options[0],
    teleprompter_script: buildVoiceoverScript(angle),
    shot_plan: [
      '纯口播为主，不展示热点雷达报告和原作者素材',
      '可用抽象流程卡片或录屏占位展示，不露内部数据',
      '字幕重点突出：真实问题、流程、检查点、Skill',
    ],
    required_materials: [
      '老板自己的真实项目或工作流例子',
      '不含敏感数据的流程概念图或白板式画面',
      '可公开表达的观点和限制说明',
    ],
    forbidden_materials: [
      '原作者视频画面',
      '原作者文案逐句改写',
      '热点雷达内部候选表或 API 原始数据',
      '收益、效率或爆款保证',
    ],
    subtitle_highlights: [
      '不是按钮，是流程',
      '先验证，再开发',
      '能检查，才叫能落地',
    ],
    pinned_comment_suggestion: '你现在最想把哪个重复流程交给 AI？可以留一个具体场景。',
    owner_review_gate: [
      '这个方向是否值得讲',
      '观点是否符合老板真实判断',
      '是否有自有案例支撑',
      '表达是否像老板本人',
    ],
    publish_ready: false,
    status: 'recording_material_ready_for_owner_review',
  };
}

const all = [];
for (const keyword of keywords) {
  if (runLog.requests.length >= requestBudget) break;
  const result = await apiPost('/api/v1/douyin/search/fetch_general_search_v2', {
    keyword,
    cursor: 0,
    count: 20,
    sort_type: '0',
    publish_time: '0',
  });
  const rawPath = path.join(rawSearchDir, `search-${slug(keyword)}.json`);
  fs.writeFileSync(rawPath, JSON.stringify(result.json, null, 2));
  const items = searchItems(result.json).map((item) => normalizeAweme(item, keyword, path.relative(root, rawPath)));
  const classification = classifyRequest(result, items.length, 'search');
  all.push(...items);
  runLog.requests.push({
    type: 'search',
    keyword,
    ok: classification.ok,
    error_category: classification.category,
    error_summary: classification.summary,
    statusCode: result.statusCode,
    apiCode: result.json?.code,
    item_count: items.length,
    bytes: result.bytes,
    ms: result.ms,
    file: path.relative(root, rawPath),
  });
}

const candidates = mergeCandidates(all);
fs.writeFileSync(path.join(normalizedDir, 'content-candidates.json'), JSON.stringify(candidates, null, 2));

let scored = candidates.map((candidate) => ({ ...candidate, score: scoreCandidate(candidate, []) }));
scored.sort((a, b) => b.score.total - a.score.total);

const commentTargets = scored.slice(0, Math.min(10, requestBudget - runLog.requests.length));
for (const item of commentTargets) {
  const result = await apiGet('/api/v1/douyin/app/v3/fetch_video_comments', {
    aweme_id: item.content_id,
    cursor: '0',
    count: '20',
  });
  const rawPath = path.join(rawCommentsDir, `${item.content_id}.json`);
  fs.writeFileSync(rawPath, JSON.stringify(result.json, null, 2));
  const comments = parseComments(result.json);
  const classification = classifyRequest(result, comments.length, 'comments');
  item.comment_samples = comments;
  item.score = scoreCandidate(item, comments);
  item.evidence_level = comments.length ? 'metadata_comments' : 'metadata';
  runLog.requests.push({
    type: 'comments',
    content_id: item.content_id,
    ok: classification.ok,
    error_category: classification.category,
    error_summary: classification.summary,
    statusCode: result.statusCode,
    apiCode: result.json?.code,
    parsed: Array.isArray(result.json?.data?.comments),
    count: comments.length,
    bytes: result.bytes,
    ms: result.ms,
    file: path.relative(root, rawPath),
  });
}

scored.sort((a, b) => b.score.total - a.score.total);
const selected = scored.filter((item) => item.score.tier.startsWith('A') || item.score.tier.startsWith('B')).slice(0, 20);
const recordingCandidates = chooseRecordingCandidates(selected);
const structuredAnalyses = [];
for (const [index, item] of recordingCandidates.entries()) {
  structuredAnalyses.push(await aiStructuredAnalysis(item, index));
}
fs.writeFileSync(path.join(analysesDir, 'structured-analyses.json'), JSON.stringify({
  generated_at: new Date().toISOString(),
  run_id: runId,
  theme,
  ai_analysis_enabled: runLog.ai_analysis_enabled,
  analysis_count: structuredAnalyses.length,
  structured_analyses: structuredAnalyses,
}, null, 2));
const creationBriefs = recordingCandidates.map((item, index) => buildCreationBrief(item, index, structuredAnalyses[index]));
const recordingPackages = creationBriefs.map((brief, index) => buildRecordingPackage(brief, index));
const scoreOutput = {
  generated_at: new Date().toISOString(),
  run_id: runId,
  theme,
  keywords,
  keyword_nodes: keywordNodes,
  ai_analysis_enabled: runLog.ai_analysis_enabled,
  request_budget: requestBudget,
  request_count: runLog.requests.length,
  candidate_count: candidates.length,
  selected_count: selected.length,
  selected,
  all_scores: scored,
};
fs.writeFileSync(path.join(scoresDir, 'opportunity-scores.json'), JSON.stringify(scoreOutput, null, 2));
fs.writeFileSync(path.join(briefsDir, 'creation-briefs.json'), JSON.stringify({
  generated_at: new Date().toISOString(),
  run_id: runId,
  theme,
  selection_rule: 'recording candidates must pass minimum interaction, comment-demand or very-strong-interaction, account-fit, score, and confidence gates; low-evidence own-view candidates stay in candidate pool',
  analysis_rule: 'prefer OpenAI structured analysis when HOTSPOT_AI_ANALYSIS=1 and OPENAI_API_KEY exists; otherwise use heuristic fallback with evidence limits',
  creation_briefs: creationBriefs,
}, null, 2));
fs.writeFileSync(path.join(briefsDir, 'recording-packages.json'), JSON.stringify({
  generated_at: new Date().toISOString(),
  run_id: runId,
  theme,
  publish_ready: false,
  recording_packages: recordingPackages,
}, null, 2));

runLog.finished_at = new Date().toISOString();
runLog.request_count = runLog.requests.length;
runLog.failure_summary = summarizeFailures(runLog.requests);
fs.writeFileSync(runLogPath, JSON.stringify(runLog, null, 2));
const failureSummaryPath = path.join(baseDir, 'logs/failure-summary.json');
fs.writeFileSync(failureSummaryPath, JSON.stringify({
  generated_at: new Date().toISOString(),
  run_id: runId,
  ...runLog.failure_summary,
}, null, 2));

const searchSuccess = runLog.requests.filter((request) => request.type === 'search' && request.ok).length;
const commentSuccess = runLog.requests.filter((request) => request.type === 'comments' && request.ok && request.parsed).length;
const failureRows = runLog.failure_summary.failures.map((failure) => {
  const target = failure.keyword || failure.content_id || '';
  return `| ${failure.type} | ${target} | ${failure.error_category} | ${failure.error_summary} | ${failure.statusCode} | ${failure.apiCode ?? ''} | ${failure.file} |`;
});
const rows = selected.map((item, index) => {
  const metrics = `${item.like_count}/${item.comment_count}/${item.favorite_count}/${item.share_count}`;
  const desc = String(item.description || '').replace(/\s+/g, ' ').slice(0, 90);
  return `| ${index + 1} | ${item.score.tier} | ${item.score.total} | ${desc} | ${metrics} | ${item.score.comments_sample_count} | ${item.score.demand_count} | ${item.score.recommended_action} |`;
});

const briefSections = creationBriefs.flatMap((brief, index) => {
  const pkg = recordingPackages[index];
  return [
    `### ${index + 1}. ${pkg.recommended_title}`,
    '',
    `来源候选：${brief.source_content_id}`,
    '',
    `数据：点赞 ${brief.source_metrics.like_count}，评论 ${brief.source_metrics.comment_count}，收藏 ${brief.source_metrics.favorite_count}，分享 ${brief.source_metrics.share_count}。`,
    '',
    `评论样本：${brief.source_metrics.comments_sample_count}，需求评论：${brief.source_metrics.demand_count}。`,
    '',
    `分析方式：${brief.analysis_provider}${brief.analysis_model ? ` / ${brief.analysis_model}` : ''}，置信度：${brief.confidence}。`,
    '',
    `录制证据门槛：${brief.recording_evidence.eligible ? '通过' : '未通过'}；${brief.recording_evidence.reason.join('；')}。`,
    '',
    `原创角度：${brief.original_angle}`,
    '',
    `停留理由：${brief.retention_reason}`,
    '',
    '可借鉴：',
    '',
    ...brief.borrowable_structure.map((item) => `- ${item}`),
    '',
    '不可照搬：',
    '',
    ...brief.do_not_copy.map((item) => `- ${item}`),
    '',
    `封面文案：${pkg.cover_copy}`,
    '',
    '提词器草稿：',
    '',
    pkg.teleprompter_script,
    '',
    '人工确认门：',
    '',
    ...pkg.owner_review_gate.map((item) => `- ${item}`),
    '',
    `状态：${pkg.status}，publish_ready: ${pkg.publish_ready}`,
    '',
  ];
});

const briefsReport = [
  '# Gate 1 创作简报与录制包',
  '',
  `日期：${new Date().toISOString().slice(0, 10)}`,
  '',
  `主题：${theme}`,
  '',
  '## 结论',
  '',
  `本轮在 ${selected.length} 条 A/B 候选中，按账号适配度和可拍性自动选出 ${creationBriefs.length} 条录制验证样本。`,
  '',
  `结构化分析：${structuredAnalyses.length} 条，AI 分析开关：${runLog.ai_analysis_enabled ? '开启' : '关闭，使用规则兜底'}。`,
  '',
  '这里输出的是内容机会候选的原创再创作材料，不是发布成品，也不是爆款保证。',
  '',
  '## 选择规则',
  '',
  '- 优先选择 Codex、Skill、AI 工作流、内容生产、真实项目相关候选；',
  '- 录制样本必须通过互动、评论需求或强互动、账号适配、机会分和置信度门槛；',
  '- 低互动、无评论、低置信度候选保留在候选池，不自动进入录制包；',
  '- 降权工厂自动化、机器人、军事科技、夸张收益和明显偏账号内容；',
  '- 每条保留来源指标、缺失数据、不可照搬边界、录制证据和人工确认门；',
  '- 不展示热点雷达内部报告，不展示原作者素材，不进入自动发布。',
  '',
  '## Top 录制验证样本',
  '',
  ...briefSections,
  '## 输出文件',
  '',
  `- 创作简报 JSON：data/gate-1/runs/${runId}/briefs/creation-briefs.json`,
  `- 结构化分析 JSON：data/gate-1/runs/${runId}/analyses/structured-analyses.json`,
  `- 录制包 JSON：data/gate-1/runs/${runId}/briefs/recording-packages.json`,
  `- 候选报告：reports/gate-1/${runId}-candidate-selection-report.md`,
  '',
].join('\n');
fs.writeFileSync(briefsReportPath, briefsReport);

const report = [
  `# Gate 1 新主题复跑候选筛选报告`,
  '',
  `日期：${new Date().toISOString().slice(0, 10)}`,
  '',
  `主题：${theme}`,
  '',
  '## 结论',
  '',
  `本轮输入 ${keywords.length} 个关键词，搜索请求 ${runLog.requests.filter((request) => request.type === 'search').length} 次，评论补证据请求 ${runLog.requests.filter((request) => request.type === 'comments').length} 次。`,
  '',
  `标准化去重候选 ${candidates.length} 条，自动输出 A/B 候选 ${selected.length} 条。`,
  '',
  '本轮仍只验证候选筛选、证据补齐和 Skill 工作流复跑，不进入 Web、拍摄、剪辑或发布。',
  '',
  '## 请求与错误',
  '',
  `- 搜索请求：${runLog.requests.filter((request) => request.type === 'search').length} 次，成功 ${searchSuccess} 次。`,
  `- 评论请求：${runLog.requests.filter((request) => request.type === 'comments').length} 次，成功解析 ${commentSuccess} 次。`,
  `- 总请求：${runLog.request_count} / ${requestBudget}。`,
  `- 失败请求：${runLog.failure_summary.failure_count} 次。`,
  '',
  ...(failureRows.length ? [
    '| 类型 | 关键词/内容 ID | 失败类型 | 摘要 | HTTP | API code | 原始文件 |',
    '|---|---|---|---|---:|---:|---|',
    ...failureRows,
  ] : [
    '本轮未记录失败请求。',
  ]),
  '',
  '## 关键词',
  '',
  '| 关键词 | 类型 | 状态 | 来源说明 |',
  '|---|---|---|---|',
  ...keywordNodes.map((node) => `| ${node.keyword} | ${node.type} | ${node.status} | ${node.reason} |`),
  '',
  '## Top 候选内容',
  '',
  '| 排名 | 层级 | 分数 | 内容摘要 | 互动数据 赞/评/藏/转 | 评论样本 | 需求评论数 | 推荐动作 |',
  '|---:|---|---:|---|---|---:|---:|---|',
  ...rows,
  '',
  '## 输出文件',
  '',
  `- 标准化候选：data/gate-1/runs/${runId}/normalized/content-candidates.json`,
  `- 关键词树：data/gate-1/runs/${runId}/keywords/keyword-nodes.json`,
  `- 评分结果：data/gate-1/runs/${runId}/scores/opportunity-scores.json`,
  `- 结构化分析：data/gate-1/runs/${runId}/analyses/structured-analyses.json`,
  `- 创作简报：data/gate-1/runs/${runId}/briefs/creation-briefs.json`,
  `- 录制包：data/gate-1/runs/${runId}/briefs/recording-packages.json`,
  `- 创作简报报告：reports/gate-1/${runId}-creation-briefs-and-recording-packages.md`,
  `- 运行日志：data/gate-1/runs/${runId}/logs/run-log.json`,
  `- 失败摘要：data/gate-1/runs/${runId}/logs/failure-summary.json`,
  '',
].join('\n');
fs.writeFileSync(reportPath, report);

console.log(JSON.stringify({
  run_id: runId,
  theme,
  request_count: runLog.request_count,
  candidate_count: candidates.length,
  selected_count: selected.length,
  creation_brief_count: creationBriefs.length,
  recording_package_count: recordingPackages.length,
  report: path.relative(root, reportPath),
  briefs_report: path.relative(root, briefsReportPath),
  scores: `data/gate-1/runs/${runId}/scores/opportunity-scores.json`,
  keyword_nodes: `data/gate-1/runs/${runId}/keywords/keyword-nodes.json`,
  failure_summary: `data/gate-1/runs/${runId}/logs/failure-summary.json`,
  structured_analyses: `data/gate-1/runs/${runId}/analyses/structured-analyses.json`,
  creation_briefs: `data/gate-1/runs/${runId}/briefs/creation-briefs.json`,
  recording_packages: `data/gate-1/runs/${runId}/briefs/recording-packages.json`,
}, null, 2));
