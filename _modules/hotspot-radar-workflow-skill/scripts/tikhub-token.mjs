import { execFileSync as defaultExecFileSync } from 'node:child_process';
import os from 'node:os';

export const DEFAULT_TIKHUB_BASE_URL = 'https://api.tikhub.io';
export const PRIMARY_TIKHUB_SERVICE = 'hotspot_radar_tikhub_api_token';
export const LEGACY_TIKHUB_SERVICE = 'ai_anget_tikhub_api_token';

export function tikhubAccount(env = process.env) {
  return env.TIKHUB_KEYCHAIN_ACCOUNT || env.USER || os.userInfo().username || 'default';
}

export function keychainTargets(env = process.env) {
  const account = tikhubAccount(env);
  return [
    { service: PRIMARY_TIKHUB_SERVICE, account },
    { service: LEGACY_TIKHUB_SERVICE, account: 'dalin' },
  ];
}

export function findTikHubToken({
  env = process.env,
  execFileSync = defaultExecFileSync,
} = {}) {
  if (env.TIKHUB_API_KEY && env.TIKHUB_API_KEY.trim()) {
    return {
      token: env.TIKHUB_API_KEY.trim(),
      source: 'env:TIKHUB_API_KEY',
    };
  }

  const errors = [];
  for (const target of keychainTargets(env)) {
    try {
      const token = execFileSync('security', [
        'find-generic-password',
        '-s',
        target.service,
        '-a',
        target.account,
        '-w',
      ], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
      if (token) {
        return {
          token,
          source: `keychain:${target.service}/${target.account}`,
        };
      }
    } catch (error) {
      errors.push(`${target.service}/${target.account}: ${error.status || error.message}`);
    }
  }

  return {
    token: '',
    source: '',
    errors,
  };
}

export function installTikHubToken(token, {
  env = process.env,
  execFileSync = defaultExecFileSync,
} = {}) {
  const clean = String(token || '').trim();
  if (!clean) throw new Error('TikHub Token 不能为空');
  const account = tikhubAccount(env);
  execFileSync('security', [
    'add-generic-password',
    '-U',
    '-s',
    PRIMARY_TIKHUB_SERVICE,
    '-a',
    account,
    '-w',
    clean,
  ], { stdio: ['ignore', 'ignore', 'pipe'] });
  return { service: PRIMARY_TIKHUB_SERVICE, account };
}

export function buildMissingTikHubTokenMessage(env = process.env) {
  const account = tikhubAccount(env);
  return [
    '缺少 TikHub API Token，热点雷达无法执行真实抓取。',
    '',
    '首次使用前请先准备：',
    `1. TikHub API 地址：${env.TIKHUB_BASE_URL || DEFAULT_TIKHUB_BASE_URL}`,
    '2. TikHub API Token：从 TikHub 控制台复制。',
    '',
    '推荐保存方式：',
    `node scripts/setup-tikhub-token.mjs`,
    '',
    '运行后把 Token 粘贴进去，脚本会保存到本机 macOS 钥匙串：',
    `- service: ${PRIMARY_TIKHUB_SERVICE}`,
    `- account: ${account}`,
    '',
    '临时方式：',
    '在当前终端设置环境变量 TIKHUB_API_KEY 后再运行。不要把 Token 写入项目文件、报告或 Git。',
  ].join('\n');
}
