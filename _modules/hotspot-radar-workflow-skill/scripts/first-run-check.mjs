import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import {
  DEFAULT_TIKHUB_BASE_URL,
  findTikHubToken,
} from './tikhub-token.mjs';

const currentScriptDir = path.dirname(fileURLToPath(import.meta.url));

export function nodeMajor(version = process.version) {
  const match = String(version).match(/^v?(\d+)/);
  return match ? Number(match[1]) : 0;
}

export function buildFirstRunCheck({
  cwd = process.cwd(),
  env = process.env,
  platform = process.platform,
  nodeVersion = process.version,
  tokenResult = findTikHubToken({ env }),
  exists = fs.existsSync,
  scriptDir = currentScriptDir,
} = {}) {
  const baseUrl = env.TIKHUB_BASE_URL || DEFAULT_TIKHUB_BASE_URL;
  const scriptGroups = [
    {
      label: 'Token 保存脚本',
      paths: ['tools/setup-tikhub-token.mjs', 'scripts/setup-tikhub-token.mjs'],
    },
    {
      label: '主题抓取脚本',
      paths: ['tools/run-gate1-topic-validation.mjs', 'scripts/run-gate1-topic-validation.mjs'],
    },
    {
      label: '老板勾选表脚本',
      paths: ['tools/build-gate1a-owner-review.mjs', 'scripts/build-gate1a-owner-review.mjs'],
    },
    {
      label: '主题到勾选表一键入口',
      paths: ['tools/run-topic-checklist.mjs', 'scripts/run-topic-checklist.mjs'],
    },
  ];
  const scriptExists = (scriptPath) => {
    const localScriptPath = path.join(scriptDir, path.basename(scriptPath));
    const cwdScriptPath = path.join(cwd, scriptPath);
    const portable = (value) => value.replaceAll('\\', '/');
    return exists(cwdScriptPath)
      || exists(portable(cwdScriptPath))
      || exists(localScriptPath)
      || exists(portable(localScriptPath));
  };
  const missingScriptGroups = scriptGroups
    .filter((group) => !group.paths.some((scriptPath) => scriptExists(scriptPath)))
    .map((group) => group.label);
  const nodeOk = nodeMajor(nodeVersion) >= 18;
  const baseUrlOk = baseUrl === DEFAULT_TIKHUB_BASE_URL;

  const checks = [
    {
      id: 'node',
      label: 'Node.js 版本',
      ok: nodeOk,
      severity: nodeOk ? 'ok' : 'error',
      detail: nodeOk ? `${nodeVersion} 可运行热点雷达脚本` : `${nodeVersion} 过低，建议 Node.js 18 或以上`,
      next_step: nodeOk ? '' : '安装或切换到 Node.js 18+ 后重试。',
    },
    {
      id: 'platform',
      label: '本机平台',
      ok: true,
      severity: platform === 'darwin' ? 'ok' : 'warn',
      detail: platform === 'darwin'
        ? 'macOS 可使用 Keychain 保存 Token'
        : `${platform} 不是 macOS，Keychain 保存方式可能不可用`,
      next_step: platform === 'darwin' ? '' : '使用 TIKHUB_API_KEY 临时环境变量，或按本机系统改造密钥存储。',
    },
    {
      id: 'base_url',
      label: 'TikHub API 地址',
      ok: baseUrlOk,
      severity: baseUrlOk ? 'ok' : 'warn',
      detail: baseUrl,
      next_step: baseUrlOk ? '' : '确认该域名可信且由老板明确授权，默认只使用 https://api.tikhub.io。',
    },
    {
      id: 'token',
      label: 'TikHub Token',
      ok: Boolean(tokenResult.token),
      severity: tokenResult.token ? 'ok' : 'error',
      detail: tokenResult.token ? `已找到：${tokenResult.source}` : '未找到可用 Token',
      next_step: tokenResult.token ? '' : '运行 node scripts/setup-tikhub-token.mjs 保存 Token。',
    },
    {
      id: 'scripts',
      label: 'Skill 脚本',
      ok: missingScriptGroups.length === 0,
      severity: missingScriptGroups.length === 0 ? 'ok' : 'error',
      detail: missingScriptGroups.length === 0 ? '必需脚本齐全' : `缺少：${missingScriptGroups.join('、')}`,
      next_step: missingScriptGroups.length === 0 ? '' : '重新安装完整 hotspot-radar-workflow Skill 包。',
    },
  ];

  return {
    ok: checks.every((check) => check.severity !== 'error'),
    base_url: baseUrl,
    token_source: tokenResult.source || null,
    checks,
  };
}

export function formatFirstRunCheck(result) {
  const icon = (check) => {
    if (check.severity === 'ok') return '[OK]';
    if (check.severity === 'warn') return '[WARN]';
    return '[NEED]';
  };
  const lines = [
    '# 热点雷达首次运行检查',
    '',
    `总体状态：${result.ok ? '可真实抓取' : '尚未就绪'}`,
    '',
    ...result.checks.flatMap((check) => [
      `${icon(check)} ${check.label}：${check.detail}`,
      check.next_step ? `  下一步：${check.next_step}` : '',
    ].filter(Boolean)),
    '',
  ];

  if (!result.ok) {
    lines.push('最短配置路径：');
    lines.push('1. 打开 https://user.tikhub.io/dashboard/api 复制 TikHub API Token。');
    lines.push('2. 运行 node scripts/setup-tikhub-token.mjs。');
    lines.push('3. 再运行 node scripts/first-run-check.mjs。');
    lines.push('4. 看到“总体状态：可真实抓取”后，再输入主题执行热点雷达。');
  }

  return lines.join('\n');
}

function main() {
  const result = buildFirstRunCheck();
  if (process.argv.includes('--json')) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(formatFirstRunCheck(result));
  }
  process.exit(result.ok ? 0 : 1);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  main();
}
