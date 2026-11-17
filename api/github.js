// /api/github.js
// 대시보드(script.js)가 GitHub API를 호출할 때 거치는 프록시입니다.
// GitHub 토큰은 서버에만 있으므로, 아래 ROUTES 허용 목록에 있는 요청만 대신 보내 줍니다.
// 목록에 없는 주소나 메서드는 비밀번호와 관계없이 모두 거부합니다.
import { createHash, timingSafeEqual } from 'node:crypto';

const OWNER = process.env.GITHUB_OWNER || 'jhjhc1483';
const REPO = process.env.GITHUB_REPO || 'AI_Trend_Analysis_vercel';
const REPO_PREFIX = `repos/${OWNER}/${REPO}/`;

// access: 'public' = 누구나 가능, 'admin' = 관리자 비밀번호 필요
const ROUTES = [
    {
        // 즐겨찾기 / Few-shot 학습 데이터 / 일일동향 제외 목록
        pattern: /^contents\/codes\/favorites\/(favorite_articles|favorite_publications|fewshot_examples|excluded_articles)\.json(\?ref=main)?$/,
        methods: { GET: 'public', PUT: 'admin' },
    },
    {
        // 워크플로우 수동 실행 (기사 업데이트, AI 자동 선정, 텍스트 변환, 오디오 생성)
        pattern: /^actions\/workflows\/(main|auto_favorites|json_to_txt|audio_gen)\.yml\/dispatches$/,
        methods: { POST: 'admin' },
    },
    {
        // 데이터 전체 삭제 - 파일 목록 조회
        pattern: /^contents\/codes(\?ref=main)?$/,
        methods: { GET: 'admin' },
    },
    {
        // 데이터 전체 삭제 - 개별 파일 삭제 (구독자 목록은 삭제 불가)
        pattern: /^contents\/codes\/(?!receiver_email\.json$)[A-Za-z0-9_-]+\.(json|txt)$/,
        methods: { DELETE: 'admin' },
    },
];

// 요청이 허용 목록에 있으면 'public' 또는 'admin'을, 없으면 null을 반환합니다.
function findAccess(endpoint, method) {
    if (typeof endpoint !== 'string' || !endpoint.startsWith(REPO_PREFIX)) return null;
    const path = endpoint.slice(REPO_PREFIX.length);
    const route = ROUTES.find(r => r.pattern.test(path));
    return (route && route.methods[method]) || null;
}

// 응답 시간 차이로 비밀번호를 추측할 수 없도록 고정 길이 해시끼리 비교합니다. (api/auth.js와 동일)
function isAdminPassword(input) {
    const expected = process.env.ADMIN_PASSWORD;
    if (!expected || typeof input !== 'string' || input.length === 0) return false;
    const digest = (value) => createHash('sha256').update(value, 'utf8').digest();
    return timingSafeEqual(digest(input), digest(expected));
}

export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: "Method Not Allowed" });
    }

    const token = process.env.GITHUB_TOKEN;
    if (!token) {
        return res.status(500).json({ error: "Server Configuration Error: Token not found" });
    }

    // 프론트엔드에서 보낸 요청 정보 받기
    const { endpoint, method = 'GET', body } = req.body || {};
    const upperMethod = String(method).toUpperCase();

    const access = findAccess(endpoint, upperMethod);
    if (!access) {
        return res.status(403).json({ error: "Forbidden", message: "허용되지 않은 요청입니다." });
    }

    if (access === 'admin' && !isAdminPassword(req.headers['x-admin-password'])) {
        return res.status(401).json({
            error: "Unauthorized",
            message: "관리자 인증이 필요한 작업입니다. 비밀번호를 확인해주세요."
        });
    }

    try {
        const options = {
            method: upperMethod,
            headers: {
                "Authorization": `token ${token}`,
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
        };
        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`https://api.github.com/${endpoint}`, options);

        // 상태 코드가 204(No Content)인 경우 처리 (워크플로우 실행 요청 성공 시)
        if (response.status === 204) {
            return res.status(204).end();
        }

        const data = await response.json().catch(() => ({})); // JSON 파싱 실패 시 빈 객체
        return res.status(response.ok ? 200 : response.status).json(data);

    } catch (error) {
        console.error(error);
        return res.status(500).json({ error: "Internal Server Error" });
    }
}
