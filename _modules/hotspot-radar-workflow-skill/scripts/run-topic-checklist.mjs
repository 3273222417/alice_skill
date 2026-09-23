import { spawnSync } from 'node:child_process';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));

function slug(input) {
  return String(input || '')
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\p{Letter}\p{Number}-]+/gu, '')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}

export function parseArgs(args) {
  const options = { runId: '', themeParts: [] };
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === '--run-id') {
      options.runId = args[index + 1] || '';
      index += 1;
      continue;
    }
    options.themeParts.push(arg);
  }
  const theme = options.themeParts.join(' ').trim();
  const date = new Date().toISOString().slice(0, 10);
  return {
    theme,
    runId: options.runId || `topic-${slug(theme || 'theme')}-${date}`,
  };
}

function runNode(scriptName, args) {
  const scriptPath = path.join(scriptDir, scriptName);
  const result = spawnSync(process.execPath, [scriptPath, ...args], {
    cwd: process.cwd(),
    encoding: 'utf8',
    stdio: 'inherit',
  });
  if (result.status !== 0) process.exit(result.status || 1);
}

export function usage() {
  return [
    '用法：',
    'node scripts/run-topic-checklist.mjs "AI 自动化真实项目"',
    '',
    '可选：',
    'node scripts/run-topic-checklist.mjs --run-id topic-ai-001 "AI 自动化真实项目"',
  ].join('\n');
}

function main() {
  const { theme, runId } = parseArgs(process.argv.slice(2));
  if (!theme) {
    console.error(usage());
    process.exit(1);
  }

  console.log(`热点雷达主题：${theme}`);
  console.log(`运行编号：${runId}`);
  console.log('流程：首次检查 -> 关键词扩展 -> 抖音候选抓取 -> 评分 -> 10 条候选勾选表');

  runNode('first-run-check.mjs', []);
  runNode('run-gate1-topic-validation.mjs', [runId, theme]);
  runNode('build-gate1a-owner-review.mjs', [
    runId,
    `reports/gate-1/${runId}-owner-review-checklist.md`,
  ]);

  console.log('');
  console.log(`已生成候选勾选表：reports/gate-1/${runId}-owner-review-checklist.md`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
