// /api/github.js
export default async function handler(req, res) {
    // Vercel 환경변수에서 토큰 가져오기
    const token = process.env.GITHUB_TOKEN;

    if (!token) {
        return res.status(500).json({ error: "Server Configuration Error: Token not found" });
    }

    // 프론트엔드에서 보낸 요청 정보 받기
    const { endpoint, method = 'GET', body } = req.body;

    if (!endpoint) {
        return res.status(400).json({ error: "Endpoint is required" });
    }

    // --- 보안 로직 추가 ---
    const adminPassword = process.env.ADMIN_PASSWORD;
    const clientPassword = req.headers['x-admin-password']; // 클라이언트가 보낸 비밀번호

    // 1. GET 요청은 허용 (조회용)
    const isGet = method.toUpperCase() === 'GET';
    // 2. 구독하기 파일(receiver_email.json) 업데이트는 허용 (일반 사용자용)
    const isSubscriberUpdate = endpoint.includes('codes/receiver_email.json') && method.toUpperCase() === 'PUT';

    if (!isGet && !isSubscriberUpdate) {
        // 그 외 모든 수정/삭제/실행 요청은 비밀번호 확인 필수
        if (!clientPassword || clientPassword !== adminPassword) {
            return res.status(401).json({ 
                error: "Unauthorized", 
                message: "관리자 인증이 필요한 작업입니다. 비밀번호를 확인해주세요." 
            });
        }
    }
    // ----------------------

    try {
        const url = `https://api.github.com/${endpoint}`;
        
        const options = {
            method: method,
            headers: {
                "Authorization": `token ${token}`,
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(url, options);
        
        // 상태 코드가 204(No Content)인 경우 처리
        if (response.status === 204) {
             return res.status(204).end();
        }

        const data = await response.json().catch(() => ({})); // JSON 파싱 실패 시 빈 객체

        if (!response.ok) {
            return res.status(response.status).json(data);
        }

        return res.status(200).json(data);

    } catch (error) {
        console.error(error);
        return res.status(500).json({ error: "Internal Server Error" });
    }
}