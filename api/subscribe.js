// /api/subscribe.js
// 이메일 구독 신청/해지 API입니다.
// 브라우저는 이메일 한 건과 동작(subscribe/unsubscribe)만 보내고,
// 구독자 목록 파일(codes/receiver_email.json)은 서버에서만 읽고 씁니다.
//
// 목록은 SUBSCRIBER_ENCRYPTION_KEY 환경변수로 암호화해 저장합니다.
// 암호화 형식은 codes/pycode/subscribers.py 와 반드시 같아야 합니다.
//   {"v": 1, "enc": "aes-256-gcm", "iv": "<base64 12바이트>", "data": "<base64 암호문+인증태그 16바이트>"}
//   키 = SHA-256(SUBSCRIBER_ENCRYPTION_KEY 앞뒤 공백 제거)
// 키가 설정되지 않은 동안에는 기존과 같은 평문 형식({"emails": [...]})으로 저장합니다.
//
// 메일 속 '구독 해지' / '1년 연장' 링크에는 받은 사람만 가진 토큰이 들어갑니다.
//   토큰 = base64url(HMAC-SHA256(SHA-256("token:" + 키), "<용도>:<이메일 소문자>"))   용도: unsubscribe | renew
//   (codes/pycode/subscribers.py 의 make_token 과 같아야 함)
// 메일 앱의 '구독 취소' 버튼(RFC 8058 원클릭)은 주소창의 쿼리로 같은 값을 보내므로 쿼리도 함께 읽습니다.
import { createCipheriv, createDecipheriv, createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto';

const OWNER = process.env.GITHUB_OWNER || 'jhjhc1483';
const REPO = process.env.GITHUB_REPO || 'AI_Trend_Analysis_vercel';
const BRANCH = 'main';
const FILE_PATH = 'codes/receiver_email.json';

const MAX_SUBSCRIBERS = 100;   // gmail_send_visualizer.py 의 발송 상한과 같게 유지
const EXPIRE_DAYS = 365;       // 등록 후 1년이 지나면 만료
// 발송 스크립트(codes/pycode/subscribers.py)와 같은 규칙으로 검사해야 등록 후 발송에서 빠지는 일이 없습니다.
const EMAIL_REGEX = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
const MAX_ATTEMPTS = 3;        // 다른 요청과 동시에 저장이 겹쳤을 때 재시도 횟수

const KEY_ENV = 'SUBSCRIBER_ENCRYPTION_KEY';
const MIN_KEY_LENGTH = 32;
const ENC_ALG = 'aes-256-gcm';
const IV_BYTES = 12;
const TAG_BYTES = 16;

const MESSAGES = {
    subscribed: "성공적으로 구독되었습니다! 🎉",
    already: "이미 등록된 이메일입니다.",
    full: "구독 정원이 가득 찼습니다. 관리자에게 문의해주세요.",
    unsubscribed: "구독이 해지되었습니다. 😢",
    not_found: "등록되지 않은 이메일입니다.",
    bad_token: "링크가 올바르지 않거나 만료되었습니다. 메일에 있는 링크를 다시 눌러주세요.",
};
const ACTIONS = ['subscribe', 'unsubscribe', 'renew'];

class HttpError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
    }
}

// ---------------- 암호화 ----------------

function getPassphrase() {
    const passphrase = (process.env[KEY_ENV] || '').trim();
    if (!passphrase) return null;
    if (passphrase.length < MIN_KEY_LENGTH) {
        throw new HttpError(500, `서버 설정 오류: ${KEY_ENV}는 ${MIN_KEY_LENGTH}자 이상이어야 합니다.`);
    }
    return passphrase;
}

function getKey() {
    const passphrase = getPassphrase();
    return passphrase ? createHash('sha256').update(passphrase, 'utf8').digest() : null;
}

// ---------------- 해지/연장 링크 토큰 ----------------

function makeToken(purpose, email) {
    const passphrase = getPassphrase();
    if (!passphrase) throw new HttpError(500, `서버 설정 오류: 링크를 확인할 ${KEY_ENV}가 없습니다.`);
    const tokenKey = createHash('sha256').update(`token:${passphrase}`, 'utf8').digest();
    return createHmac('sha256', tokenKey).update(`${purpose}:${email}`, 'utf8').digest('base64url');
}

function isValidToken(purpose, email, token) {
    if (typeof token !== 'string' || !token) return false;
    const expected = Buffer.from(makeToken(purpose, email));
    const received = Buffer.from(token);
    return expected.length === received.length && timingSafeEqual(expected, received);
}

function encrypt(plaintext, key) {
    const iv = randomBytes(IV_BYTES);
    const cipher = createCipheriv(ENC_ALG, key, iv);
    const data = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final(), cipher.getAuthTag()]);
    return { v: 1, enc: ENC_ALG, iv: iv.toString('base64'), data: data.toString('base64') };
}

function decrypt(doc, key) {
    const iv = Buffer.from(doc.iv, 'base64');
    const data = Buffer.from(doc.data, 'base64');
    const decipher = createDecipheriv(ENC_ALG, key, iv);
    decipher.setAuthTag(data.subarray(data.length - TAG_BYTES));
    return Buffer.concat([decipher.update(data.subarray(0, data.length - TAG_BYTES)), decipher.final()]).toString('utf8');
}

// ---------------- 구독자 목록 형식 ----------------

// 파일 내용(문자열) → 정리 전 구독자 배열
function parseSubscriberFile(text) {
    let doc = JSON.parse(text);
    if (doc && doc.enc === ENC_ALG) {
        const key = getKey();
        if (!key) throw new HttpError(500, `서버 설정 오류: 암호화된 구독자 목록을 읽을 ${KEY_ENV}가 없습니다.`);
        try {
            doc = JSON.parse(decrypt(doc, key));
        } catch (e) {
            throw new HttpError(500, `서버 설정 오류: 구독자 목록을 복호화하지 못했습니다. (Vercel과 GitHub의 ${KEY_ENV} 값이 같은지 확인하세요)`);
        }
    }
    return Array.isArray(doc) ? doc : (doc && doc.emails) || [];
}

// 구독자 배열 → 저장할 파일 내용(문자열). 키가 있으면 암호화합니다.
function serializeSubscriberFile(subscribers) {
    const payload = { emails: subscribers };
    const key = getKey();
    return JSON.stringify(key ? encrypt(JSON.stringify(payload), key) : payload, null, 2) + '\n';
}

function todayKST() {
    return new Date(Date.now() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

function addDays(dateStr, days) {
    return new Date(Date.parse(dateStr) + days * 86400000).toISOString().slice(0, 10);
}

// 옛 형식(문자열) 변환, 잘못된 주소와 만료된 구독 제거 (subscribers.py 의 clean_subscribers 와 같은 규칙)
function cleanSubscribers(raw, today) {
    const todayTime = Date.parse(today);
    const valid = [];
    for (const item of raw) {
        const entry = typeof item === 'string' ? { email: item, date: today } : item;
        if (!entry || typeof entry.email !== 'string') continue;
        const email = entry.email.replace(/[\x00-\x1f\x7f]/g, '').trim();
        if (!EMAIL_REGEX.test(email)) continue;
        const date = typeof entry.date === 'string' && entry.date ? entry.date : today;
        const regTime = Date.parse(date);
        if (!Number.isNaN(regTime) && (todayTime - regTime) / 86400000 >= EXPIRE_DAYS) continue;
        valid.push({ email, date });
    }
    return valid;
}

// ---------------- GitHub 파일 읽기/쓰기 ----------------

function githubRequest(token, method, body) {
    const query = method === 'GET' ? `?ref=${BRANCH}` : '';
    return fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}${query}`, {
        method,
        headers: {
            "Authorization": `token ${token}`,
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        },
        ...(body && { body: JSON.stringify(body) }),
    });
}

async function readSubscribers(token) {
    const res = await githubRequest(token, 'GET');
    if (res.status === 404) return { raw: [], sha: null };
    if (!res.ok) throw new HttpError(502, `구독자 목록을 불러오지 못했습니다. (GitHub ${res.status})`);
    const data = await res.json();
    const text = Buffer.from(data.content || '', 'base64').toString('utf8');
    return { raw: text.trim() ? parseSubscriberFile(text) : [], sha: data.sha };
}

// 저장에 성공하면 true, 다른 요청이 먼저 파일을 바꿔 충돌하면 false
async function writeSubscribers(token, subscribers, sha) {
    const res = await githubRequest(token, 'PUT', {
        message: "Update subscriber list",   // 공개 저장소이므로 커밋 메시지에 이메일을 남기지 않습니다.
        content: Buffer.from(serializeSubscriberFile(subscribers), 'utf8').toString('base64'),
        branch: BRANCH,
        ...(sha && { sha }),
    });
    if (res.status === 409 || res.status === 422) return false;
    if (!res.ok) throw new HttpError(502, `구독자 목록을 저장하지 못했습니다. (GitHub ${res.status})`);
    return true;
}

// ---------------- 핸들러 ----------------

export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: "Method Not Allowed" });
    }

    const githubToken = process.env.GITHUB_TOKEN;
    if (!githubToken) {
        return res.status(500).json({ error: "Server Configuration Error", message: "서버 설정 오류: GITHUB_TOKEN이 없습니다." });
    }

    // 본문(JSON) 또는 주소 쿼리(메일 앱의 원클릭 구독 취소)에서 값을 읽습니다.
    const body = req.body && typeof req.body === 'object' ? req.body : {};
    const query = req.query || {};
    const pick = (key) => (typeof body[key] === 'string' ? body[key] : typeof query[key] === 'string' ? query[key] : undefined);
    const email = pick('email');
    const action = pick('action');
    const token = pick('token');

    if (!ACTIONS.includes(action)) {
        return res.status(400).json({ error: "Bad Request", message: "알 수 없는 요청입니다." });
    }
    const target = typeof email === 'string' ? email.trim().toLowerCase() : '';
    if (target.length > 254 || !EMAIL_REGEX.test(target)) {
        return res.status(400).json({ error: "Bad Request", message: "유효한 이메일을 입력해주세요." });
    }

    try {
        // 연장은 메일 링크로만 가능, 해지는 링크(토큰)가 있으면 검증하고 없으면 기존처럼 이메일만으로 처리
        if ((action === 'renew' || token !== undefined) && !isValidToken(action, target, token)) {
            return res.status(403).json({ status: 'bad_token', message: MESSAGES.bad_token });
        }

        for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            const today = todayKST();
            const { raw, sha } = await readSubscribers(githubToken);
            const subscribers = cleanSubscribers(raw, today);
            const exists = subscribers.some(s => s.email.toLowerCase() === target);

            let next, status, message;
            if (action === 'subscribe') {
                if (exists) return res.status(200).json({ status: 'already', message: MESSAGES.already });
                if (subscribers.length >= MAX_SUBSCRIBERS) return res.status(409).json({ status: 'full', message: MESSAGES.full });
                next = [...subscribers, { email: target, date: today }];
                status = 'subscribed';
            } else if (action === 'unsubscribe') {
                if (!exists) return res.status(200).json({ status: 'not_found', message: MESSAGES.not_found });
                next = subscribers.filter(s => s.email.toLowerCase() !== target);
                status = 'unsubscribed';
            } else {
                if (!exists) return res.status(200).json({ status: 'not_found', message: "구독 정보가 없습니다. 이미 만료되었다면 다시 구독해주세요." });
                next = subscribers.map(s => (s.email.toLowerCase() === target ? { email: s.email, date: today } : s));
                status = 'renewed';
                message = `구독이 1년 연장되었습니다. 🎉 (새 만료일: ${addDays(today, EXPIRE_DAYS)})`;
            }

            if (await writeSubscribers(githubToken, next, sha)) {
                return res.status(200).json({ status, message: message || MESSAGES[status] });
            }
        }
        return res.status(503).json({ error: "Conflict", message: "다른 요청과 겹쳤습니다. 잠시 후 다시 시도해주세요." });
    } catch (error) {
        console.error("Subscribe API Error:", error.message);
        if (error instanceof HttpError) {
            return res.status(error.status).json({ error: "Subscribe Error", message: error.message });
        }
        return res.status(500).json({ error: "Internal Server Error", message: "처리 중 오류가 발생했습니다." });
    }
}
