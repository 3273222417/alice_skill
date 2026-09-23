#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const args = process.argv.slice(2);
const cmd = args[0] || 'help';

function arg(name, fallback = null) {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : fallback;
}
function has(name) { return args.includes(name); }
function projectRoot() { return path.resolve(arg('--project', process.cwd())); }
function readText(file) { return fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''); }
function ensureDir(dir) { fs.mkdirSync(dir, { recursive: true }); }
function clean(value) { return String(value || '').replace(/^[-*]\s*/, '').replace(/\*\*/g, '').trim(); }
function normalizeId(value) {
  const s = String(value || '').toLowerCase().trim()
    .replace(/[^a-z0-9\u4e00-\u9fff]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  return s || 'expert';
}
function extractField(block, label) {
  const re = new RegExp(`^- \\*\\*${label}\\*\\*:\\s*(.+)$`, 'm');
  const m = block.match(re);
  return m ? clean(m[1]) : '';
}
function extractPrompt(block) {
  const m = block.match(/^- \*\*提示词\*\*:\s*$/m);
  if (!m || m.index == null) return '';
  return block.slice(m.index + m[0].length).replace(/^`{3,4}[a-zA-Z0-9_-]*\s*/, '').replace(/\s*`{3,4}\s*$/, '').trim();
}
function parseIntro(intro) {
  const sourceId = intro.match(/来源标识:\s*`([^`]+)`/)?.[1]?.trim() || '';
  const tagsText = intro.match(/标签:\s*([^;]+)/)?.[1]?.trim() || '';
  const tags = tagsText.split(/\s*\/\s*|[、,，]/).map(s => s.trim()).filter(Boolean);
  const identity = intro.split(';').map(s => s.trim()).find(Boolean) || '';
  const name = identity.split('/')[0]?.trim() || '';
  return { sourceId, tags, identity, name };
}
function categorize(title, tags, desc) {
  const hay = `${title} ${tags.join(' ')} ${desc}`;
  if (/内容|文案|小红书|抖音|视频|直播|广告|品牌|营销|电商|脚本|创作/.test(hay)) return '内容增长';
  if (/股票|投资|财务|数据|分析|研报|交易|BI|KPI/.test(hay)) return '经营分析';
  if (/法律|合同|合规|风控|审查|法务|税/.test(hay)) return '法务合规';
  if (/招聘|HR|人力|组织|培训|销售|客户|CRM/.test(hay)) return '企业运营';
  if (/开发|代码|架构|产品|设计|UI|工程|技术/.test(hay)) return '产品技术';
  return '专业咨询';
}
function parseExperts(root) {
  const mdPath = path.join(root, 'docs', 'workbuddy-agent-prompts.md');
  const md = readText(mdPath);
  const re = /^##\s+(\d{3})\.\s+(.+?)(?:\s+\((.*?)\))?\s*$/gm;
  const matches = [...md.matchAll(re)];
  return matches.map((m, index) => {
    const start = m.index || 0;
    const end = matches[index + 1]?.index ?? md.length;
    const block = md.slice(start, end);
    const title = extractField(block, '标题') || m[2].trim();
    const intro = extractField(block, '介绍');
    const parsed = parseIntro(intro);
    const id = normalizeId(parsed.sourceId || `${m[1]}-${title}`);
    const prompt = extractPrompt(block);
    const tags = parsed.tags.length ? parsed.tags : [categorize(title, [], intro)];
    const category = categorize(title, tags, intro);
    return { index: index + 1, id, title, intro, name: parsed.name, subtitle: parsed.identity, tags, category, prompt };
  }).filter(e => e.title && e.prompt);
}
function avatarDir(root) { return path.join(root, 'public', 'expert-avatars', 'image2'); }
function existingIds(root) {
  const dir = avatarDir(root);
  if (!fs.existsSync(dir)) return new Set();
  return new Set(fs.readdirSync(dir).filter(f => f.endsWith('.webp')).map(f => f.replace(/\.webp$/, '')));
}
function missingExperts(root) {
  const existing = existingIds(root);
  return parseExperts(root).filter(e => !existing.has(e.id));
}
const faceShapes = ['round face', 'oval face', 'square face', 'heart-shaped face', 'angular face', 'long narrow face', 'broad mature face', 'soft youthful face'];
const hairstyles = ['short wavy hair', 'neat side-part hair', 'short bob', 'high ponytail', 'curly hair', 'silver swept hair', 'low ponytail with glasses', 'messy topknot'];
const outfits = ['casual blazer', 'hoodie', 'cardigan', 'business vest', 'turtleneck jacket', 'minimalist suit', 'coach blazer', 'studio jacket'];
const palettes = ['peach, emerald, cream', 'navy, orange, warm ivory', 'teal, coral, midnight blue', 'rose, sage, beige', 'slate blue, silver, muted teal', 'purple, yellow, charcoal', 'crimson, gold, soft black', 'lime, teal, auburn'];
function promptFor(expert) {
  const n = expert.index;
  const tags = expert.tags.slice(0, 4).join(' / ') || expert.category;
  return [
    'Use case: stylized-concept',
    'Asset type: 1 square expert avatar for OpenClaw app',
    `Primary request: ${expert.title} avatar, ${expert.category} professional; keywords: ${tags}`,
    `Scene/backdrop: domain-specific ${expert.category} workspace with 1-3 abstract props related to ${tags}, no readable text, no logos`,
    `Subject: distinct 2D cartoon Chinese professional character, ${faceShapes[n % faceShapes.length]}, ${hairstyles[(n * 3) % hairstyles.length]}, ${outfits[(n * 5) % outfits.length]}, holding one clear role-specific prop`,
    'Style/medium: polished 2D cartoon app-avatar illustration, cute professional, clean UI asset, NOT realistic, NOT photo',
    'Composition/framing: square close-up icon, head and shoulders, clear silhouette, generous padding, rounded app-icon feel',
    'Lighting/mood: friendly, capable, premium but simple',
    `Color palette: ${palettes[(n * 7) % palettes.length]}; avoid repeating nearby avatars`,
    'Constraints: single avatar only, no text, no watermark, no brand/platform logos, no photorealism, no real-person portrait, do not repeat previous character designs',
  ].join('\n');
}
function writePlan(root, limit, out) {
  const items = missingExperts(root).slice(0, limit).map(e => ({ ...e, output: `public/expert-avatars/image2/${e.id}.webp`, imagegenPrompt: promptFor(e) }));
  ensureDir(path.dirname(out));
  fs.writeFileSync(out, JSON.stringify({ generatedAt: new Date().toISOString(), project: root, count: items.length, items }, null, 2), 'utf8');
  return items;
}
async function saveImages(root, mapFile) {
  const requireFromProject = createRequire(path.join(root, 'package.json'));
  const sharp = requireFromProject('sharp');
  const parsed = JSON.parse(readText(mapFile));
  const entries = Array.isArray(parsed) ? parsed : parsed.items;
  if (!Array.isArray(entries)) throw new Error('map must be an array or {items:[{id,src}]}');
  ensureDir(avatarDir(root));
  const results = [];
  for (const item of entries) {
    const id = normalizeId(item.id || item.expertId || '');
    const src = path.resolve(root, item.src || item.path || '');
    if (!id || !fs.existsSync(src)) throw new Error(`missing src for ${id}: ${src}`);
    const dst = path.join(avatarDir(root), `${id}.webp`);
    await sharp(src).resize(256, 256, { fit: 'cover' }).webp({ quality: Number(item.quality || 72), effort: 6 }).toFile(dst);
    results.push({ id, dst, bytes: fs.statSync(dst).size });
  }
  console.log(JSON.stringify({ saved: results.length, results }, null, 2));
}
function printTable(items) {
  for (const e of items) console.log(`${String(e.index).padStart(3, '0')}\t${e.id}\t${e.title}\t${e.tags.slice(0,3).join('/')}`);
}
async function main() {
  const root = projectRoot();
  if (cmd === 'stats') {
    const total = parseExperts(root).length;
    const existing = existingIds(root).size;
    console.log(JSON.stringify({ project: root, total, existing, missing: Math.max(0, total - existing), avatarDir: avatarDir(root) }, null, 2));
    return;
  }
  if (cmd === 'list') {
    printTable(missingExperts(root).slice(0, Number(arg('--limit', 20))));
    return;
  }
  if (cmd === 'plan') {
    const out = path.resolve(root, arg('--out', 'tmp/expert-avatar-batch/next.json'));
    const items = writePlan(root, Number(arg('--limit', 4)), out);
    console.log(`wrote ${items.length} prompts -> ${out}`);
    printTable(items);
    if (has('--print-prompts')) console.log(readText(out));
    return;
  }
  if (cmd === 'save') {
    const map = path.resolve(root, arg('--map'));
    await saveImages(root, map);
    return;
  }
  console.log(`Usage:
  node expert_avatar_batch.mjs stats --project <root>
  node expert_avatar_batch.mjs list --project <root> --limit 12
  node expert_avatar_batch.mjs plan --project <root> --limit 4 --out tmp/expert-avatar-batch/next.json [--print-prompts]
  node expert_avatar_batch.mjs save --project <root> --map tmp/expert-avatar-batch/generated-map.json`);
}
main().catch(err => { console.error(err); process.exit(1); });


