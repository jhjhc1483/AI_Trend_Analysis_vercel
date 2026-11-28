// Vercel 배포 빌드 (vercel.json buildCommand) — 사이트에 필요한 파일만 dist/ 에 모읍니다.
//
// 허용 목록 방식: 아래에 적힌 것만 공개되고, 그 밖의 파일(파이썬 코드, codes/state 기록, 워크플로우,
// 테스트, 문서, 편집기 설정, 구독자 목록 등)은 사이트에 올라가지 않습니다.
// 새 페이지나 데이터 파일을 사이트에 내보내려면 여기에 추가하세요. (tests/js/build_site.test.mjs 가 확인)
//
// 출처별 수집 데이터는 config/sources.json 의 목록을 따르고,
// 대시보드 첫 화면 데이터(codes/dashboard/recent.json)도 여기서 만듭니다.
//
// 로컬 확인: node scripts/build-site.mjs  →  dist/ 를 정적 서버로 열기
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildDashboardData } from './build-dashboard-data.mjs';

// 페이지와 화면 코드
export const SITE_FILES = [
    'index.html', 'script.js', 'style.css',
    'visualizer.html',        // /report (동향 리포트)
    'visualizer_brief.html',  // /brief (공유용 브리핑)
    'subscribe.html',         // /subscribe (구독·해지·연장)
];
// 폴더째 공개
export const SITE_DIRS = [
    'public',            // 오디오·재생 페이지(/listen)·업데이트 시각·공유 썸네일
    'config',            // 출처 목록
    'codes/favorites',   // 오늘 일일 동향(⭐)·Few-shot·제외 목록
];
// 일일 동향 기록
export const DATA_FILES = ['codes/data.json', 'codes/data.txt'];

export function buildSite({ root, out, now = new Date() }) {
    rmSync(out, { recursive: true, force: true });
    mkdirSync(out, { recursive: true });

    const { sources } = JSON.parse(readFileSync(join(root, 'config', 'sources.json'), 'utf8'));
    const files = [...SITE_FILES, ...DATA_FILES, ...sources.map(source => `codes/${source.file}`)];
    for (const file of files) {
        const from = join(root, file);
        if (!existsSync(from)) throw new Error(`배포할 파일이 없습니다: ${file}`);
        mkdirSync(dirname(join(out, file)), { recursive: true });
        cpSync(from, join(out, file));
    }
    for (const dir of SITE_DIRS) cpSync(join(root, dir), join(out, dir), { recursive: true });

    const { payload, total } = buildDashboardData({ root, now });
    const recentPath = join(out, 'codes', 'dashboard', 'recent.json');
    mkdirSync(dirname(recentPath), { recursive: true });
    const text = JSON.stringify(payload);
    writeFileSync(recentPath, text);
    return { files: files.length, recent: total, recentBytes: Buffer.byteLength(text), dataUpdatedAt: payload.data_updated_at };
}

function main() {
    const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
    const result = buildSite({ root, out: join(root, 'dist') });
    console.log(`✅ dist/: 파일 ${result.files}개 + 폴더 ${SITE_DIRS.length}개, ` +
        `대시보드 데이터 ${result.recent}건 ${(result.recentBytes / 1e6).toFixed(2)}MB (데이터 커밋 ${result.dataUpdatedAt || '알 수 없음'})`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) main();
