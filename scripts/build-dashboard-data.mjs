// 대시보드 첫 화면용 데이터 (codes/dashboard/recent.json) — Vercel 배포 때마다 scripts/build-site.mjs 가 만듭니다.
//
// 예전에는 크롤링 워크플로우에서만 만들어 커밋했기 때문에, 크롤러를 로컬에서 돌려 데이터만 push 하면
// 대시보드 기본 화면이 예전 데이터를 보여줬습니다. (11/28 IITP 11/27 간행물 누락)
// 배포 직전에 그 커밋의 데이터로 만들면 데이터가 어떤 경로로 바뀌어도 항상 맞습니다.
//
//  - 기사: 최근 RECENT_DAYS 일 (+ 날짜 없는 항목). 전체(약 12MB)는 검색·'전체 기간 불러오기' 때 받음
//  - 간행물: 전부 (출처 8곳 합쳐 수백 KB). 몇 달에 한 번 올라오는 출처도 탭이 비지 않도록
//  - data_updated_at: 출처 데이터 파일이 마지막으로 바뀐 커밋 시각 (대시보드 '기사 업데이트')
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

export const RECENT_DAYS = 30;

function kstDateKey(date) {
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(date).map(part => [part.type, part.value]));
    return `${p.year}${p.month}${p.day}`;
}

function itemDateKey(item) {
    const year = String(item['년'] ?? '').trim();
    if (!year) return '';
    const pad = value => String(value ?? '').trim().padStart(2, '0');
    return `${year}${pad(item['월'])}${pad(item['일'])}`;
}

function lastDataCommit(root, files) {
    try {
        const out = execFileSync('git', ['log', '-1', '--format=%cI', '--', ...files], { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
        return out.trim() || null;
    } catch {
        return null;  // git 기록이 없는 환경 (대시보드는 public/update_time.json 으로 대신 표시)
    }
}

export function buildDashboardData({ root, now = new Date(), days = RECENT_DAYS }) {
    const { sources } = JSON.parse(readFileSync(join(root, 'config', 'sources.json'), 'utf8'));
    const cutoff = kstDateKey(new Date(now.getTime() - days * 86400000));
    const files = {};
    let total = 0;
    for (const source of sources) {
        let rows = [];
        try {
            rows = JSON.parse(readFileSync(join(root, 'codes', source.file), 'utf8'));
            if (!Array.isArray(rows)) rows = [];
        } catch (error) {
            console.warn(`⚠️ codes/${source.file} 읽기 실패 (${error.message}) - 빈 목록으로 둡니다.`);
        }
        files[source.file] = source.type === 'publication'
            ? rows
            : rows.filter(row => { const key = itemDateKey(row); return !key || key >= cutoff; });
        total += files[source.file].length;
    }
    return {
        payload: {
            generated_at: now.toISOString(),
            days,
            complete_types: ['publication'],
            data_updated_at: lastDataCommit(root, sources.map(source => `codes/${source.file}`)),
            files,
        },
        total,
    };
}
