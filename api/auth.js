// /api/auth.js
export default async function handler(req, res) {
    // POST 요청만 허토
    if (req.method !== 'POST') {
        return res.status(405).json({ error: "Method Not Allowed" });
    }

    try {
        const { password } = req.body || {};
        const adminPassword = process.env.ADMIN_PASSWORD;

        // 환경변수 체크
        if (!adminPassword) {
            console.error("ADMIN_PASSWORD is not set in environment variables.");
            return res.status(500).json({
                error: "Internal Server Error",
                message: "서버 설정에 비밀번호(ADMIN_PASSWORD)가 등록되지 않았습니다. Vercel 환경변수를 확인해주세요."
            });
        }

        if (!password) {
            return res.status(400).json({ error: "Bad Request", message: "비밀번호가 입력되지 않았습니다." });
        }

        if (password === adminPassword) {
            return res.status(200).json({ success: true });
        } else {
            return res.status(401).json({ success: false, error: "Unauthorized", message: "비밀번호가 일치하지 않습니다." });
        }
    } catch (error) {
        console.error("Auth API Error:", error);
        return res.status(500).json({ error: "Internal Server Error", message: error.message });
    }
}
