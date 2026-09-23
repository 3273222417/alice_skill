import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildMissingTikHubTokenMessage,
  findTikHubToken,
  installTikHubToken,
  keychainTargets,
  PRIMARY_TIKHUB_SERVICE,
} from '../scripts/tikhub-token.mjs';

test('uses TIKHUB_API_KEY from environment first', () => {
  const result = findTikHubToken({
    env: { TIKHUB_API_KEY: '  env-token  ', USER: 'alice' },
    execFileSync: () => {
      throw new Error('keychain should not be called');
    },
  });

  assert.equal(result.token, 'env-token');
  assert.equal(result.source, 'env:TIKHUB_API_KEY');
});

test('checks hotspot radar keychain target before legacy target', () => {
  const calls = [];
  const result = findTikHubToken({
    env: { USER: 'alice' },
    execFileSync: (_cmd, args) => {
      calls.push(args);
      if (args.includes(PRIMARY_TIKHUB_SERVICE)) return 'primary-token\n';
      throw new Error('unexpected target');
    },
  });

  assert.equal(result.token, 'primary-token');
  assert.equal(result.source, `keychain:${PRIMARY_TIKHUB_SERVICE}/alice`);
  assert.equal(calls.length, 1);
});

test('keeps legacy ai_anget keychain target for existing installs', () => {
  const result = findTikHubToken({
    env: { USER: 'alice' },
    execFileSync: (_cmd, args) => {
      if (args.includes(PRIMARY_TIKHUB_SERVICE)) {
        const error = new Error('not found');
        error.status = 44;
        throw error;
      }
      return 'legacy-token\n';
    },
  });

  assert.equal(result.token, 'legacy-token');
  assert.equal(result.source, 'keychain:ai_anget_tikhub_api_token/dalin');
});

test('install writes to primary keychain service and current account', () => {
  let savedArgs = null;
  const target = installTikHubToken('secret-token', {
    env: { USER: 'alice' },
    execFileSync: (_cmd, args) => {
      savedArgs = args;
      return '';
    },
  });

  assert.deepEqual(target, { service: PRIMARY_TIKHUB_SERVICE, account: 'alice' });
  assert.deepEqual(savedArgs.slice(0, 6), ['add-generic-password', '-U', '-s', PRIMARY_TIKHUB_SERVICE, '-a', 'alice']);
  assert.equal(savedArgs.at(-1), 'secret-token');
});

test('missing token message gives setup command and default base url', () => {
  const message = buildMissingTikHubTokenMessage({ USER: 'alice' });
  assert.match(message, /node scripts\/setup-tikhub-token\.mjs/);
  assert.match(message, /https:\/\/api\.tikhub\.io/);
  assert.match(message, new RegExp(PRIMARY_TIKHUB_SERVICE));
  assert.match(message, /alice/);
});

test('keychain targets include primary and legacy locations', () => {
  assert.deepEqual(keychainTargets({ USER: 'alice' }), [
    { service: PRIMARY_TIKHUB_SERVICE, account: 'alice' },
    { service: 'ai_anget_tikhub_api_token', account: 'dalin' },
  ]);
});
