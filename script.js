'use strict';
// =====================================================
// 대시보드 (index.html)
//
//  - 출처 목록: config/sources.json (크롤러·AI 선정과 같은 파일)
//  - 기사/간행물: 첫 화면은 codes/dashboard/recent.json(최근 30일), 검색·'전체 기간'은 출처별 전체 파일
//  - ⭐ 오늘 일일 동향: codes/favorites/favorite_*.json 이 기준.
//    고친 내용은 '일일 동향 저장' 전까지 이 브라우저(localStorage)에만 임시로 남고,
//    서버 목록이 바뀌면(새 AI 선정 등) 새 목록으로 바뀝니다.
//  - 관리자 작업은 /api/github(허용 목록 프록시)로 GitHub에 저장하거나 워크플로우를 실행합니다.
// =====================================================

// -----------------------------------------------------
// 1. 설정
// -----------------------------------------------------
const OWNER = "jhjhc1483";
const REPO = "AI_Trend_Analysis_vercel";
const BRANCH = "main";
const REPO_API = `repos/${OWNER}/${REPO}`;

const SOURCES_URL = 'config/sources.json';
const RECENT_DATA_URL = 'codes/dashboard/recent.json';
const REPORT_URL = 'codes/data.txt';
const UPDATE_TIME_URL = 'public/update_time.json';
const AUDIO_URL = 'public/audio.mp3';
const FAVORITE_FILES = {
    article: 'codes/favorites/favorite_articles.json',
    publication: 'codes/favorites/favorite_publications.json',
};
const FEWSHOT_FILE = 'codes/favorites/fewshot_examples.json';
const EXCLUDED_FILE = 'codes/favorites/excluded_articles.json';

const ARTICLE = 'article';
const PUBLICATION = 'publication';
const TYPES = [ARTICLE, PUBLICATION];
const CATEGORIES = ["국방", "육군", "민간", "기관", "해외", "기타"];
const PUBLICATION_CATEGORY = "간행물";
const CATEGORY_CLASS = { 국방: 'cat-defense', 육군: 'cat-army', 민간: 'cat-civil', 기관: 'cat-pub', 해외: 'cat-foreign', 기타: 'cat-etc' };

const PAGE_SIZE = 300;          // 목록을 한 번에 그리는 개수 ('더 보기'로 이어서 표시)
const DRAFT_KEY = 'favoritesDraft.v2';
const LEGACY_FAVORITE_KEYS = ['favoriteArticles', 'favoritePublications'];  // 예전 형식 (브라우저별 즐겨찾기)
const THEME_KEY = 'ai-trend-theme';  // visualizer.html 과 같은 키

// 대시보드 '오늘 자동 처리 현황'에 보여줄 단계 (.github/workflows/<workflow>.yml)
const PIPELINE = [
    { workflow: 'main', label: '기사 수집' },
    { workflow: 'auto_favorites', label: 'AI 선정' },
    { workflow: 'audio_gen', label: '브리핑 오디오' },
    { workflow: 'kakao_or_gmail_send', label: '구독자 메일' },
];
// 관리자가 직접 실행할 수 있는 워크플로우 (api/github.js 허용 목록과 같아야 함)
const WORKFLOWS = {
    main: {
        label: '기사 수집',
        confirm: '기사를 다시 수집할까요? (5분 이상 걸립니다)\n\n오늘 일일 동향이 아직 없으면 AI 선정 → 오디오 → 메일까지 이어서 자동으로 진행됩니다.',
    },
    auto_favorites: {
        label: 'AI 일일 동향 선정',
        confirm: 'AI가 어제 기사로 오늘 일일 동향을 다시 고릅니다. (약 2~5분)\n\n지금 ⭐ 목록(사람이 고친 내용 포함)은 새 결과로 바뀌고, 브리핑 오디오도 다시 만들어집니다.',
    },
    json_to_txt: {
        label: '일일 동향 텍스트 만들기',
        confirm: '지금 ⭐ 목록으로 일일 동향 텍스트를 다시 만듭니다. (약 30초)',
    },
    audio_gen: {
        label: '브리핑 오디오 만들기',
        confirm: '지금 일일 동향으로 브리핑 대본과 오디오를 다시 만듭니다. (약 1~2분)',
    },
};
const POLL_ACTIVE_MS = 15000;   // 진행 중인 단계가 있을 때 상태 확인 간격
const WATCH_AFTER_MS = 90000;   // 실행 요청·완료 후 이어지는 단계를 기다리는 시간

const state = {
    sources: [],
    sourceById: new Map(),
    items: { article: [], publication: [] },
    linkIndex: new Map(),       // 링크 → 기사/간행물
    dataScope: 'none',          // 'recent' (최근 N일) | 'all' (전체 기간)
    recentDays: 30,
    fullDataPromise: null,
    view: 'HOME',
    renderLimit: PAGE_SIZE,
    renderedItems: new Map(),   // 지금 화면 목록의 링크 → 항목 (버튼 처리용)
    search: { article: '', publication: '' },
    sort: { article: 'date_desc', publication: 'date_desc' },
    favorites: { article: new Map(), publication: new Map() },   // 지금 ⭐ 목록 (링크 → 항목)
    serverFavorites: { article: [], publication: [] },           // 기준이 되는 서버 목록
    draftMeta: { base: '', saved: null, savedKey: '' },
    fewshot: [],
    excluded: new Set(),
    admin: { enabled: false, password: '' },
    pipeline: {},               // workflow → 최근 실행 (null = 기록 없음, undefined = 확인 실패)
    watches: new Map(),         // 실행을 요청한 workflow → { since }
    watchUntil: 0,
    pollTimer: null,
};

// -----------------------------------------------------
// 2. 공통 함수
// -----------------------------------------------------
function escapeHTML(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// 수집한 링크는 외부 사이트 값이므로 http(s) 주소만 링크로 씁니다.
function safeUrl(url) {
    return typeof url === 'string' && /^https?:\/\//i.test(url.trim()) ? url.trim() : '#';
}

function withCacheBust(url) {
    return `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`;
}

async function fetchJSON(url, fallback) {
    try {
        const res = await fetch(withCacheBust(url));
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    } catch (error) {
        if (fallback !== undefined) {
            console.warn(`${url} 을(를) 불러오지 못했습니다:`, error);
            return fallback;
        }
        throw error;
    }
}

function storageGet(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
}
function storageSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* 사생활 보호 모드 등 */ }
}
function storageRemove(key) {
    try { localStorage.removeItem(key); } catch (e) { /* 무시 */ }
}

function base64ToUtf8(base64) {
    const binary = atob(base64.replace(/\n/g, ""));
    const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
}
function utf8ToBase64(text) {
    const bytes = new TextEncoder().encode(text);
    let binary = '';
    for (let i = 0; i < bytes.length; i += 0x8000) {
        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    return btoa(binary);
}

// 짧은 문자열 해시 (FNV-1a) — ⭐ 목록 버전 비교용
function hashString(text) {
    let hash = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) {
        hash ^= text.charCodeAt(i);
        hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0).toString(36);
}

function pad2(value) {
    return String(value ?? '').trim().padStart(2, '0');
}

const KST_PARTS = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});
function kstParts(date) {
    const parts = {};
    KST_PARTS.formatToParts(date).forEach(p => { parts[p.type] = p.value; });
    return parts;
}
function todayKstKey() {
    const p = kstParts(new Date());
    return `${p.year.slice(2)}.${p.month}.${p.day}`;  // data.txt 날짜 형식 (예: 26.11.28)
}

async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    area.remove();
    if (!ok) throw new Error('클립보드에 복사할 수 없습니다.');
}

function debounce(func, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => func(...args), delay);
    };
}

// -----------------------------------------------------
// 3. 알림(토스트) · 대화상자
// -----------------------------------------------------
function toast(message, { type = 'info', timeout = 5000, action } = {}) {
    const root = document.getElementById('toast-root');
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');

    const text = document.createElement('span');
    text.className = 'toast-text';
    text.textContent = message;
    el.appendChild(text);

    let timer = null;
    const dismiss = () => {
        clearTimeout(timer);
        el.classList.add('leaving');
        setTimeout(() => el.remove(), 200);
    };
    if (action) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'toast-action';
        btn.textContent = action.label;
        btn.addEventListener('click', () => { dismiss(); action.onClick(); });
        el.appendChild(btn);
    }
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast-close';
    close.setAttribute('aria-label', '닫기');
    close.textContent = '×';
    close.addEventListener('click', dismiss);
    el.appendChild(close);

    root.appendChild(el);
    if (timeout) timer = setTimeout(dismiss, timeout);
    return dismiss;
}

// <dialog> 기반 입력창. 확인하면 FormData, 취소하면 null 을 돌려줍니다.
// body 는 HTML 문자열이므로 넣는 값은 반드시 escapeHTML 을 거쳐야 합니다.
function openDialog({ title, body = '', confirmText = '확인', cancelText = '취소', danger = false }) {
    const dialog = document.getElementById('dialog');
    if (typeof dialog.showModal !== 'function') {
        // <dialog> 를 지원하지 않는 아주 오래된 브라우저
        return Promise.resolve(window.confirm(title) ? new FormData() : null);
    }
    // 확인 버튼을 먼저 두어 Enter 키가 확인으로 동작하게 함 (화면에는 CSS로 오른쪽에 배치)
    dialog.innerHTML = `
        <form method="dialog" class="dialog-form">
            <h3 class="dialog-title">${escapeHTML(title)}</h3>
            <div class="dialog-body">${body}</div>
            <div class="dialog-actions">
                <button type="submit" value="ok" class="btn ${danger ? 'danger' : 'primary'}">${escapeHTML(confirmText)}</button>
                ${cancelText ? `<button type="submit" value="cancel" class="btn" formnovalidate>${escapeHTML(cancelText)}</button>` : ''}
            </div>
        </form>`;
    const form = dialog.querySelector('form');
    return new Promise(resolve => {
        dialog.addEventListener('close', () => {
            resolve(dialog.returnValue === 'ok' ? new FormData(form) : null);
        }, { once: true });
        dialog.returnValue = '';
        dialog.showModal();
        const focusTarget = dialog.querySelector('input[type=password], input[type=text], textarea, input[type=radio]');
        if (focusTarget) focusTarget.focus();
    });
}

async function confirmDialog(title, message, options = {}) {
    const body = `<p class="dialog-message">${escapeHTML(message)}</p>`;
    return (await openDialog({ title, body, ...options })) !== null;
}

function categoryChips(selected) {
    return `<div class="chip-group" role="radiogroup" aria-label="분류">${CATEGORIES.map(category => `
        <label class="chip ${CATEGORY_CLASS[category]}">
            <input type="radio" name="category" value="${escapeHTML(category)}" ${category === selected ? 'checked' : ''} required>
            <span>${escapeHTML(category)}</span>
        </label>`).join('')}</div>`;
}

function itemSummaryHTML(item) {
    return `<p class="dialog-item"><strong>${escapeHTML(item.title)}</strong><br><span>${escapeHTML(item.displayName || '')}</span></p>`;
}

async function pickCategory(item, title, selected = '') {
    const data = await openDialog({
        title,
        body: `${itemSummaryHTML(item)}<div class="field-label">분류</div>${categoryChips(selected)}`,
        confirmText: '확인',
    });
    return data ? String(data.get('category') || '') : null;
}

// 버튼을 잠시 비활성화하고 작업 중 표시
async function withBusy(button, task) {
    if (!button) return task();
    const original = button.textContent;
    button.disabled = true;
    button.classList.add('is-busy');
    try {
        return await task();
    } finally {
        button.disabled = false;
        button.classList.remove('is-busy');
        if (button.isConnected) button.textContent = original;
    }
}

// -----------------------------------------------------
// 4. 서버 API (관리자 인증, GitHub 프록시)
// -----------------------------------------------------
async function callProxyAPI(endpoint, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.admin.password) headers['x-admin-password'] = state.admin.password;
    const res = await fetch('/api/github', {
        method: 'POST',  // 프록시에는 항상 POST로 전달하고, 실제 GitHub 메서드는 body에 담음
        headers,
        body: JSON.stringify({ endpoint, method, body }),
    });
    if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const error = new Error(errData.message || `HTTP Error ${res.status}`);
        error.status = res.status;
        throw error;
    }
    if (res.status === 204) return null;
    return res.json();
}

async function ensureAdmin() {
    if (state.admin.enabled) return true;
    const data = await openDialog({
        title: '🔒 관리자 로그인',
        body: `<label class="field">비밀번호
            <input type="password" name="password" required autocomplete="current-password">
        </label>`,
        confirmText: '로그인',
    });
    if (!data) return false;
    const password = String(data.get('password') || '');
    try {
        const res = await fetch('/api/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password }),
        });
        const result = await res.json().catch(() => ({}));
        if (res.ok && result.success) {
            setAdmin(true, password);
            toast('관리자 모드가 켜졌습니다. 🧠·🚫 버튼과 관리자 작업을 쓸 수 있습니다.', { type: 'success' });
            return true;
        }
        toast(result.message || '비밀번호가 틀렸습니다.', { type: 'error' });
    } catch (error) {
        toast('비밀번호 확인 중 오류가 발생했습니다.', { type: 'error' });
    }
    return false;
}

function setAdmin(enabled, password = '') {
    state.admin = { enabled, password: enabled ? password : '' };
    document.body.classList.toggle('is-admin', enabled);
    const btn = document.getElementById('adminModeBtn');
    btn.textContent = enabled ? '🔓 관리자' : '🔒 관리자';
    btn.title = enabled ? '관리자 모드 켜짐 (누르면 잠금)' : '관리자 모드 (비밀번호 필요)';
    btn.setAttribute('aria-pressed', String(enabled));
    renderCurrentView();
}

// GitHub 저장소의 JSON 목록 파일을 읽고 고쳐서 저장합니다. (sha 로 다른 저장과의 충돌 방지)
// mutate(현재 목록) 가 null 을 돌려주면 저장하지 않습니다.
async function readRepoJSON(path) {
    try {
        const res = await callProxyAPI(`${REPO_API}/contents/${path}?ref=${BRANCH}`, 'GET');
        const parsed = res && res.content ? JSON.parse(base64ToUtf8(res.content)) : [];
        return { data: Array.isArray(parsed) ? parsed : [], sha: res ? res.sha : null };
    } catch (error) {
        if (error.status === 404) return { data: [], sha: null };  // 아직 파일이 없음
        throw error;
    }
}

async function writeRepoJSON(path, data, sha, message) {
    await callProxyAPI(`${REPO_API}/contents/${path}`, 'PUT', {
        message,
        content: utf8ToBase64(JSON.stringify(data, null, 2)),
        branch: BRANCH,
        ...(sha && { sha }),
    });
}

async function updateRepoJSON(path, mutate, message) {
    const { data, sha } = await readRepoJSON(path);
    const next = mutate(data);
    if (next === null) return null;
    await writeRepoJSON(path, next, sha, message);
    return next;
}

// -----------------------------------------------------
// 5. 출처 · 기사/간행물 데이터
// -----------------------------------------------------
function navLabel(source) {
    return source.type === PUBLICATION ? `${source.name}(${source.full_name})` : source.name;
}

async function loadSources() {
    const data = await fetchJSON(SOURCES_URL);
    state.sources = data.sources || [];
    state.sourceById = new Map(state.sources.map(source => [source.id, source]));
    TYPES.forEach(type => {
        document.getElementById(`nav-${type}-sources`).innerHTML = state.sources
            .filter(source => source.type === type)
            .map(source => `<a href="#${encodeURIComponent(source.id)}" class="nav-link" data-view="${escapeHTML(source.id)}">${escapeHTML(navLabel(source))}</a>`)
            .join('');
    });
}

function dateKeyOf(row) {
    return `${row.년 || '0000'}${pad2(row.월 || '00')}${pad2(row.일 || '00')}${pad2(row.시 || '00')}${pad2(row.분 || '00')}`;
}

function toItems(source, rows) {
    return (Array.isArray(rows) ? rows : []).map(row => ({
        ...row,
        site: source.id,
        type: source.type,
        displayName: source.name,
        title: row.기사명 || row.제목 || '제목 없음',
        link: row.링크 || row.link || '#',
        category: row.분류 || row.category || '',
        dateKey: dateKeyOf(row),
    }));
}

function setLoadedData(itemsPerSource, scope) {
    state.items = { article: [], publication: [] };
    state.linkIndex = new Map();
    state.sources.forEach((source, i) => {
        const list = itemsPerSource[i] || [];
        state.items[source.type] = state.items[source.type].concat(list);
        list.forEach(item => {
            if (item.link && item.link !== '#' && !state.linkIndex.has(item.link)) state.linkIndex.set(item.link, item);
        });
    });
    state.dataScope = scope;
}

async function loadRecentOrAllData() {
    try {
        const res = await fetch(withCacheBust(RECENT_DATA_URL));
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const recent = await res.json();
        state.recentDays = recent.days || state.recentDays;
        setLoadedData(state.sources.map(source => toItems(source, (recent.files || {})[source.file])), 'recent');
    } catch (error) {
        console.warn('최근 데이터 파일을 불러오지 못해 전체 데이터를 불러옵니다:', error);
        await loadAllData();
    }
}

// 전체 기간 데이터 (한 번만 받아서 재사용)
function loadAllData() {
    if (!state.fullDataPromise) {
        state.fullDataPromise = Promise.all(state.sources.map(source =>
            fetchJSON(`codes/${source.file}`, []).then(rows => toItems(source, rows))
        )).then(lists => setLoadedData(lists, 'all'));
    }
    return state.fullDataPromise;
}

function loadAllDataAndRender(loadingMessage) {
    updateDataScopeNotice(loadingMessage);
    return loadAllData().then(renderCurrentView);
}

// -----------------------------------------------------
// 6. ⭐ 오늘 일일 동향 (서버 목록 + 저장 전 임시 변경)
// -----------------------------------------------------
function normalizeFavoriteList(list, type) {
    return (Array.isArray(list) ? list : [])
        .filter(item => item && item.link)
        .map(item => ({ ...item, category: item.category || (type === PUBLICATION ? PUBLICATION_CATEGORY : '기타') }));
}

function currentLists() {
    return {
        article: Array.from(state.favorites.article.values()),
        publication: Array.from(state.favorites.publication.values()),
    };
}

function listSignature(list) {
    return list.map(item => `${item.link}\u0001${item.category}`).sort().join('\u0002');
}
function favoritesKey(lists) {
    return hashString(TYPES.map(type => listSignature(lists[type] || [])).join('\u0003'));
}

function setFavoriteMaps(lists) {
    TYPES.forEach(type => {
        state.favorites[type] = new Map((lists[type] || []).map(item => [item.link, { ...item }]));
    });
}

function cloneLists(lists) {
    return { article: (lists.article || []).map(i => ({ ...i })), publication: (lists.publication || []).map(i => ({ ...i })) };
}

function readDraft() {
    try {
        const draft = JSON.parse(storageGet(DRAFT_KEY) || 'null');
        return draft && draft.v === 2 && draft.lists ? draft : null;
    } catch (e) {
        return null;
    }
}

function favoritesChanges() {
    const changes = { added: 0, removed: 0, changed: 0, total: 0 };
    TYPES.forEach(type => {
        const server = new Map(state.serverFavorites[type].map(item => [item.link, item]));
        state.favorites[type].forEach((item, link) => {
            if (!server.has(link)) changes.added++;
            else if (server.get(link).category !== item.category) changes.changed++;
        });
        server.forEach((item, link) => { if (!state.favorites[type].has(link)) changes.removed++; });
    });
    changes.total = changes.added + changes.removed + changes.changed;
    return changes;
}

// 저장 전 변경(또는 저장했지만 아직 사이트에 반영되지 않은 목록)을 브라우저에 남김
function persistDraft() {
    const { saved, savedKey, base } = state.draftMeta;
    if (favoritesChanges().total === 0 && !saved) {
        storageRemove(DRAFT_KEY);
        return;
    }
    storageSet(DRAFT_KEY, JSON.stringify({ v: 2, base, saved, savedKey, lists: currentLists(), updatedAt: Date.now() }));
}

async function loadFavorites() {
    LEGACY_FAVORITE_KEYS.forEach(storageRemove);
    const [articles, publications] = await Promise.all([
        fetchJSON(FAVORITE_FILES.article, []),
        fetchJSON(FAVORITE_FILES.publication, []),
    ]);
    const server = { article: normalizeFavoriteList(articles, ARTICLE), publication: normalizeFavoriteList(publications, PUBLICATION) };
    const serverKey = favoritesKey(server);
    const draft = readDraft();

    state.serverFavorites = server;
    state.draftMeta = { base: serverKey, saved: null, savedKey: '' };
    setFavoriteMaps(server);
    if (!draft) return;

    if (draft.savedKey && draft.savedKey === serverKey) {
        // 저장한 목록이 사이트에 반영됨 → 그 뒤에 고친 내용만 이어서 유지
        setFavoriteMaps(draft.lists);
    } else if (draft.base === serverKey) {
        // 아직 같은 서버 목록 기준 (저장했다면 반영 대기 중)
        if (draft.saved) {
            state.serverFavorites = cloneLists(draft.saved);
            state.draftMeta = { base: serverKey, saved: draft.saved, savedKey: draft.savedKey };
        }
        setFavoriteMaps(draft.lists);
    } else {
        // 그 사이 서버 목록이 바뀜 (새 AI 선정 등) → 임시 변경은 버림
        storageRemove(DRAFT_KEY);
        const hadChanges = draft.lists && favoritesKey(draft.lists) !== (draft.savedKey || draft.base);
        if (hadChanges) toast('새 일일 동향이 나와서, 저장하지 않았던 ⭐ 변경은 지웠습니다.', { timeout: 8000 });
        return;
    }
    persistDraft();
}

function updateFavoriteCounts() {
    TYPES.forEach(type => {
        const el = document.getElementById(`fav-count-${type}`);
        if (el) el.textContent = state.favorites[type].size ? String(state.favorites[type].size) : '';
    });
}

function renderFavoritesBar() {
    const bar = document.getElementById('favorites-bar');
    const changes = favoritesChanges();
    bar.hidden = changes.total === 0;
    if (changes.total === 0) return;
    const parts = [];
    if (changes.added) parts.push(`추가 ${changes.added}`);
    if (changes.removed) parts.push(`빼기 ${changes.removed}`);
    if (changes.changed) parts.push(`분류 변경 ${changes.changed}`);
    document.getElementById('favorites-bar-text').textContent =
        `저장하지 않은 일일 동향 변경: ${parts.join(' · ')}`;
}

function afterFavoritesChange() {
    persistDraft();
    updateFavoriteCounts();
    renderFavoritesBar();
    renderCurrentView();
}

async function toggleFavorite(item) {
    const map = state.favorites[item.type];
    if (map.has(item.link)) {
        map.delete(item.link);
    } else {
        let category = PUBLICATION_CATEGORY;
        if (item.type === ARTICLE) {
            category = await pickCategory(item, '⭐ 오늘 일일 동향에 넣기');
            if (!category) return;
        }
        map.set(item.link, { title: item.title, link: item.link, category, site: item.site });
    }
    afterFavoritesChange();
}

async function changeFavoriteCategory(item) {
    const current = state.favorites[item.type].get(item.link);
    if (!current || item.type !== ARTICLE) return;
    const category = await pickCategory(item, '분류 바꾸기', current.category);
    if (!category || category === current.category) return;
    state.favorites[item.type].set(item.link, { ...current, category });
    afterFavoritesChange();
}

function revertFavorites() {
    setFavoriteMaps(state.serverFavorites);
    afterFavoritesChange();
    toast('저장된 일일 동향으로 되돌렸습니다.');
}

async function clearFavorites(type) {
    const label = type === ARTICLE ? '기사' : '간행물';
    const ok = await confirmDialog('모두 빼기', `오늘 일일 동향에서 ${label} ${state.favorites[type].size}건을 모두 뺄까요?\n('일일 동향 저장'을 눌러야 실제로 반영됩니다)`, { confirmText: '모두 빼기', danger: true });
    if (!ok) return;
    state.favorites[type].clear();
    afterFavoritesChange();
}

// ⭐ 목록을 저장소에 올리고 일일 동향 텍스트(json_to_txt)를 다시 만듭니다.
async function saveFavorites(button) {
    if (!(await ensureAdmin())) return false;
    return withBusy(button, async () => {
        const lists = currentLists();
        try {
            const remote = {};
            for (const type of TYPES) remote[type] = await readRepoJSON(FAVORITE_FILES[type]);

            // 이 페이지를 연 뒤 서버 목록이 바뀌었으면(새 AI 선정, 다른 관리자 저장) 덮어쓰기 전에 확인
            const changedRemotely = TYPES.some(type =>
                listSignature(normalizeFavoriteList(remote[type].data, type)) !== listSignature(state.serverFavorites[type]));
            if (changedRemotely) {
                const ok = await confirmDialog('서버 목록이 바뀌었습니다',
                    '이 페이지를 연 뒤 저장소의 일일 동향이 바뀌었습니다. (새 AI 선정 또는 다른 관리자의 저장)\n\n그래도 지금 화면의 ⭐ 목록으로 덮어쓸까요?',
                    { confirmText: '덮어쓰기', danger: true });
                if (!ok) return false;
            }

            for (const type of TYPES) {
                if (listSignature(normalizeFavoriteList(remote[type].data, type)) === listSignature(lists[type])) continue;
                await writeRepoJSON(FAVORITE_FILES[type], lists[type], remote[type].sha, `update ${FAVORITE_FILES[type]}`);
            }
        } catch (error) {
            console.error(error);
            toast(`일일 동향 저장 실패: ${error.message}`, { type: 'error', timeout: 8000 });
            return false;
        }

        state.serverFavorites = cloneLists(lists);
        state.draftMeta = { ...state.draftMeta, saved: cloneLists(lists), savedKey: favoritesKey(lists) };
        afterFavoritesChange();
        return dispatchWorkflow('json_to_txt', '⭐ 목록을 저장했습니다. 일일 동향 텍스트를 만드는 중입니다. (약 1분 뒤 반영)');
    });
}

// -----------------------------------------------------
// 7. Few-shot 학습 데이터 · 일일동향 제외 (관리자)
// -----------------------------------------------------
async function loadFewshotAndExcluded() {
    const [fewshot, excluded] = await Promise.all([fetchJSON(FEWSHOT_FILE, []), fetchJSON(EXCLUDED_FILE, [])]);
    state.fewshot = Array.isArray(fewshot) ? fewshot : [];
    state.excluded = new Set((Array.isArray(excluded) ? excluded : []).map(item => item.link).filter(Boolean));
}

// 학습 데이터는 출처를 표시 이름(displayName)으로 저장합니다.
function sameFewshot(example, item) {
    return example.title === item.title && example.site === item.displayName;
}

async function toggleFewshot(item, button) {
    if (!(await ensureAdmin())) return;
    const learned = state.fewshot.some(example => sameFewshot(example, item));
    if (learned) {
        const ok = await confirmDialog('🧠 학습 데이터에서 빼기', `${item.title}\n(${item.displayName})\n\n이 기사를 AI 분류 학습 데이터에서 뺄까요?`, { confirmText: '빼기', danger: true });
        if (!ok) return;
    }
    let example = null;
    if (!learned) {
        const data = await openDialog({
            title: '🧠 AI 분류 학습 데이터 추가',
            body: `${itemSummaryHTML(item)}
                <div class="field-label">올바른 분류</div>${categoryChips('')}
                <label class="field">이유 (선택)
                    <textarea name="reason" rows="2" maxlength="300" placeholder="AI가 이 분류로 판단해야 하는 이유"></textarea>
                </label>`,
            confirmText: '추가',
        });
        if (!data) return;
        const reason = String(data.get('reason') || '').trim();
        example = { site: item.displayName, title: item.title, category: String(data.get('category')), ...(reason && { reason }) };
    }

    await withBusy(button, async () => {
        try {
            const next = await updateRepoJSON(FEWSHOT_FILE, list => {
                if (learned) {
                    const filtered = list.filter(d => !sameFewshot(d, item));
                    return filtered.length === list.length ? null : filtered;
                }
                return list.some(d => sameFewshot(d, item)) ? null : [...list, example];
            }, `${learned ? 'Remove' : 'Add'} few-shot example: ${item.title}`);
            if (next) state.fewshot = next;
            toast(learned ? '학습 데이터에서 뺐습니다.' : '학습 데이터에 추가했습니다. 다음 AI 선정부터 반영됩니다.', { type: 'success' });
        } catch (error) {
            console.error(error);
            toast(`학습 데이터 저장 실패: ${error.message}`, { type: 'error' });
        }
    });
    renderCurrentView();
}

async function toggleExclude(item, button) {
    if (!(await ensureAdmin())) return;
    const isExcluded = state.excluded.has(item.link);
    let reason = '';
    if (isExcluded) {
        const ok = await confirmDialog('🚫 제외 해제', `${item.title}\n(${item.displayName})\n\n이 기사를 다시 일일 동향 후보에 넣을까요?`, { confirmText: '해제' });
        if (!ok) return;
    } else {
        const data = await openDialog({
            title: '🚫 일일 동향에서 제외',
            body: `${itemSummaryHTML(item)}
                <p class="dialog-message">AI가 이 기사를 일일 동향에 고르지 않도록 합니다.</p>
                <label class="field">이유 (선택)
                    <textarea name="reason" rows="2" maxlength="300" placeholder="AI가 이런 기사를 고르지 말아야 하는 이유"></textarea>
                </label>`,
            confirmText: '제외',
            danger: true,
        });
        if (!data) return;
        reason = String(data.get('reason') || '').trim();
    }

    await withBusy(button, async () => {
        try {
            await updateRepoJSON(EXCLUDED_FILE, list => {
                if (isExcluded) {
                    const filtered = list.filter(d => d.link !== item.link);
                    return filtered.length === list.length ? null : filtered;
                }
                if (list.some(d => d.link === item.link)) return null;
                return [...list, { title: item.title, link: item.link, site: item.displayName, ...(reason && { reason }) }];
            }, `${isExcluded ? 'Remove' : 'Add'} excluded article: ${item.title}`);
            if (isExcluded) state.excluded.delete(item.link);
            else state.excluded.add(item.link);
            toast(isExcluded ? '제외를 해제했습니다.' : '제외했습니다. AI가 이 기사를 고르지 않습니다.', { type: 'success' });
        } catch (error) {
            console.error(error);
            toast(`제외 목록 저장 실패: ${error.message}`, { type: 'error' });
        }
    });
    renderCurrentView();
}

// -----------------------------------------------------
// 8. 화면 그리기
// -----------------------------------------------------
function viewType(view) {
    if (view.startsWith('ARTICLE_')) return ARTICLE;
    if (view.startsWith('PUBLICATION_')) return PUBLICATION;
    const source = state.sourceById.get(view);
    return source ? source.type : null;
}

function isValidView(view) {
    return view === 'HOME' || ['ARTICLE_ALL', 'ARTICLE_FAV', 'PUBLICATION_ALL', 'PUBLICATION_FAV'].includes(view) || state.sourceById.has(view);
}

function viewTitle(view) {
    const titles = {
        HOME: '대시보드',
        ARTICLE_ALL: '기사 전체',
        ARTICLE_FAV: '⭐ 오늘 일일 동향 · 기사',
        PUBLICATION_ALL: '간행물 전체',
        PUBLICATION_FAV: '⭐ 오늘 일일 동향 · 간행물',
    };
    if (titles[view]) return titles[view];
    const source = state.sourceById.get(view);
    return source ? navLabel(source) : 'AI 동향 분석';
}

const SORT_OPTIONS = {
    article: [['date_desc', '최신순'], ['date_asc', '오래된순'], ['title_asc', '제목순'], ['site_asc', '출처순']],
    publication: [['date_desc', '최신순'], ['date_asc', '오래된순'], ['title_asc', '제목순'], ['category_asc', '분류순']],
};

function sortItems(items, sortBy) {
    const sorted = [...items];
    sorted.sort((a, b) => {
        switch (sortBy) {
            case 'date_asc': return a.dateKey.localeCompare(b.dateKey);
            case 'title_asc': return a.title.localeCompare(b.title);
            case 'site_asc': return (a.displayName || '').localeCompare(b.displayName || '') || b.dateKey.localeCompare(a.dateKey);
            case 'category_asc': return (a.category || '').localeCompare(b.category || '') || b.dateKey.localeCompare(a.dateKey);
            case 'date_desc':
            default: return b.dateKey.localeCompare(a.dateKey);
        }
    });
    return sorted;
}

function formatItemDate(item) {
    if (!item.년) return '';
    const time = (item.시 && item.분) ? ` ${pad2(item.시)}:${pad2(item.분)}` : '';
    return `${item.년}.${pad2(item.월)}.${pad2(item.일)}${time}`;
}

function categoryBadge(category, editable) {
    const cls = CATEGORY_CLASS[category] || 'cat-default';
    if (!editable) return `<span class="badge ${cls}">${escapeHTML(category)}</span>`;
    return `<button type="button" class="badge ${cls}" data-action="category" title="분류 바꾸기">${escapeHTML(category)}</button>`;
}

function renderItem(item) {
    const favorite = state.favorites[item.type].get(item.link);
    const admin = state.admin.enabled;
    const isArticle = item.type === ARTICLE;
    const excluded = admin && isArticle && state.excluded.has(item.link);

    let adminButtons = '';
    if (admin && isArticle) {
        const learned = state.fewshot.some(example => sameFewshot(example, item));
        adminButtons = `
            <button type="button" class="tool-btn${learned ? ' is-on' : ''}" data-action="fewshot" title="${learned ? 'AI 분류 학습 데이터에서 빼기' : 'AI 분류 학습 데이터로 추가'}" aria-pressed="${learned}">🧠</button>
            <button type="button" class="tool-btn${excluded ? ' is-on danger' : ''}" data-action="exclude" title="${excluded ? '제외 해제 (일일 동향 후보에 다시 포함)' : '일일 동향에서 제외 (AI가 고르지 않음)'}" aria-pressed="${excluded}">🚫</button>`;
    }

    const badges = [];
    if (favorite) badges.push(categoryBadge(favorite.category, isArticle));
    if (excluded) badges.push('<span class="badge badge-excluded">일일 동향 제외</span>');
    const meta = [item.displayName, item.category, formatItemDate(item)].filter(Boolean)
        .map(text => `<span>${escapeHTML(text)}</span>`).join('');

    return `
        <li class="article-item${excluded ? ' is-excluded' : ''}" data-link="${escapeHTML(item.link)}">
            <div class="article-actions">
                <button type="button" class="favorite-btn${favorite ? ' is-favorite' : ''}" data-action="favorite"
                    aria-pressed="${Boolean(favorite)}" title="${favorite ? '오늘 일일 동향에서 빼기' : '오늘 일일 동향에 넣기'}">${favorite ? '★' : '☆'}</button>
                ${adminButtons}
            </div>
            <div class="article-body">
                <div class="article-title-row">
                    <a class="article-title" href="${escapeHTML(safeUrl(item.link))}" target="_blank" rel="noopener noreferrer">${escapeHTML(item.title)}</a>
                    ${badges.join('')}
                </div>
                <div class="article-meta">${meta}</div>
            </div>
        </li>`;
}

// ⭐ 목록 항목: 불러온 기사 데이터에 있으면 그 정보(날짜 등)를, 없으면 저장된 값만으로 표시
function favoriteItems(type) {
    return Array.from(state.favorites[type].values()).map(fav => {
        const found = state.linkIndex.get(fav.link);
        if (found) return found;
        const source = state.sourceById.get(fav.site) || state.sources.find(s => s.name === fav.site);
        return {
            title: fav.title || '제목 없음', link: fav.link, type, site: source ? source.id : fav.site,
            displayName: source ? source.name : (fav.site || ''), category: '', dateKey: '',
        };
    });
}

function renderList(view) {
    const type = viewType(view);
    const isFav = view.endsWith('_FAV');
    const isAll = view.endsWith('_ALL');
    const searchTerm = state.search[type].trim().toLowerCase();

    let items;
    if (isFav) items = favoriteItems(type);
    else if (isAll) items = state.items[type];
    else items = state.items[type].filter(item => item.site === view);

    // 최근 데이터만 있는 상태에서 검색하면 전체 기간 데이터를 받아 다시 검색 (그동안은 최근 결과를 먼저 표시)
    if (searchTerm && state.dataScope === 'recent' && !isFav) {
        loadAllDataAndRender('전체 기간에서 검색하기 위해 데이터를 불러오는 중입니다...');
    } else {
        updateDataScopeNotice();
    }

    if (searchTerm) items = items.filter(item => item.title.toLowerCase().includes(searchTerm));
    const sorted = sortItems(items, state.sort[type]);
    const container = document.getElementById('data-list-container');
    const noData = document.getElementById('no-data');
    const showMoreBtn = document.getElementById('showMoreBtn');

    const visible = sorted.slice(0, state.renderLimit);
    state.renderedItems = new Map(visible.map(item => [item.link, item]));
    container.innerHTML = visible.map(renderItem).join('');

    noData.hidden = sorted.length > 0;
    if (!sorted.length) {
        noData.textContent = searchTerm ? `"${state.search[type].trim()}" 검색 결과가 없습니다.`
            : isFav ? '오늘 일일 동향에 넣은 항목이 없습니다. 목록에서 ☆를 눌러 넣을 수 있습니다.'
                : '데이터가 없습니다.';
    }
    const remaining = sorted.length - visible.length;
    showMoreBtn.hidden = remaining <= 0;
    showMoreBtn.textContent = `더 보기 (${remaining.toLocaleString()}건 남음)`;
}

function updateDataScopeNotice(loadingMessage) {
    const notice = document.getElementById('data-scope-notice');
    const isFav = state.view.endsWith('_FAV');
    notice.hidden = state.dataScope !== 'recent' || state.view === 'HOME' || isFav;
    document.getElementById('data-scope-text').textContent = loadingMessage ||
        `빠른 표시를 위해 최근 ${state.recentDays}일 데이터만 보여주고 있습니다.`;
    const btn = document.getElementById('loadAllDataBtn');
    btn.disabled = Boolean(loadingMessage);
    btn.hidden = Boolean(loadingMessage);
}

function renderLatest(elementId, items) {
    document.getElementById(elementId).innerHTML = sortItems(items, 'date_desc').slice(0, 5).map(item => `
        <li class="latest-item">
            <a href="${escapeHTML(safeUrl(item.link))}" target="_blank" rel="noopener noreferrer">${escapeHTML(item.title)}</a>
            <span>${escapeHTML(item.displayName)} · ${escapeHTML(formatItemDate(item).slice(0, 10))}</span>
        </li>`).join('') || '<li class="latest-item empty">데이터가 없습니다.</li>';
}

function renderDashboard() {
    renderLatest('latest-articles', state.items.article);
    renderLatest('latest-publications', state.items.publication);
}

function showView(view) {
    if (!isValidView(view)) view = 'HOME';
    const changed = view !== state.view;
    if (changed) state.renderLimit = PAGE_SIZE;
    state.view = view;

    document.querySelectorAll('.nav-link[data-view]').forEach(link => {
        const active = link.dataset.view === view;
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
    });
    document.getElementById('main-content-title').textContent = viewTitle(view);

    const isHome = view === 'HOME';
    document.getElementById('dashboard-view').hidden = !isHome;
    document.getElementById('list-view').hidden = isHome;

    if (isHome) {
        renderDashboard();
    } else {
        const type = viewType(view);
        const search = document.getElementById('search-term');
        if (search.value !== state.search[type]) search.value = state.search[type];
        search.placeholder = type === ARTICLE ? '기사 제목 검색' : '간행물 제목 검색';
        const select = document.getElementById('sort-by');
        select.innerHTML = SORT_OPTIONS[type].map(([value, label]) =>
            `<option value="${value}"${value === state.sort[type] ? ' selected' : ''}>${label}</option>`).join('');
        document.getElementById('clearFavoritesBtn').hidden = !(view.endsWith('_FAV') && state.favorites[type].size);
        renderList(view);
    }
    if (changed) window.scrollTo({ top: 0 });
}

function renderCurrentView() {
    showView(state.view);
}

function viewFromHash() {
    try {
        return decodeURIComponent(location.hash.replace(/^#/, '')) || 'HOME';
    } catch (e) {
        return 'HOME';
    }
}

// -----------------------------------------------------
// 9. 오늘 일일 동향 카드 (data.txt) · 업데이트 시각
// -----------------------------------------------------
async function loadReportPreview() {
    const title = document.getElementById('report-date');
    const summary = document.getElementById('report-summary');
    try {
        const res = await fetch(withCacheBust(REPORT_URL));
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        const match = text.match(/📢(\d{2}\.\d{2}\.\d{2}) AI 일일 동향📢/);
        const dateKey = match ? match[1] : '';
        const pubIndex = text.indexOf('📚');
        const before = pubIndex >= 0 ? text.slice(0, pubIndex) : text;
        const articleCount = (before.match(/^◾/gm) || []).length;
        const publicationCount = pubIndex >= 0 ? (text.slice(pubIndex).match(/^◾/gm) || []).length : 0;

        title.textContent = dateKey ? `${dateKey} AI 일일 동향` : 'AI 일일 동향';
        const isToday = dateKey === todayKstKey();
        summary.textContent = `기사 ${articleCount}건 · 간행물 ${publicationCount}건` +
            (isToday ? '' : ' — 아직 오늘 일일 동향이 만들어지지 않았습니다. (매일 새벽 4시경 생성)');
        summary.classList.toggle('is-stale', !isToday);
    } catch (error) {
        console.error(error);
        title.textContent = 'AI 일일 동향';
        summary.textContent = '일일 동향을 불러오지 못했습니다.';
    }
}

async function copyReport(button) {
    await withBusy(button, async () => {
        try {
            const res = await fetch(withCacheBust(REPORT_URL));
            if (!res.ok) throw new Error('일일 동향 파일을 불러오지 못했습니다.');
            await copyText(await res.text());
            toast('일일 동향을 복사했습니다. 메신저에 붙여 넣어 공유하세요.', {
                type: 'success',
                action: { label: '시각화 보기', onClick: () => { location.href = 'visualizer.html'; } },
            });
        } catch (error) {
            console.error(error);
            toast(`복사하지 못했습니다: ${error.message}`, { type: 'error' });
        }
    });
}

async function loadCompletionTime() {
    const el = document.getElementById('workflow-completed-time');
    try {
        const data = await fetchJSON(UPDATE_TIME_URL);
        const match = String(data.completed_at || '').match(/^\d{4}-(\d{2})-(\d{2}) (\d{2}):(\d{2})/);
        el.textContent = match ? `${match[1]}.${match[2]} ${match[3]}:${match[4]}` : (data.completed_at || '정보 없음');
    } catch (error) {
        el.textContent = '정보 없음';
    }
}

// -----------------------------------------------------
// 10. 자동 처리 현황 · 워크플로우 실행 (GitHub Actions)
// -----------------------------------------------------
function formatRunTime(isoString) {
    if (!isoString) return '';
    const p = kstParts(new Date(isoString));
    const key = `${p.year.slice(2)}.${p.month}.${p.day}`;
    return key === todayKstKey() ? `오늘 ${p.hour}:${p.minute}` : `${p.month}.${p.day} ${p.hour}:${p.minute}`;
}

function runStatus(run) {
    if (run === undefined) return { key: 'unknown', icon: '·', text: '확인 불가' };
    if (run === null) return { key: 'none', icon: '·', text: '기록 없음' };
    if (run.status !== 'completed') return { key: 'running', icon: '⏳', text: run.status === 'queued' ? '대기 중' : '진행 중' };
    const map = {
        success: { key: 'success', icon: '✅', text: '완료' },
        failure: { key: 'failure', icon: '❌', text: '실패' },
        cancelled: { key: 'cancelled', icon: '⏹️', text: '취소됨' },
        skipped: { key: 'skipped', icon: '⏭️', text: '건너뜀' },
        timed_out: { key: 'failure', icon: '⌛', text: '시간 초과' },
    };
    return map[run.conclusion] || { key: 'unknown', icon: '·', text: run.conclusion || '알 수 없음' };
}

async function fetchLatestRun(workflow) {
    try {
        const data = await callProxyAPI(`${REPO_API}/actions/workflows/${workflow}.yml/runs?per_page=1`, 'GET');
        return (data && data.workflow_runs && data.workflow_runs[0]) || null;
    } catch (error) {
        console.warn(`${workflow} 실행 기록을 불러오지 못했습니다:`, error);
        return undefined;
    }
}

function renderPipeline() {
    document.getElementById('pipeline').innerHTML = PIPELINE.map(stage => {
        const run = state.pipeline[stage.workflow];
        const status = runStatus(run);
        const time = run ? formatRunTime(run.run_started_at || run.created_at) : '';
        const stale = run && run.status === 'completed' && !time.startsWith('오늘');  // 오늘 실행 기록이 아님
        const link = run && run.html_url
            ? `<a class="stage-link" href="${escapeHTML(safeUrl(run.html_url))}" target="_blank" rel="noopener noreferrer">실행 기록</a>` : '';
        return `
            <li class="stage stage-${status.key}${stale ? ' is-stale' : ''}">
                <span class="stage-icon" aria-hidden="true">${status.icon}</span>
                <span class="stage-text">
                    <span class="stage-label">${escapeHTML(stage.label)}</span>
                    <span class="stage-status">${escapeHTML(status.text)}${time ? ` · ${escapeHTML(time)}` : ''}</span>
                </span>
                ${link}
            </li>`;
    }).join('');
}

async function refreshPipeline() {
    const workflows = new Set(PIPELINE.map(stage => stage.workflow));
    state.watches.forEach((_, workflow) => workflows.add(workflow));
    const results = await Promise.all(Array.from(workflows).map(async workflow => [workflow, await fetchLatestRun(workflow)]));
    results.forEach(([workflow, run]) => { state.pipeline[workflow] = run; });
    renderPipeline();
    checkWatches();
}

// 실행을 요청한 워크플로우가 끝나면 알림
function checkWatches() {
    state.watches.forEach((watch, workflow) => {
        const run = state.pipeline[workflow];
        if (!run || Date.parse(run.created_at) < watch.since) return;  // 아직 새 실행이 시작되지 않음
        if (run.status !== 'completed') return;
        state.watches.delete(workflow);
        state.watchUntil = Math.max(state.watchUntil, Date.now() + WATCH_AFTER_MS);  // 이어지는 단계 대기
        const label = (WORKFLOWS[workflow] || {}).label || workflow;
        if (run.conclusion === 'success') {
            toast(`${label}이(가) 끝났습니다. 사이트 반영까지 1~2분 걸릴 수 있습니다.`, {
                type: 'success', timeout: 0,
                action: { label: '새로고침', onClick: () => location.reload() },
            });
        } else {
            toast(`${label}이(가) ${runStatus(run).text} 상태로 끝났습니다. 실행 기록을 확인하세요.`, {
                type: 'error', timeout: 0,
                action: { label: '실행 기록', onClick: () => window.open(safeUrl(run.html_url), '_blank', 'noopener') },
            });
        }
    });
}

function schedulePoll(delay) {
    clearTimeout(state.pollTimer);
    state.pollTimer = setTimeout(pollPipeline, delay);
}

async function pollPipeline() {
    if (document.hidden) {  // 탭이 안 보일 때는 쉬었다가 다시 보이면 이어서 확인
        document.addEventListener('visibilitychange', pollPipeline, { once: true });
        return;
    }
    await refreshPipeline();
    const running = Object.values(state.pipeline).some(run => run && run.status !== 'completed');
    if (running) state.watchUntil = Math.max(state.watchUntil, Date.now() + WATCH_AFTER_MS);
    if (running || state.watches.size || Date.now() < state.watchUntil) schedulePoll(POLL_ACTIVE_MS);
}

async function dispatchWorkflow(workflow, successMessage) {
    try {
        await callProxyAPI(`${REPO_API}/actions/workflows/${workflow}.yml/dispatches`, 'POST', { ref: BRANCH });
    } catch (error) {
        console.error(error);
        toast(`실행 요청 실패: ${error.message}`, { type: 'error', timeout: 8000 });
        return false;
    }
    toast(successMessage || `${WORKFLOWS[workflow].label} 실행을 요청했습니다. 진행 상황은 '오늘 자동 처리 현황'에 표시됩니다.`, { type: 'success' });
    state.watches.set(workflow, { since: Date.now() - 15000 });  // 서버 시각 차이 여유
    state.watchUntil = Date.now() + WATCH_AFTER_MS;
    schedulePoll(5000);
    return true;
}

async function runWorkflow(workflow, button) {
    if (!(await ensureAdmin())) return;
    // ⭐ 목록으로 텍스트를 만들 때 저장하지 않은 변경이 있으면 먼저 저장
    if (workflow === 'json_to_txt' && favoritesChanges().total > 0) {
        await saveFavorites(button);
        return;
    }
    const config = WORKFLOWS[workflow];
    const ok = await confirmDialog(config.label, config.confirm, { confirmText: '실행' });
    if (!ok) return;
    await withBusy(button, () => dispatchWorkflow(workflow));
}

// -----------------------------------------------------
// 11. 테마 · 사이드바 · 기타 UI
// -----------------------------------------------------
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.getElementById('themeToggle').textContent = theme === 'dark' ? '🌙' : '☀️';
}

function toggleTheme() {
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    storageSet(THEME_KEY, next);
    applyTheme(next);
}

function isMobileLayout() {
    return window.matchMedia('(max-width: 900px)').matches;
}

function setSidebarOpen(open) {
    document.body.classList.toggle('sidebar-open', open);
    document.getElementById('sidebarBackdrop').hidden = !open;
    document.getElementById('sidebarToggle').setAttribute('aria-expanded', String(open));
}

function bindEvents() {
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    document.getElementById('adminModeBtn').addEventListener('click', async () => {
        if (state.admin.enabled) {
            setAdmin(false);
            toast('관리자 모드를 잠갔습니다.');
        } else {
            await ensureAdmin();
        }
    });

    document.getElementById('sidebarToggle').addEventListener('click', () => {
        if (isMobileLayout()) setSidebarOpen(!document.body.classList.contains('sidebar-open'));
        else document.body.classList.toggle('sidebar-collapsed');
    });
    document.getElementById('sidebarBackdrop').addEventListener('click', () => setSidebarOpen(false));
    document.getElementById('main-nav').addEventListener('click', event => {
        if (event.target.closest('a') && isMobileLayout()) setSidebarOpen(false);
    });
    window.addEventListener('hashchange', () => showView(viewFromHash()));

    document.getElementById('search-term').addEventListener('input', debounce(event => {
        const type = viewType(state.view);
        if (!type) return;
        state.search[type] = event.target.value;
        state.renderLimit = PAGE_SIZE;
        renderCurrentView();
    }, 250));
    document.getElementById('sort-by').addEventListener('change', event => {
        const type = viewType(state.view);
        if (!type) return;
        state.sort[type] = event.target.value;
        state.renderLimit = PAGE_SIZE;
        renderCurrentView();
    });
    document.getElementById('loadAllDataBtn').addEventListener('click', () => loadAllDataAndRender('전체 기간 데이터를 불러오는 중입니다...'));
    document.getElementById('showMoreBtn').addEventListener('click', () => {
        state.renderLimit += PAGE_SIZE;
        renderCurrentView();
    });
    document.getElementById('clearFavoritesBtn').addEventListener('click', () => clearFavorites(viewType(state.view)));

    // 목록 버튼 (⭐, 분류, 🧠, 🚫) — 항목마다 onclick 을 넣지 않고 한 곳에서 처리
    document.getElementById('data-list-container').addEventListener('click', event => {
        const button = event.target.closest('[data-action]');
        if (!button) return;
        const li = button.closest('[data-link]');
        const item = li && state.renderedItems.get(li.dataset.link);
        if (!item) return;
        event.preventDefault();
        const actions = {
            favorite: () => toggleFavorite(item),
            category: () => changeFavoriteCategory(item),
            fewshot: () => toggleFewshot(item, button),
            exclude: () => toggleExclude(item, button),
        };
        if (actions[button.dataset.action]) actions[button.dataset.action]();
    });

    document.getElementById('saveFavoritesBtn').addEventListener('click', event => saveFavorites(event.currentTarget));
    document.getElementById('revertFavoritesBtn').addEventListener('click', revertFavorites);
    document.getElementById('copyReportBtn').addEventListener('click', event => copyReport(event.currentTarget));
    document.getElementById('refreshPipelineBtn').addEventListener('click', event => withBusy(event.currentTarget, refreshPipeline));
    document.querySelectorAll('[data-workflow]').forEach(button => {
        button.addEventListener('click', () => runWorkflow(button.dataset.workflow, button));
    });

    const scrollTopBtn = document.getElementById('scrollTopBtn');
    window.addEventListener('scroll', () => { scrollTopBtn.hidden = window.scrollY < 400; }, { passive: true });
    scrollTopBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// -----------------------------------------------------
// 12. 시작
// -----------------------------------------------------
async function init() {
    applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
    bindEvents();
    document.getElementById('audioPlayer').src = withCacheBust(AUDIO_URL);
    loadCompletionTime();
    loadReportPreview();
    refreshPipeline().then(() => {
        if (Object.values(state.pipeline).some(run => run && run.status !== 'completed')) schedulePoll(POLL_ACTIVE_MS);
    });

    try {
        await loadSources();
    } catch (error) {
        console.error('출처 목록(config/sources.json)을 불러오지 못했습니다:', error);
        document.getElementById('no-data').textContent = '출처 목록을 불러오지 못했습니다. 잠시 후 새로고침해 주세요.';
        toast('출처 목록을 불러오지 못했습니다. 잠시 후 새로고침해 주세요.', { type: 'error', timeout: 0 });
        return;
    }

    try {
        await Promise.all([loadRecentOrAllData(), loadFavorites(), loadFewshotAndExcluded()]);
    } catch (error) {
        console.error('데이터 로드 중 오류:', error);
        document.getElementById('no-data').textContent = '데이터를 불러오는 중 오류가 발생했습니다.';
    }
    updateFavoriteCounts();
    renderFavoritesBar();
    state.view = '';  // 첫 화면 강제 그리기
    showView(viewFromHash());
}

document.addEventListener('DOMContentLoaded', init);
