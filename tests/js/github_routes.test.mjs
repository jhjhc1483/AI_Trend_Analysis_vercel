// api/github.js 허용 목록: 대시보드가 쓰는 요청만 통과하고, 파일 삭제·임의 경로는 막히는지
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { findAccess } from '../../api/github.js';

const R = 'repos/jhjhc1483/AI_Trend_Analysis_vercel/';

test('favorites files: anyone reads, admin writes', () => {
    assert.equal(findAccess(`${R}contents/codes/favorites/favorite_articles.json?ref=main`, 'GET'), 'public');
    assert.equal(findAccess(`${R}contents/codes/favorites/fewshot_examples.json`, 'PUT'), 'admin');
    assert.equal(findAccess(`${R}contents/codes/favorites/favorite_articles.json`, 'DELETE'), null);
});

test('workflows: admin dispatch, public run status, mail cannot be dispatched', () => {
    assert.equal(findAccess(`${R}actions/workflows/main.yml/dispatches`, 'POST'), 'admin');
    assert.equal(findAccess(`${R}actions/workflows/kakao_or_gmail_send.yml/dispatches`, 'POST'), null);
    assert.equal(findAccess(`${R}actions/workflows/audio_gen.yml/runs?per_page=1`, 'GET'), 'public');
    assert.equal(findAccess(`${R}actions/workflows/audio_gen.yml/runs?per_page=100`, 'GET'), null);
    assert.equal(findAccess(`${R}actions/workflows/audio_gen.yml/runs?per_page=1&branch=x`, 'GET'), null);
});

test('no file deletion, no other repos, no path tricks', () => {
    assert.equal(findAccess(`${R}contents/codes/data.json`, 'DELETE'), null);
    assert.equal(findAccess(`${R}contents/codes`, 'GET'), null);
    assert.equal(findAccess(`${R}contents/codes/receiver_email.json`, 'GET'), null);
    assert.equal(findAccess('repos/someone/else/contents/codes/favorites/favorite_articles.json', 'GET'), null);
    assert.equal(findAccess(`${R}contents/codes/favorites/../receiver_email.json`, 'GET'), null);
    assert.equal(findAccess(undefined, 'GET'), null);
});
