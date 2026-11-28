// scripts/build-dashboard-data.mjs: 배포 때 만드는 대시보드 첫 화면 데이터
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildDashboardData } from '../../scripts/build-dashboard-data.mjs';

function fixture() {
    const root = mkdtempSync(join(tmpdir(), 'dash-'));
    mkdirSync(join(root, 'config'));
    mkdirSync(join(root, 'codes'));
    writeFileSync(join(root, 'config', 'sources.json'), JSON.stringify({ sources: [
        { id: 'MND', type: 'article', file: 'mnd.json' },
        { id: 'NIPA', type: 'publication', file: 'NIPA.json' },
        { id: 'BROKEN', type: 'article', file: 'missing.json' },
    ] }));
    writeFileSync(join(root, 'codes', 'mnd.json'), JSON.stringify([
        { 기사명: '오늘', 년: '2026', 월: '11', 일: '27' },
        { 기사명: '한 자리 월일', 년: '2026', 월: '11', 일: '5' },
        { 기사명: '오래됨', 년: '2026', 월: '09', 일: '01' },
        { 기사명: '날짜 없음', 년: '', 월: '', 일: '' },
    ]));
    writeFileSync(join(root, 'codes', 'NIPA.json'), JSON.stringify([{ 제목: '4월 보고서', 년: '2026', 월: '04', 일: '09' }]));
    return root;
}

test('articles: last 30 days (KST) + undated; publications: everything', () => {
    const { payload, total } = buildDashboardData({ root: fixture(), now: new Date('2026-11-27T20:00:00Z') });  // 11/28 05:00 KST
    assert.deepEqual(payload.files['mnd.json'].map(i => i.기사명), ['오늘', '한 자리 월일', '날짜 없음']);
    assert.equal(payload.files['NIPA.json'].length, 1, '몇 달 전 간행물도 포함');
    assert.deepEqual(payload.files['missing.json'], [], '파일이 없어도 빌드는 계속');
    assert.deepEqual(payload.complete_types, ['publication']);
    assert.equal(total, 4);
    assert.equal(payload.data_updated_at, null, 'git 기록이 없으면 null (대시보드는 update_time.json 사용)');
});
