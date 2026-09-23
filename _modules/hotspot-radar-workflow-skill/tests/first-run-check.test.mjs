import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildFirstRunCheck,
  formatFirstRunCheck,
  nodeMajor,
} from '../scripts/first-run-check.mjs';

const allScripts = new Set([
  'scripts/setup-tikhub-token.mjs',
  'scripts/run-gate1-topic-validation.mjs',
  'scripts/build-gate1a-owner-review.mjs',
  'scripts/run-topic-checklist.mjs',
]);

function exists(filePath) {
  return allScripts.has(filePath.replace('/project/', ''));
}

test('accepts Node 18 and above', () => {
  assert.equal(nodeMajor('v18.19.0'), 18);
  assert.equal(nodeMajor('v22.0.0'), 22);
});

test('reports ready when node, token, base url, and scripts are available', () => {
  const result = buildFirstRunCheck({
    cwd: '/project',
    env: {},
    platform: 'darwin',
    nodeVersion: 'v22.0.0',
    tokenResult: { token: 'token', source: 'keychain:hotspot_radar_tikhub_api_token/alice' },
    exists,
  });

  assert.equal(result.ok, true);
  assert.equal(result.token_source, 'keychain:hotspot_radar_tikhub_api_token/alice');
});

test('blocks real fetching when token is missing', () => {
  const result = buildFirstRunCheck({
    cwd: '/project',
    env: {},
    platform: 'darwin',
    nodeVersion: 'v22.0.0',
    tokenResult: { token: '', source: '' },
    exists,
  });

  assert.equal(result.ok, false);
  assert.equal(result.checks.find((check) => check.id === 'token').severity, 'error');
  assert.match(formatFirstRunCheck(result), /首次运行检查/);
  assert.match(formatFirstRunCheck(result), /setup-tikhub-token/);
});

test('warns when a non-default API base url is configured', () => {
  const result = buildFirstRunCheck({
    cwd: '/project',
    env: { TIKHUB_BASE_URL: 'https://example.com' },
    platform: 'darwin',
    nodeVersion: 'v22.0.0',
    tokenResult: { token: 'token', source: 'env:TIKHUB_API_KEY' },
    exists,
  });

  assert.equal(result.ok, true);
  assert.equal(result.checks.find((check) => check.id === 'base_url').severity, 'warn');
});

test('accepts a package-only skill scripts directory', () => {
  const result = buildFirstRunCheck({
    cwd: '/elsewhere',
    scriptDir: '/skill/scripts',
    env: {},
    platform: 'darwin',
    nodeVersion: 'v22.0.0',
    tokenResult: { token: 'token', source: 'env:TIKHUB_API_KEY' },
    exists: (filePath) => [
      '/skill/scripts/setup-tikhub-token.mjs',
      '/skill/scripts/run-gate1-topic-validation.mjs',
      '/skill/scripts/build-gate1a-owner-review.mjs',
      '/skill/scripts/run-topic-checklist.mjs',
    ].includes(filePath),
  });

  assert.equal(result.checks.find((check) => check.id === 'scripts').ok, true);
});
