// /api/auth.js
// 대시보드 관리자 모드의 비밀번호를 확인합니다.
import { createHash, timingSafeEqual } from 'node:crypto';

// 응답 시간 차이로 비밀번호를 추측할 수 없도록 고정 길이 해시끼리 비교합니다. (api/github.js와 동일)
function isAdminPassword(input) {
    const expected = process.env.ADMIN_PASSWORD;
    if (!expected || typeof input !== 'string' || input.length === 0) return false;
    const digest = (value) => createHash('sha256').update(value, 'utf8').digest();
    return timingSafeEqual(digest(input), digest(expected));
}

export default async function handler(req, res) {
    // POST 요청만 허용
    if (req.method !== 'POST') {
        return res.status(405).json({ error: "Method Not Allowed" });
    }

    try {
        const { password } = req.body || {};

        // 환경변수 체크
        if (!process.env.ADMIN_PASSWORD) {
            console.error("ADMIN_PASSWORD is not set in environment variables.");
            return res.status(500).json({
                error: "Internal Server Error",
                message: "서버 설정에 비밀번호(ADMIN_PASSWORD)가 등록되지 않았습니다. Vercel 환경변수를 확인해주세요."
            });
        }

        if (!password) {
            return res.status(400).json({ error: "Bad Request", message: "비밀번호가 입력되지 않았습니다." });
        }

        if (isAdminPassword(password)) {
            return res.status(200).json({ success: true });
        }

        // 무차별 대입 공격을 늦추기 위한 지연 (1초)
        await new Promise(resolve => setTimeout(resolve, 1000));
        return res.status(401).json({ success: false, error: "Unauthorized", message: "비밀번호가 일치하지 않습니다." });
    } catch (error) {
        console.error("Auth API Error:", error);
        return res.status(500).json({ error: "Internal Server Error", message: error.message });
    }
}
