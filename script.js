// -----------------------------------------------------
// 1. 설정 및 공통 함수 (토큰 관련 코드 제거됨)
// -----------------------------------------------------
const OWNER = "jhjhc1483";
const REPO = "AI_Trend_Analysis_vercel";
const BRANCH = "main";

// ★ 핵심: GitHub API 대신 Vercel Serverless Function을 호출하는 함수
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

// -----------------------------------------------------
// 2. 기사 업데이트 실행 (runActionBtn)
// -----------------------------------------------------
document.getElementById('runActionBtn').addEventListener('click', async function() {
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

// 닫기 및 복사 버튼
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
// 4. 텍스트 추출 실행 (runActionBtn2)
// -----------------------------------------------------
document.getElementById('runActionBtn2').addEventListener('click', async function() {
    const WORKFLOW_ID = "json_to_txt.yml";
    const endpoint = `repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

    try {
        await callProxyAPI(endpoint, 'POST', { ref: "main" });
        alert("✅ 즐겨찾기에 있는 목록을 일일 동향을 텍스트로 만듭니다.\n\n약 30초 후 페이지를 새로고침 하고 대시보드에서 \n'텍스트추출'을 누르세요.");
    } catch (error) {
        console.error('Error:', error);
        alert(`❌ 실패: ${error.message}`);
    }
});

// -----------------------------------------------------
// 5. 전역 변수 및 데이터 로드 (기존 로직 유지)
// -----------------------------------------------------
let articleData = [];
let publicationData = [];
let allDataLoaded;
let debounceTimeout;
let currentView = 'HOME';
let favoriteArticles = new Map();
let favoritePublications = new Map(); 
const cacheBuster = `?t=${new Date().getTime()}`;

const FILES_TO_LOAD = [
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

    const promises = FILES_TO_LOAD.map(file => {
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
    });

    Promise.all(promises)
        .then(results => {
            results.forEach(siteData => {
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
// 6. UI/UX 렌더링 및 헬퍼 함수들 (기존 로직 유지)
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
    const isArticleView = sourceName.includes('ARTICLE') || ['AITIMES', 'ETNEWS', 'AINEWS', 'MND', 'kookbang', 'DAPA', 'MSIT'].includes(sourceName);
    const isPublicationView = sourceName.includes('PUBLICATION') || ['NIA', 'IITP','STEPI', 'NIPA', 'KISDI', 'KISTI','KISA','TTA'].includes(sourceName);

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
    document.getElementById('stat-articles').textContent = articleData.length;
    document.getElementById('stat-publications').textContent = publicationData.length;
    document.getElementById('stat-fav-articles').textContent = favoriteArticles.size;
    document.getElementById('stat-fav-publications').textContent = favoritePublications.size;

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
    const isArticle = sourceName.includes('ARTICLE') || ['AITIMES', 'ETNEWS', 'AINEWS', 'MND', 'kookbang', 'DAPA', 'MSIT'].includes(sourceName);
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
            else colorClass = 'cat-etc';
        } else {
            colorClass = 'cat-pub';
        }
        categoryBadge = `<span class="category-badge ${colorClass}">${savedCat}</span>`;
    }

    return `
        <li class="article-item">
            <button class="favorite-btn ${isFavorite ? 'is-favorite' : ''}" onclick="toggleFavorite(event, '${item.link}', ${item.isArticle})">${isFavorite ? '★' : '☆'}</button>
            <div class="article-title-group">
                <a href="#" class="article-title" onclick="openPopup('${item.link}', '${item.title}'); return false;">${item.title}</a>
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
            let cat = prompt("카테고리 (국방, 육군, 민간, 기관, 기타)", "");
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
    if (currentView === 'HOME') {
        document.getElementById(isArticle ? 'stat-fav-articles' : 'stat-fav-publications').textContent = isArticle ? favoriteArticles.size : favoritePublications.size;
    }
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

const debounce = (func, delay) => {
    return function(...args) {
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
// 7. 즐겨찾기 JSON 업로드 (uploadFavoritesBtn)
// -----------------------------------------------------
document.getElementById('uploadFavoritesBtn').addEventListener('click', async function() {
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
            // 1. SHA 조회
            let sha = null;
            const getEndpoint = `repos/${OWNER}/${REPO}/contents/${file.path}`;
            const getResData = await callProxyAPI(getEndpoint, 'GET').catch(() => null);
            if (getResData && getResData.sha) sha = getResData.sha;

            // 2. 파일 업로드 (PUT)
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
    alert("✅ 모든 데이터 업로드 완료");
});

// 사이드바 토글
document.getElementById('sidebarToggle').addEventListener('click', () => {
    const container = document.querySelector('.container');
    if (window.innerWidth <= 768) container.classList.toggle('sidebar-open');
    else container.classList.toggle('sidebar-collapsed');
});

// -----------------------------------------------------
// 8. 데이터 전체 삭제 (deleteCodesBtn)
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
// script.js 하단에 추가

document.getElementById('createAudioBtn').addEventListener('click', async function() {
    if (!token) {
        alert("토큰이 입력되지 않았습니다.");
        return;
    }

    // 사용자 확인
    if (!confirm("🎙️ AI 뉴스 브리핑 오디오를 생성하시겠습니까?\n(약 1~2분 소요됩니다)")) {
        return;
    }

    const WORKFLOW_ID = "audio_gen.yml"; // 위에서 만든 워크플로우 파일명
    const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;

    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                "Authorization": `token ${token}`,
                "Accept": "application/vnd.github.v3+json",
            },
            body: JSON.stringify({ ref: "main" })    
        }); 

        if (res.status === 204) {
            alert("✅ 브리핑 생성 요청 성공!\nGemini가 대본을 쓰고 녹음 중입니다.\n약 1분 뒤 페이지를 새로고침하여 들어보세요.");
        } else {
            const errorData = await res.json();
            alert(`❌ 실패: ${res.status}\n메시지: ${errorData.message}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert("네트워크 오류가 발생했습니다.");
    }
});