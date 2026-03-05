// -----------------------------------------------------
// 1. 설정 및 공통 함수
// -----------------------------------------------------
const OWNER = "jhjhc1483";
const REPO = "AI_Trend_Analysis_vercel";
const BRANCH = "main";

//Vercel Serverless Function을 호출하는 함수
async function callProxyAPI(endpoint, method = 'GET', body = null) {
    try {
        const res = await fetch('/api/github', {
            method: 'POST', // 프록시에는 항상 POST로 데이터 전달
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                endpoint: endpoint, // 예: repos/owner/repo/...
                method: method,     // 실제 GitHub에 보낼 method (GET, POST, PUT 등)
                body: body          // 실제 GitHub에 보낼 데이터
            })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.message || `HTTP Error ${res.status}`);
        }

        // 204 No Content 처리
        if (res.status === 204) return null;

        return await res.json();
    } catch (error) {
        throw error;
    }
}

// 비밀번호 확인 함수
async function verifyPassword() {
    const pw = prompt("관리자 비밀번호를 입력하세요:");
    if (!pw) return false;

    try {
        const res = await fetch('/api/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pw })
        });
        const data = await res.json();
        if (data.success) return true;
        else {
            alert("비밀번호가 틀렸습니다.");
            return false;
        }
    } catch (e) {
        alert("비밀번호 확인 중 오류가 발생했습니다.");
        return false;
    }
}

// -----------------------------------------------------
// 2. 기사 업데이트 실행 (runActionBtn)
// -----------------------------------------------------
document.getElementById('runActionBtn').addEventListener('click', async function () {
    const message = "⚠️기사 업데이트를 진행하시겠습니까?⚠️\n\n" +
        "✅기사는 지정된 시간에 맞춰 자동으로 업데이트 됩니다.\n" +
        "✅수동으로 기사 업데이트 시 최소 5분 이상의 시간이 소요 됩니다.";

    if (!confirm(message)) return;

    const WORKFLOW_ID = "main.yml";
    const endpoint = `repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

    try {
        await callProxyAPI(endpoint, 'POST', { ref: "main" });
        alert("✅ 실행 성공! 최소 5분의 시간이 소요 됩니다.\n페이지를 새로고침 하세요.");
    } catch (error) {
        console.error('Error:', error);
        alert(`❌ 실패: ${error.message}`);
    }
});

// -----------------------------------------------------
// 3. 파일 불러오기 (loadFileBtn)
// -----------------------------------------------------
const popup = document.getElementById('popup');
const overlay = document.getElementById('overlay');
const contentDiv = document.getElementById('popupContent');
const PATH = "codes/data.txt";

function base64ToUtf8(base64) {
    const binary = atob(base64.replace(/\n/g, ""));
    const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
}

document.getElementById('loadFileBtn').addEventListener('click', async () => {
    try {
        const endpoint = `repos/${OWNER}/${REPO}/contents/${PATH}?ref=${BRANCH}`;
        const data = await callProxyAPI(endpoint, 'GET');

        const text = base64ToUtf8(data.content);
        contentDiv.textContent = text;
        popup.style.display = 'block';
        overlay.style.display = 'block';
        console.log(text);
    } catch (error) {
        console.error(error);
        alert("파일을 불러오는 중 오류 발생: " + error.message);
    }
});

document.getElementById('closeBtn').addEventListener('click', () => {
    popup.style.display = 'none';
    overlay.style.display = 'none';
});
document.getElementById('copyBtn2').addEventListener('click', () => {
    navigator.clipboard.writeText(contentDiv.textContent)
        .then(() => alert("복사 완료!"))
        .catch(err => alert("복사 실패: " + err));
});

// -----------------------------------------------------
// 4. 텍스트 만들기 실행 (runActionBtn2)
// -----------------------------------------------------
// document.getElementById('runActionBtn2').addEventListener('click', async function () {
//     const WORKFLOW_ID = "json_to_txt.yml";
//     const endpoint = `repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

//     try {
//         await callProxyAPI(endpoint, 'POST', { ref: "main" });
//         alert("✅ 즐겨찾기에 있는 목록을 일일 동향 텍스트로 만듭니다.\n\n약 30초 후 대시보드에서 '텍스트추출'을 누르세요.");
//     } catch (error) {
//         console.error('Error:', error);
//         alert(`❌ 실패: ${error.message}`);
//     }
// });

// -----------------------------------------------------
// 5. 전역 변수 및 데이터 로드
// -----------------------------------------------------
let articleData = [];
let publicationData = [];
let allDataLoaded;
let debounceTimeout;
let currentView = 'HOME';
let favoriteArticles = new Map();
let favoritePublications = new Map();
let fewshotExamples = [];
let excludedArticles = new Set(); // 일일동향 제외 블랙리스트 (링크 기준)
let fewshotUnlocked = false; // 관리자 인증 후 true로 변경
const cacheBuster = `?t=${new Date().getTime()}`;

const FILES_TO_LOAD = [
    { url: 'codes/aikorea.json' + cacheBuster, site: 'AIKOREA', isArticle: true, displayName: '국가인공지능전략위원회' },
    { url: 'codes/aitimes.json' + cacheBuster, site: 'AITIMES', isArticle: true, displayName: 'AI Times' },
    { url: 'codes/etnews.json' + cacheBuster, site: 'ETNEWS', isArticle: true, displayName: '전자신문' },
    { url: 'codes/AInews.json' + cacheBuster, site: 'AINEWS', isArticle: true, displayName: '인공지능신문' },
    { url: 'codes/mnd.json' + cacheBuster, site: 'MND', isArticle: true, displayName: '국방부' },
    { url: 'codes/kookbang.json' + cacheBuster, site: 'kookbang', isArticle: true, displayName: '국방일보' },
    { url: 'codes/dapa.json' + cacheBuster, site: 'DAPA', isArticle: true, displayName: '방사청' },
    { url: 'codes/msit.json' + cacheBuster, site: 'MSIT', isArticle: true, displayName: '과기정통부' },
    { url: 'codes/iitp.json' + cacheBuster, site: 'IITP', isArticle: false, displayName: 'IITP' },
    { url: 'codes/nia.json' + cacheBuster, site: 'NIA', isArticle: false, displayName: 'NIA' },
    { url: 'codes/STEPI.json' + cacheBuster, site: 'STEPI', isArticle: false, displayName: 'STEPI' },
    { url: 'codes/NIPA.json' + cacheBuster, site: 'NIPA', isArticle: false, displayName: 'NIPA' },
    { url: 'codes/KISDI.json' + cacheBuster, site: 'KISDI', isArticle: false, displayName: 'KISDI' },
    { url: 'codes/KISTI.json' + cacheBuster, site: 'KISTI', isArticle: false, displayName: 'KISTI' },
    { url: 'codes/KISA.json' + cacheBuster, site: 'KISA', isArticle: false, displayName: 'KISA' },
    { url: 'codes/tta.json' + cacheBuster, site: 'TTA', isArticle: false, displayName: 'TTA' }
];

function loadFewshotExamples() {
    return fetch('codes/favorites/fewshot_examples.json' + cacheBuster)
        .then(response => {
            if (!response.ok) return [];
            return response.json();
        })
        .then(data => {
            fewshotExamples = data;
            return data;
        })
        .catch(error => {
            console.error("Error loading fewshot examples:", error);
            return [];
        });
}

function loadExcludedArticles() {
    return fetch('codes/favorites/excluded_articles.json' + cacheBuster)
        .then(response => {
            if (!response.ok) return [];
            return response.json();
        })
        .then(data => {
            excludedArticles = new Set(data.map(item => item.link));
            return data;
        })
        .catch(error => {
            console.error("Error loading excluded articles:", error);
            return [];
        });
}

function loadData() {
    const favArticlesStr = localStorage.getItem('favoriteArticles');
    const favPublicationsStr = localStorage.getItem('favoritePublications');

    if (favArticlesStr) {
        const parsed = JSON.parse(favArticlesStr);
        if (Array.isArray(parsed) && parsed.length > 0 && Array.isArray(parsed[0])) {
            favoriteArticles = new Map(parsed);
        } else if (Array.isArray(parsed)) {
            favoriteArticles = new Map(parsed.map(link => [link, '기타']));
        }
    }

    if (favPublicationsStr) {
        const parsed = JSON.parse(favPublicationsStr);
        if (Array.isArray(parsed) && parsed.length > 0 && Array.isArray(parsed[0])) {
            favoritePublications = new Map(parsed);
        } else if (Array.isArray(parsed)) {
            favoritePublications = new Map(parsed.map(link => [link, '기타']));
        }
    }

    const promises = [
        ...FILES_TO_LOAD.map(file => {
            // 데이터 파일은 public 접근 가능하므로 기존 fetch 유지
            return fetch(file.url)
                .then(response => {
                    if (!response.ok) throw new Error(`Failed to load ${file.url}`);
                    return response.json();
                })
                .then(data => {
                    return data.map(item => ({
                        ...item,
                        site: file.site,
                        isArticle: file.isArticle,
                        displayName: file.displayName,
                        title: item.기사명 || item.제목 || '제목 없음',
                        link: item.링크 || item.link || '#',
                        category: item.분류 || item.category || '',
                    }));
                })
                .catch(error => {
                    console.error(`Error loading ${file.url}:`, error);
                    return [];
                });
        }),
        loadFewshotExamples(),
        loadExcludedArticles()
    ];

    Promise.all(promises)
        .then(results => {
            // 마지막 2개 결과(fewshotExamples, excludedArticles)는 이미 전역변수에 저장됨
            const dataResults = results.slice(0, -2);
            dataResults.forEach(siteData => {
                if (siteData.length > 0) {
                    if (siteData[0].isArticle) articleData = articleData.concat(siteData);
                    else publicationData = publicationData.concat(siteData);
                }
            });
            allDataLoaded = true;
            console.log(`Loaded ${articleData.length} articles, ${publicationData.length} publications.`);
            showTab('HOME');
        })
        .catch(error => {
            console.error("Critical error:", error);
            document.getElementById('no-data').textContent = "데이터 로드 중 치명적인 오류 발생.";
        });
}

// -----------------------------------------------------
// 6. UI/UX 렌더링 및 헬퍼 함수들
// -----------------------------------------------------
function sortData(data, sortBy) {
    const sortedData = [...data];
    sortedData.sort((a, b) => {
        const getDateString = (item) => `${item.년 || '0000'}${item.월 || '00'}${item.일 || '00'}${item.시 || '00'}${item.분 || '00'}`;
        const dateA = getDateString(a);
        const dateB = getDateString(b);
        switch (sortBy) {
            case 'date_asc': return dateA.localeCompare(dateB);
            case 'date_desc': return dateB.localeCompare(dateA);
            case 'title_asc': return a.title.localeCompare(b.title);
            case 'site_asc': return a.site !== b.site ? a.site.localeCompare(b.site) : dateB.localeCompare(dateA);
            case 'category_asc': return a.category !== b.category ? a.category.localeCompare(b.category) : dateB.localeCompare(dateA);
            default: return 0;
        }
    });
    return sortedData;
}

function showTab(sourceName) {
    currentView = sourceName;
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    const activeTab = document.querySelector(`.tab-button[data-source="${sourceName}"]`);
    if (activeTab) activeTab.classList.add('active');

    const isHome = sourceName === 'HOME';
    const isArticleView = sourceName.includes('ARTICLE') || ['AIKOREA', 'AITIMES', 'ETNEWS', 'AINEWS', 'MND', 'kookbang', 'DAPA', 'MSIT'].includes(sourceName);
    const isPublicationView = sourceName.includes('PUBLICATION') || ['NIA', 'IITP', 'STEPI', 'NIPA', 'KISDI', 'KISTI', 'KISA', 'TTA'].includes(sourceName);

    document.getElementById('dashboard-view').style.display = isHome ? 'block' : 'none';
    document.getElementById('list-view').style.display = isHome ? 'none' : 'block';
    document.getElementById('article-controls').style.display = isArticleView ? 'flex' : 'none';
    document.getElementById('publication-controls').style.display = isPublicationView ? 'flex' : 'none';

    document.getElementById('main-content-title').textContent = activeTab ? activeTab.textContent.replace(/^(🏠|📰|⭐️|📚) /, '') : 'AI 동향 분석';

    if (isHome) renderDashboard();
    else renderList(sourceName);
}

function renderCurrentView() { showTab(currentView); }

function renderDashboard() {
    // Stats removed

    const latestArticles = sortData(articleData, 'date_desc').slice(0, 5);
    document.getElementById('latest-articles').innerHTML = latestArticles.map(item => `
        <li class="latest-item">
            <a href="#" onclick="openPopup('${item.link}', '${item.title}'); return false;">${item.title}</a>
            <span>${item.displayName} | ${item.년}.${item.월}.${item.일}</span>
        </li>
    `).join('');

    const latestPublications = sortData(publicationData, 'date_desc').slice(0, 5);
    document.getElementById('latest-publications').innerHTML = latestPublications.map(item => `
        <li class="latest-item">
            <a href="#" onclick="openPopup('${item.link}', '${item.title}'); return false;">${item.title}</a>
            <span>${item.displayName} | ${item.년}.${item.월}.${item.일}</span>
        </li>
    `).join('');
}

function renderList(sourceName) {
    let data = [];
    let sortBy, searchTerm, dataLabel;
    const isArticle = sourceName.includes('ARTICLE') || ['AIKOREA', 'AITIMES', 'ETNEWS', 'AINEWS', 'MND', 'kookbang', 'DAPA', 'MSIT'].includes(sourceName);
    const isAll = sourceName.includes('_ALL');
    const isFav = sourceName.includes('_FAV');

    if (isArticle) {
        sortBy = document.getElementById('sort-by-article').value;
        searchTerm = document.getElementById('search-term-article').value.toLowerCase();
        dataLabel = '기사';
        if (isFav) data = articleData.filter(a => favoriteArticles.has(a.link));
        else if (isAll) data = articleData;
        else data = articleData.filter(a => a.site === sourceName);
    } else {
        sortBy = document.getElementById('sort-by-publication').value;
        searchTerm = document.getElementById('search-term-publication').value.toLowerCase();
        dataLabel = '간행물';
        if (isFav) data = publicationData.filter(p => favoritePublications.has(p.link));
        else if (isAll) data = publicationData;
        else data = publicationData.filter(p => p.site === sourceName);
    }

    if (searchTerm) data = data.filter(item => item.title.toLowerCase().includes(searchTerm));
    const filteredAndSortedData = sortData(data, sortBy);
    const listContainer = document.getElementById('data-list-container');
    const noDataMsg = document.getElementById('no-data');

    if (filteredAndSortedData.length === 0) {
        listContainer.innerHTML = '';
        noDataMsg.style.display = 'block';
        noDataMsg.textContent = searchTerm ? `검색어 "${searchTerm}" 결과 없음` : `데이터가 없습니다.`;
    } else {
        listContainer.innerHTML = filteredAndSortedData.map(item => createListItem(item)).join('');
        noDataMsg.style.display = 'none';
    }
}

function createListItem(item) {
    const timeInfo = (item.시 && item.분) ? `${item.시.padStart(2, '0')}:${item.분.padStart(2, '0')}` : '';
    const fullDate = `${item.년}.${item.월}.${item.일} ${timeInfo}`;
    let isFavorite = item.isArticle ? favoriteArticles.has(item.link) : favoritePublications.has(item.link);
    let categoryBadge = '';
    let colorClass = 'cat-default';

    if (isFavorite) {
        const savedCat = item.isArticle ? favoriteArticles.get(item.link) : favoritePublications.get(item.link);
        if (item.isArticle) {
            if (savedCat === '국방') colorClass = 'cat-defense';
            else if (savedCat === '육군') colorClass = 'cat-army';
            else if (savedCat === '민간') colorClass = 'cat-civil';
            else if (savedCat === '기관') colorClass = 'cat-pub';
            else if (savedCat === '해외') colorClass = 'cat-foreign';
            else if (savedCat === '기타') colorClass = 'cat-etc';
        } else {
            colorClass = 'cat-default';
        }
        categoryBadge = `<span class="category-badge ${colorClass}">${savedCat}</span>`;
    }

    // FewShot 모드에서만 표시되는 버튼들 (관리자 인증된 경우에만)
    let fewshotButtons = '';
    if (item.isArticle && fewshotUnlocked) {
        const isLearned = fewshotExamples.some(ex => ex.title === item.title && ex.site === item.displayName);
        const learnBtn = isLearned
            ? `<button class="learn-btn" onclick="removeFewshotExample(event, '${item.link}')" title="FewShot 학습에서 제거" style="background:none;border:none;cursor:pointer;font-size:1.1em;padding:0 3px;">🧠✕</button>`
            : `<button class="learn-btn" onclick="addFewshotExample(event, '${item.link}')" title="FewShot 학습 데이터로 추가" style="background:none;border:none;cursor:pointer;font-size:1.1em;padding:0 3px;">🧠</button>`;

        const isExcluded = excludedArticles.has(item.link);
        const excludeBtn = isExcluded
            ? `<button class="learn-btn" onclick="toggleExcludeArticle(event, '${item.link}')" title="제외 해제 클릭 → 일일동향에 다시 포함" style="background:#e74c3c;color:white;border:none;border-radius:4px;cursor:pointer;font-size:0.9em;padding:2px 6px;font-weight:bold;">🚫</button>`
            : `<button class="learn-btn" onclick="toggleExcludeArticle(event, '${item.link}')" title="일일동향에서 제외 (AI가 이 기사를 선택하지 않음)" style="background:#555;color:white;border:none;border-radius:4px;cursor:pointer;font-size:0.9em;padding:2px 6px;">🚫</button>`;

        fewshotButtons = learnBtn + excludeBtn;
    }

    const isExcluded = excludedArticles.has(item.link);
    const excludeStyle = isExcluded ? 'opacity:0.45;' : '';

    return `
        <li class="article-item" style="${excludeStyle}">
            <div class="article-actions">
                <button class="favorite-btn ${isFavorite ? 'is-favorite' : ''}" onclick="toggleFavorite(event, '${item.link}', ${item.isArticle})">${isFavorite ? '★' : '☆'}</button>
                ${fewshotButtons}
            </div>
            <div class="article-title-group">
                <a href="#" class="article-title" onclick="openPopup('${item.link}', '${item.title}'); return false;">${item.title}</a>
                ${isExcluded ? '<span style="font-size:0.75em;color:#e74c3c;font-weight:bold;margin-left:6px;">[ 일일동향 제외 ]</span>' : ''}
                ${categoryBadge}
                <div class="article-meta">
                    <span>출처: ${item.displayName}</span>
                    <span>분류: ${item.category || '-'}</span>
                </div>
            </div>
            <div class="article-date">${fullDate}</div>
        </li>
    `;
}


function toggleFavorite(event, link, isArticle) {
    event.stopPropagation();
    if (isArticle) {
        if (favoriteArticles.has(link)) favoriteArticles.delete(link);
        else {
            let cat = prompt("카테고리 (국방, 육군, 민간, 기관, 해외, 기타)", "");
            if (cat === null) return;
            favoriteArticles.set(link, cat.trim() || "기타");
        }
        localStorage.setItem('favoriteArticles', JSON.stringify(Array.from(favoriteArticles.entries())));
    } else {
        if (favoritePublications.has(link)) favoritePublications.delete(link);
        else favoritePublications.set(link, "간행물");
        localStorage.setItem('favoritePublications', JSON.stringify(Array.from(favoritePublications.entries())));
    }
    renderCurrentView();
    // Stats removed
}

function clearFavorites(type) {
    if (!confirm("정말 모두 삭제하시겠습니까?")) return;
    if (type === 'ARTICLE') {
        favoriteArticles.clear();
        localStorage.setItem('favoriteArticles', JSON.stringify([]));
    } else {
        favoritePublications.clear();
        localStorage.setItem('favoritePublications', JSON.stringify([]));
    }
    renderCurrentView();
}

function openPopup(link, title) {
    if (link && link !== '#') window.open(link, '_blank');
    else alert(`"${title}" 링크가 없습니다.`);
}

async function addFewshotExample(event, link) {
    event.stopPropagation();

    // Find the item
    const item = articleData.find(a => a.link === link);
    if (!item) return;

    // Prompt user for category
    const cat = prompt(`[AI 분류 학습 데이터 추가]\n\n기사 제목: ${item.title}\n출처: ${item.displayName}\n\n이 기사의 올바른 카테고리를 입력하세요.\n(국방, 육군, 민간, 기관, 해외, 기타 중 하나)`, "국방");
    if (!cat) return;

    const category = cat.trim();
    if (!["국방", "육군", "민간", "기관", "해외", "기타"].includes(category)) {
        alert("❌ 알맞은 카테고리(국방, 육군, 민간, 기관, 해외, 기타)를 입력해주세요.");
        return;
    }

    const filePath = "codes/favorites/fewshot_examples.json";
    const getEndpoint = `repos/${OWNER}/${REPO}/contents/${filePath}`;

    let fewshotData = [];
    let sha = null;

    try {
        // Show loading status safely
        const originalText = event.target.textContent;
        event.target.textContent = "⏳";

        // Try to get existing file
        try {
            const getResData = await callProxyAPI(`${getEndpoint}?ref=${BRANCH}`, 'GET');
            if (getResData && getResData.content) {
                const decodedContent = base64ToUtf8(getResData.content);
                fewshotData = JSON.parse(decodedContent);
                sha = getResData.sha;
            }
        } catch (e) {
            // File might not exist (404), which is fine
            console.log("Few-shot examples file not found. Creating a new one.");
        }

        // Check for duplicates
        const exists = fewshotData.some(d => d.title === item.title && d.site === item.site);
        if (exists) {
            alert("⚠️ 이미 학습 데이터에 존재하는 기사입니다.");
            event.target.textContent = originalText;
            return;
        }

        fewshotData.push({
            site: item.displayName, // user-facing site name
            title: item.title,
            category: category
        });

        const jsonString = JSON.stringify(fewshotData, null, 2);
        const encodedContent = btoa(unescape(encodeURIComponent(jsonString)));

        const putBody = {
            message: `Add few-shot example: ${item.title}`,
            content: encodedContent,
            branch: BRANCH,
            ...(sha && { sha })
        };

        await callProxyAPI(getEndpoint, 'PUT', putBody);

        // 로컬 데이터 업데이트 및 UI 갱신
        fewshotExamples = fewshotData;
        renderCurrentView();

        alert("✅ 올바른 카테고리 학습 데이터(Few-Shot)에 성공적으로 추가되었습니다.");

    } catch (err) {
        console.error("Error saving few-shot example:", err);
        alert("❌ 학습 데이터 저장 실패: " + err.message);
    } finally {
        // Restore button icon
        event.target.textContent = "🧠";
    }
}

// FewShot 제외 함수 (학습 데이터에서 삭제)
async function removeFewshotExample(event, link) {
    event.stopPropagation();

    const item = articleData.find(a => a.link === link);
    if (!item) return;

    if (!confirm(`[FewShot 제외]\n\n기사 제목: ${item.title}\n출처: ${item.displayName}\n\n이 기사를 FewShot 학습 데이터에서 제외하시겠습니까?`)) return;

    const filePath = "codes/favorites/fewshot_examples.json";
    const getEndpoint = `repos/${OWNER}/${REPO}/contents/${filePath}`;

    try {
        const originalText = event.target.textContent;
        event.target.textContent = "⏳";

        const getResData = await callProxyAPI(`${getEndpoint}?ref=${BRANCH}`, 'GET');
        if (!getResData || !getResData.content) {
            alert("⚠️ FewShot 데이터 파일을 찾을 수 없습니다.");
            event.target.textContent = originalText;
            return;
        }

        let fewshotData = JSON.parse(base64ToUtf8(getResData.content));
        const sha = getResData.sha;

        const prevLen = fewshotData.length;
        fewshotData = fewshotData.filter(d => !(d.title === item.title && d.site === item.displayName));

        if (fewshotData.length === prevLen) {
            alert("⚠️ 해당 기사가 학습 데이터에 없습니다.");
            event.target.textContent = originalText;
            return;
        }

        const jsonString = JSON.stringify(fewshotData, null, 2);
        const encodedContent = btoa(unescape(encodeURIComponent(jsonString)));

        await callProxyAPI(getEndpoint, 'PUT', {
            message: `Remove few-shot example: ${item.title}`,
            content: encodedContent,
            branch: BRANCH,
            sha
        });

        fewshotExamples = fewshotData;
        renderCurrentView();
        alert("✅ FewShot 학습 데이터에서 제외되었습니다.");

    } catch (err) {
        console.error("Error removing few-shot example:", err);
        alert("❌ 제거 실패: " + err.message);
    } finally {
        event.target.textContent = "🚫";
    }
}

// 일일동향 제외 토글 (excluded_articles.json에 저장)
async function toggleExcludeArticle(event, link) {
    event.stopPropagation();

    const item = articleData.find(a => a.link === link);
    if (!item) return;

    const isCurrentlyExcluded = excludedArticles.has(link);
    const confirmMsg = isCurrentlyExcluded
        ? `[제외 해제]\n\n기사 제목: ${item.title}\n출처: ${item.displayName}\n\n이 기사를 일일동향에 다시 포함시키겠습니까?`
        : `[일일동향 제외]\n\n기사 제목: ${item.title}\n출처: ${item.displayName}\n\nAI가 이 기사를 일일동향에 절대 포함하지 않도록 설정합니다.\n계속하시겠습니까?`;

    if (!confirm(confirmMsg)) return;

    const originalText = event.target.textContent;
    event.target.textContent = '⏳';

    const filePath = 'codes/favorites/excluded_articles.json';
    const getEndpoint = `repos/${OWNER}/${REPO}/contents/${filePath}`;

    try {
        let excludedData = [];
        let sha = null;

        // sha는 반드시 먼저 추출 (파일 존재 여부 확인)
        try {
            const getResData = await callProxyAPI(`${getEndpoint}?ref=${BRANCH}`, 'GET');
            if (getResData) {
                sha = getResData.sha; // 파일이 존재하면 sha 즉시 저장
                if (getResData.content) {
                    try {
                        excludedData = JSON.parse(base64ToUtf8(getResData.content));
                    } catch (parseErr) {
                        console.warn('excluded_articles.json 파싱 실패, 빈 배열로 초기화');
                        excludedData = [];
                    }
                }
            }
        } catch (e) {
            // 404: 파일이 없음 → sha=null로 새 파일 생성
            console.log('excluded_articles.json not found. Creating new one.');
        }

        if (isCurrentlyExcluded) {
            excludedData = excludedData.filter(d => d.link !== link);
            excludedArticles.delete(link);
        } else {
            excludedData.push({ title: item.title, link: item.link, site: item.displayName });
            excludedArticles.add(link);
        }

        const jsonString = JSON.stringify(excludedData, null, 2);
        const encodedContent = btoa(unescape(encodeURIComponent(jsonString)));

        const putBody = {
            message: `${isCurrentlyExcluded ? 'Remove' : 'Add'} excluded article: ${item.title}`,
            content: encodedContent,
            branch: BRANCH
        };
        if (sha) putBody.sha = sha; // 파일이 존재하는 경우만 sha 포함

        await callProxyAPI(getEndpoint, 'PUT', putBody);

        renderCurrentView();
        alert(isCurrentlyExcluded
            ? '✅ 제외가 해제되었습니다. 이 기사는 이제 일일동향 선정 대상에 포함됩니다.'
            : '✅ 제외 완료! AI가 이 기사를 일일동향에 포함하지 않습니다.');

    } catch (err) {
        console.error('Error toggling excluded article:', err);
        alert('❌ 실패: ' + err.message);
        // 롤백
        if (isCurrentlyExcluded) excludedArticles.add(link);
        else excludedArticles.delete(link);
    } finally {
        event.target.textContent = originalText;
    }
}

// FewShot 모드 토글 (사이드바 버튼)
async function toggleFewshotMode() {
    if (fewshotUnlocked) {
        // 이미 잠금 해제 상태 → 다시 잠금
        fewshotUnlocked = false;
        document.getElementById('fewshotModeBtn').style.background = '#555';
        document.getElementById('fewshotModeBtn').title = 'FewShot 학습 관리 (관리자 인증 필요)';
        renderCurrentView();
        return;
    }

    // 비밀번호 인증
    const isVerified = await verifyPassword();
    if (!isVerified) return;

    fewshotUnlocked = true;
    document.getElementById('fewshotModeBtn').style.background = '#e67e22';
    document.getElementById('fewshotModeBtn').title = 'FewShot 모드 활성화됨 (클릭하여 잠금)';
    renderCurrentView();
    alert("✅ FewShot 관리 모드가 활성화되었습니다.\n기사 목록에서 🧠(학습 추가) / 🚫(제외) 버튼이 표시됩니다.");
}

const debounce = (func, delay) => {
    return function (...args) {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => func.apply(this, args), delay);
    };
};
const debounceSearchArticles = debounce(renderCurrentView, 300);
const debounceSearchPublications = debounce(renderCurrentView, 300);

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            showTab(e.target.getAttribute('data-source'));
        });
    });
    loadData();
});

// -----------------------------------------------------
// 7. AI 자동 선정 (autoSelectFavoritesBtn)
// -----------------------------------------------------
document.getElementById('autoSelectFavoritesBtn').addEventListener('click', async function () {
    const message = "🤖 AI(Gemini) 자동 즐겨찾기 생성을 시작하시겠습니까?\n\n" +
        "✅ 어제(KST) 기사/간행물을 분석하여 자동 선정하고 분류합니다.\n" +
        "✅ 약 4분 이상 소요.(별도 알람❌) 이후 대시보드에서 바로 '텍스트추출'을 눌러 일일동향을 활용하세요.\n" +
        "⚠️ 수동 실행하지 않아도 매일 오전 6시경 자동 생성 합니다."

    if (!confirm(message)) return;

    // 비밀번호 확인 추가
    const isVerified = await verifyPassword();
    if (!isVerified) return;

    const WORKFLOW_ID = "auto_favorites.yml";
    const endpoint = `repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

    try {
        await callProxyAPI(endpoint, 'POST', { ref: "main" });
        alert("✅ 실행 요청 완료! 약 2분 뒤 데이터가 자동 업데이트됩니다.\n(새로고침 불필요)");
    } catch (error) {
        console.error('Error:', error);
        alert(`❌ 실행 실패: ${error.message}`);
    }
});

// -----------------------------------------------------
// 8. 즐겨찾기 JSON 업로드 (uploadFavoritesBtn)
// -----------------------------------------------------
document.getElementById('uploadFavoritesBtn').addEventListener('click', async function () {
    const files = [
        {
            type: "ARTICLE",
            path: "codes/favorites/favorite_articles.json",
            data: articleData.filter(item => favoriteArticles.has(item.link)).map(item => ({
                title: item.title, link: item.link, category: favoriteArticles.get(item.link)
            }))
        },
        {
            type: "PUBLICATION",
            path: "codes/favorites/favorite_publications.json",
            data: publicationData.filter(item => favoritePublications.has(item.link)).map(item => ({
                title: item.title, link: item.link, category: favoritePublications.get(item.link)
            }))
        }
    ];

    for (const file of files) {
        if (file.data.length === 0) continue;
        const jsonString = JSON.stringify(file.data, null, 2);
        const encodedContent = btoa(unescape(encodeURIComponent(jsonString)));

        try {
            let sha = null;
            const getEndpoint = `repos/${OWNER}/${REPO}/contents/${file.path}`;
            const getResData = await callProxyAPI(getEndpoint, 'GET').catch(() => null);
            if (getResData && getResData.sha) sha = getResData.sha;

            const putBody = {
                message: `update ${file.path}`,
                content: encodedContent,
                branch: BRANCH,
                ...(sha && { sha })
            };

            await callProxyAPI(getEndpoint, 'PUT', putBody);
            console.log(`✅ ${file.type} 저장 완료`);
        } catch (err) {
            console.error(`❌ ${file.type} 실패: ${err.message}`);
            alert(`${file.type} 저장 실패`);
        }
    }
    // alert("✅ 모든 데이터 업로드 완료");

    const WORKFLOW_ID = "json_to_txt.yml";
    const endpoint = `repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

    try {
        await callProxyAPI(endpoint, 'POST', { ref: "main" });
        alert("✅ 즐겨찾기에 있는 목록을 일일 동향 텍스트로 만듭니다.\n\n✅️ 약 30초 후 대시보드에서 '텍스트추출'을 누르세요.");
    } catch (error) {
        console.error('Error:', error);
        alert(`❌ 실패: ${error.message}`);
    }
});

// 사이드바 토글
document.getElementById('sidebarToggle').addEventListener('click', () => {
    const container = document.querySelector('.container');
    if (window.innerWidth <= 768) container.classList.toggle('sidebar-open');
    else container.classList.toggle('sidebar-collapsed');
});

// -----------------------------------------------------
// 9. 데이터 전체 삭제 (deleteCodesBtn)
// -----------------------------------------------------
document.getElementById('deleteCodesBtn').addEventListener('click', async function () {
    const confirmMsg = "⚠️ 경고 ⚠️\n모든 데이터를 삭제합니다.\n이 작업은 되돌릴 수 없습니다.\n정말 삭제하시겠습니까?";
    if (!confirm(confirmMsg)) return;

    try {
        const listEndpoint = `repos/${OWNER}/${REPO}/contents/codes`;
        const files = await callProxyAPI(listEndpoint, 'GET');

        if (!Array.isArray(files)) {
            throw new Error("파일 목록을 불러오지 못했습니다.");
        }

        const targetFiles = files.filter(file =>
            file.type === "file" && (file.name.endsWith(".json") || file.name.endsWith(".txt"))
        );

        if (targetFiles.length === 0) {
            alert("삭제할 데이터가 없습니다.");
            return;
        }

        for (const file of targetFiles) {
            const deleteBody = {
                message: `delete ${file.path}`,
                sha: file.sha,
                branch: BRANCH
            };
            const endpoint = `repos/${OWNER}/${REPO}/contents/${file.path}`;
            await callProxyAPI(endpoint, 'DELETE', deleteBody);
            console.log(`🗑 삭제 완료: ${file.name}`);
        }

        alert(`✅ 데이터 초기화 완료\n잠시후 페이지를 새로고침하세요.`);
    } catch (error) {
        console.error(error);
        alert("❌ 삭제 중 오류 발생: " + error.message);
    }
});
// -----------------------------------------------------
// 10. 오디오 생성 실행 (createAudioBtn) - Vercel Proxy 적용
// -----------------------------------------------------
document.getElementById('createAudioBtn').addEventListener('click', async function () {
    // 1. 사용자 확인 (토큰 검사는 Proxy가 처리하므로 제거)
    const message = "🎙️ AI 뉴스 브리핑 오디오를 생성하시겠습니까?\n(약 1~2분 소요됩니다)";
    if (!confirm(message)) return;

    // 비밀번호 확인 추가
    const isVerified = await verifyPassword();
    if (!isVerified) return;

    // 2. API 호출 준비
    const WORKFLOW_ID = "audio_gen.yml";
    const endpoint = `repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

    try {
        // 3. callProxyAPI를 통해 안전하게 요청 전송
        await callProxyAPI(endpoint, 'POST', { ref: "main" });

        alert("✅ 브리핑 생성 요청 성공!\nGemini가 대본을 쓰고 녹음 중입니다.\n약 1분 뒤 페이지를 새로고침하여 들어보세요.");
    } catch (error) {
        console.error('Error:', error);
        alert(`❌ 실패: ${error.message}`);
    }
});


// 11. 최근업데이트 불러오기

async function loadCompletionTime() {
    try {
        const response = await fetch('public/update_time.json?t=' + new Date().getTime());

        if (!response.ok) {
            throw new Error('시간 정보를 불러올 수 없습니다.');
        }

        const data = await response.json();
        const timeElement = document.getElementById('workflow-completed-time');
        if (timeElement) {
            timeElement.innerText = data.completed_at;
        }
    } catch (error) {
        console.error(error);
        const timeElement = document.getElementById('workflow-completed-time');
        if (timeElement) {
            timeElement.innerText = "시간 정보 없음";
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadCompletionTime();
});


// -----------------------------------------------------
// 12. 맨 위로 가기 (Top) 버튼 및 모바일 사이드바 제어
// -----------------------------------------------------
const scrollTopBtn = document.getElementById("scrollTopBtn");

window.onscroll = function () {
    if (document.body.scrollTop > 200 || document.documentElement.scrollTop > 200) {
        scrollTopBtn.style.display = "block";
    } else {
        scrollTopBtn.style.display = "none";
    }
};


if (scrollTopBtn) {
    scrollTopBtn.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            document.querySelector('.container').classList.remove('sidebar-open');
        }
    });
});
