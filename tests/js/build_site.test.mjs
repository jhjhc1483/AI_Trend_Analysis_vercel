// scripts/build-site.mjs + vercel.json: 사이트에 필요한 파일만 배포되고, 주소 연결이 맞는지
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildSite } from '../../scripts/build-site.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const out = join(mkdtempSync(join(tmpdir(), 'site-')), 'dist');
buildSite({ root: ROOT, out });
const vercel = JSON.parse(readFileSync(join(ROOT, 'vercel.json'), 'utf8'));

test('only site files are published', () => {
    for (const file of ['index.html', 'visualizer.html', 'subscribe.html', 'public/bf.html', 'public/audio.mp3',
        'config/sources.json', 'codes/data.json', 'codes/data.txt', 'codes/mnd.json', 'codes/favorites/favorite_articles.json',
        'codes/dashboard/recent.json']) {
        assert.ok(existsSync(join(out, file)), `배포에 있어야 함: ${file}`);
    }
    for (const file of ['codes/receiver_email.json', 'codes/pycode', 'codes/state', 'README.md', 'requirements.txt',
        '.vscode', '.github', 'tests', 'scripts', 'api', 'vercel.json', '.gitignore']) {
        assert.ok(!existsSync(join(out, file)), `배포되면 안 됨: ${file}`);
    }
});

test('every short address points to a published page', () => {
    const pages = vercel.rewrites.filter(r => !r.source.startsWith('/api/'));
    assert.deepEqual(pages.map(r => r.source).sort(), ['/brief', '/listen', '/report', '/subscribe']);
    for (const { source, destination } of pages) {
        assert.ok(existsSync(join(out, destination)), `${source} → ${destination} 파일이 배포에 없음`);
    }
});

test('old addresses redirect to the new ones (links in sent mail keep working)', () => {
    const targets = new Set(['/', ...vercel.rewrites.map(r => r.source)]);
    const sources = vercel.redirects.map(r => r.source);
    for (const old of ['/visualizer.html', '/visualizer_brief.html', '/public/bf.html', '/subscribe.html']) {
        assert.ok(sources.includes(old), `예전 주소 ${old} 이동 규칙이 없음`);
    }
    for (const { source, destination, permanent } of vercel.redirects) {
        assert.ok(targets.has(destination), `${source} → ${destination} 는 연결된 주소가 아님`);
        assert.equal(permanent, true);
    }
});

test('pages load data from root paths (work under /report, /listen, ...)', () => {
    for (const page of ['visualizer.html', 'visualizer_brief.html', 'public/bf.html']) {
        const html = readFileSync(join(ROOT, page), 'utf8');
        assert.ok(!/fetch\(\s*['"`](codes|public)\//.test(html), `${page}: 상대 경로 fetch`);
        assert.ok(!/["'`]audio\.mp3/.test(html), `${page}: 상대 경로 오디오`);
    }
});
