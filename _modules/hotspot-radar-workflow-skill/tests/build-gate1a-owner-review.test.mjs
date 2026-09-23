import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildOwnerReviewMarkdown,
  normalizeThemeKey,
  selectOwnerReviewCandidates,
} from '../scripts/build-gate1a-owner-review.mjs';

function item(id, total, angle, overrides = {}) {
  return {
    candidate_id: id,
    content_id: id,
    content_url: `https://example.com/${id}`,
    author_name: `作者${id}`,
    description: overrides.description || `${angle} 候选内容`,
    like_count: overrides.like_count ?? 1000,
    comment_count: overrides.comment_count ?? 100,
    favorite_count: overrides.favorite_count ?? 800,
    share_count: overrides.share_count ?? 120,
    score: {
      total,
      tier: total >= 75 ? 'A 自动优先候选' : 'B 可研究候选',
      dimensions: {
        basic_metrics: 20,
        user_demand: overrides.user_demand ?? 8,
        track_relevance: 18,
        account_fit: 18,
        transferability: 12,
        structure_clarity: 5,
        freshness: 4,
        evidence_completeness: 3,
        risk_penalty: overrides.risk_penalty ?? 0,
      },
      demand_count: overrides.demand_count ?? 3,
      comments_sample_count: overrides.comments_sample_count ?? 10,
      missing_data: ['play_count', 'completion_rate'],
    },
    radar_angle: angle,
  };
}

test('selects score-ordered candidates while preserving angle diversity first', () => {
  const selected = selectOwnerReviewCandidates([
    item('tutorial-1', 100, 'codex教程'),
    item('tutorial-2', 99, 'codex教程'),
    item('skill-1', 94, 'skill工作流'),
    item('project-1', 92, '真实项目'),
    item('content-1', 90, '内容生产'),
  ], 4);

  assert.deepEqual(selected.map((entry) => entry.candidate_id), [
    'tutorial-1',
    'skill-1',
    'project-1',
    'content-1',
  ]);
});

test('excludes candidates already returned for the same theme', () => {
  const selected = selectOwnerReviewCandidates([
    item('old-1', 100, 'codex教程'),
    item('new-1', 92, 'codex教程'),
    item('new-2', 88, 'skill工作流'),
  ], 2, {
    seenCandidateIds: new Set(['old-1']),
  });

  assert.deepEqual(selected.map((entry) => entry.candidate_id), ['new-1', 'new-2']);
});

test('excludes near-duplicate topic fingerprints when candidate ids differ', () => {
  const duplicate = item('new-id', 95, 'codex教程', { description: 'Codex 保姆级教程！零基础入门' });
  const selected = selectOwnerReviewCandidates([
    duplicate,
    item('different', 90, '真实项目', { description: 'Codex 实战搭建运营日报系统' }),
  ], 2, {
    seenTopicFingerprints: new Set(['codex-保姆级教程-零基础入门']),
  });

  assert.deepEqual(selected.map((entry) => entry.candidate_id), ['different']);
});

test('normalizes theme keys for history lookup', () => {
  assert.equal(
    normalizeThemeKey(' AI / Codex / Skill  '),
    normalizeThemeKey('ai codex skill'),
  );
});

test('owner review markdown is a checklist, not a script package', () => {
  const markdown = buildOwnerReviewMarkdown({
    runId: 'test-run',
    theme: 'AI Codex Skill',
    sourceRunId: 'source-run',
    candidates: [
      item('one', 100, 'codex教程', { description: 'Codex 教程怎么上手' }),
      item('two', 88, 'skill工作流', { description: 'Skill 工作流怎么串起来' }),
    ],
  });

  assert.match(markdown, /老板勾选判断表/);
  assert.match(markdown, /\[ \] 要做/);
  assert.match(markdown, /\[ \] 可观察/);
  assert.match(markdown, /\[ \] 不要做/);
  assert.match(markdown, /点赞/);
  assert.doesNotMatch(markdown, /### 口播稿|完整口播稿|录制包/);
});
