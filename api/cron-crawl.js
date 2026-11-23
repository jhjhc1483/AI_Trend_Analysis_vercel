// /api/cron-crawl.js
// 매일 크롤링 시작 신호. Vercel Cron(vercel.json의 crons)이 정해진 시각에 이 주소를 호출하면
// GitHub Actions의 크롤링 워크플로우(main.yml)를 실행시킵니다.
// → 이어서 AI 자동 선정 → 오디오 → 메일이 자동으로 진행됩니다.
//
// GitHub 자체 예약(schedule)은 몇 시간씩 밀리거나 아예 건너뛰는 일이 있어서(11/24: 7시 40분까지 미실행)
// 시작 신호는 Vercel이 보내고, GitHub 예약은 예비용으로만 둡니다.
//
// 보안: 아무나 호출해 크롤링(ScraperAPI 크레딧 사용)을 돌리지 못하도록,
// Vercel 환경변수 CRON_SECRET이 있으면 Vercel Cron이 자동으로 보내는 'Authorization: Bearer <값>'이 맞을 때만 실행합니다.
// CRON_SECRET이 설정되지 않았으면 항상 거부합니다.
import { createHash, timingSafeEqual } from 'node:crypto';

const OWNER = process.env.GITHUB_OWNER || 'jhjhc1483';
const REPO = process.env.GITHUB_REPO || 'AI_Trend_Analysis_vercel';
const WORKFLOW = 'main.yml';

function isAuthorized(header) {
    const secret = process.env.CRON_SECRET;
    if (!secret || typeof header !== 'string') return false;
    const digest = (value) => createHash('sha256').update(value, 'utf8').digest();
    return timingSafeEqual(digest(header), digest(`Bearer ${secret}`));
}

export default async function handler(req, res) {
    if (!isAuthorized(req.headers.authorization)) {
        return res.status(401).json({ error: "Unauthorized" });
    }

    const token = process.env.GITHUB_TOKEN;
    if (!token) {
        return res.status(500).json({ error: "Server Configuration Error: GITHUB_TOKEN not found" });
    }

    try {
        const response = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
            method: 'POST',
            headers: {
                "Authorization": `token ${token}`,
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            // round 1 = 전체 수집 (2회차 예비 예약은 실패한 출처만 다시 수집)
            body: JSON.stringify({ ref: 'main', inputs: { round: '1' } }),
        });

        if (response.status === 204) {
            console.log(`Dispatched ${WORKFLOW}`);
            return res.status(200).json({ ok: true, dispatched: WORKFLOW });
        }
        const detail = await response.text().catch(() => '');
        console.error(`Dispatch failed (${response.status}): ${detail.slice(0, 300)}`);
        return res.status(502).json({ error: "Dispatch failed", status: response.status });
    } catch (error) {
        console.error("Cron crawl error:", error.message);
        return res.status(500).json({ error: "Internal Server Error" });
    }
}
