import assert from 'node:assert/strict';
import test from 'node:test';

import {
  parseArgs,
  usage,
} from '../scripts/run-topic-checklist.mjs';

test('parses a theme into a default run id', () => {
  const parsed = parseArgs(['AI 自动化真实项目']);
  assert.equal(parsed.theme, 'AI 自动化真实项目');
  assert.match(parsed.runId, /^topic-ai-自动化真实项目-\d{4}-\d{2}-\d{2}$/);
});

test('accepts an explicit run id', () => {
  const parsed = parseArgs(['--run-id', 'topic-ai-001', 'Codex Skill 工作流']);
  assert.equal(parsed.theme, 'Codex Skill 工作流');
  assert.equal(parsed.runId, 'topic-ai-001');
});

test('usage explains the simple theme-first command', () => {
  assert.match(usage(), /run-topic-checklist/);
  assert.match(usage(), /AI 自动化真实项目/);
});
