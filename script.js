// -----------------------------------------------------
// 1. 설정 및 초기화 (토큰/OWNER 변수 삭제됨)
// -----------------------------------------------------
// Vercel 서버가 환경변수를 관리하므로 클라이언트에는 토큰이 필요 없습니다.

document.getElementById('runActionBtn').addEventListener('click', async function() {
    const message = "⚠️기사 업데이트를 진행하시겠습니까?⚠️\n\n" +
                "✅기사는 지정된 시간에 맞춰 자동으로 업데이트 됩니다.\n" +
                "✅수동으로 기사 업데이트 시 최소 5분 이상의 시간이 소요 됩니다.";

    if (!confirm(message)) return;

    try {
        // [변경됨] 내 Vercel API 호출
        const res = await fetch('/api/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ workflowId: "main.yml" })
        });

        if (res.ok) {
            alert("✅ 실행 성공! 최소 5분의 시간이 소요 됩니다.\n페이지를 새로고침 하세요.");
        } else {
            const err = await res.json();
            alert(`❌ 실패: ${err.message || '오류 발생'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert("네트워크 오류가 발생했습니다.");
    }
});

// data.txt 팝업 띄우기
const popup = document.getElementById('popup');
const overlay = document.getElementById('overlay');
const contentDiv = document.getElementById('popupContent');

const PATH = "codes/data.txt";
function base64ToUtf8(base64) {
    // 줄바꿈 제거 후 디코딩
    const binary = atob(base64.replace(/\n/g, ""));
    const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
    return new TextDecoder("utf-8").decode(bytes);
}

document.getElementById('loadFileBtn').addEventListener('click', async () => {
    try {
        // [변경됨] 내 Vercel API 호출 (GET)
        const res = await fetch(`/api/file?path=${PATH}`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        
        const data = await res.json();
        const text = base64ToUtf8(data.content);            
        contentDiv.textContent = text;
        popup.style.display = 'block';
        overlay.style.display = 'block';
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

// 텍스트 추출 액션 실행
document.getElementById('runActionBtn2').addEventListener('click', async function() {
    try {
        // [변경됨] 내 Vercel API 호출
        const res = await fetch('/api/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ workflowId: "json_to_txt.yml" })
        });
        
        if (res.ok) {
            alert("✅ 즐겨찾기에 있는 목록을 일일 동향을 텍스트로 만듭니다.\n\n약 30초 후 페이지를 새로고침 하고 대시보드에서 \n'텍스트추출'을 누르세요.");
        } else {
            const err = await res.json();
            alert(`❌ 실패: ${err.message || '오류 발생'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert("네트워크 오류가 발생했습니다.");
    }
});

// -----------------------------------------------------
// 데이터 로드 로직 (기존 유지하되 fetch 경로 확인)
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

// loadData 함수는 기존에 json 파일을 직접 fetch하므로 수정 불필요 
// (단, codes 폴더가 public에 있어야 함. Vercel 배포시 루트에 있으면 접근 가능)
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
        return fetch(file.url)
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load`);
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
            console.log(`데이터 로드 완료: 기사 ${articleData.length}, 간행물 ${publicationData.length}`);
            showTab('HOME');
        })
        .catch(error => console.error("Critical error:", error));
}

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
    
    const filtered = sortData(data, sortBy);
    const listContainer = document.getElementById('data-list-container');
    const noDataMsg = document.getElementById('no-data');

    if (filtered.length === 0) {
        listContainer.innerHTML = '';
        noDataMsg.style.display = 'block';
        noDataMsg.textContent = searchTerm ? `검색어 "${searchTerm}" 결과 없음` : `데이터가 없습니다.`;
    } else {
        listContainer.innerHTML = filtered.map(item => createListItem(item)).join('');
        noDataMsg.style.display = 'none';
    }
}

function createListItem(item) {
    const timeInfo = (item.시 && item.분) ? `${item.시.padStart(2, '0')}:${item.분.padStart(2, '0')}` : '';
    const fullDate = `${item.년}.${item.월}.${item.일} ${timeInfo}`;
    let isFavorite = item.isArticle ? favoriteArticles.has(item.link) : favoritePublications.has(item.link);
    let categoryBadge = '';

    if (isFavorite) {
        const savedCat = item.isArticle ? favoriteArticles.get(item.link) : favoritePublications.get(item.link);
        let colorClass = 'cat-default';
        if (item.isArticle) {
            if (savedCat === '국방') colorClass = 'cat-defense';
            else if (savedCat === '육군') colorClass = 'cat-army';
            else if (savedCat === '민간') colorClass = 'cat-civil';
            else if (savedCat === '기타') colorClass = 'cat-etc';
        } else {
            colorClass = 'cat-pub';
        }
        categoryBadge = `<span class="category-badge ${colorClass}">${savedCat}</span>`;
    }

    const favIcon = isFavorite ? '★' : '☆';
    const favClass = isFavorite ? 'is-favorite' : '';
    
    return `
        <li class="article-item">
            <button class="favorite-btn ${favClass}" onclick="toggleFavorite(event, '${item.link}', ${item.isArticle})">${favIcon}</button>
            <div class="article-title-group">
                <a href="#" class="article-title" onclick="openPopup('${item.link}', '${item.title}'); return false;">
                    ${item.title}
                </a>
                ${categoryBadge} <div class="article-meta">
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
    let isFav;
    if (isArticle) {
        isFav = favoriteArticles.has(link);
        if (isFav) favoriteArticles.delete(link);
        else {
            let cat = prompt("카테고리 입력 (국방, 육군, 민간, 기관, 기타)", "") || "기타";
            favoriteArticles.set(link, cat.trim() || "기타");
        }
        localStorage.setItem('favoriteArticles', JSON.stringify(Array.from(favoriteArticles.entries())));
    } else {
        isFav = favoritePublications.has(link);
        if (isFav) favoritePublications.delete(link);
        else favoritePublications.set(link, "간행물");
        localStorage.setItem('favoritePublications', JSON.stringify(Array.from(favoritePublications.entries())));
    }
    renderCurrentView();
}

function clearFavorites(type) {
    if (!confirm('즐겨찾기를 모두 삭제하시겠습니까?')) return;
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
    else alert(`"${title}"의 링크 정보가 없습니다.`);
}

function debounce(func, delay) {
    return function(...args) {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => func.apply(this, args), delay);
    };
}
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

// ----------------------------------------------------------------------
// [중요 변경] 즐겨찾기 저장 로직 (Vercel API 사용)
// ----------------------------------------------------------------------
document.getElementById('uploadFavoritesBtn').addEventListener('click', async function() {
    const files = [
        {
            type: "ARTICLE",
            path: "codes/favorites/favorite_articles.json",
            data: articleData.filter(item => favoriteArticles.has(item.link))
                      .map(item => ({ title: item.title, link: item.link, category: favoriteArticles.get(item.link) }))
        },
        {
            type: "PUBLICATION",
            path: "codes/favorites/favorite_publications.json",
            data: publicationData.filter(item => favoritePublications.has(item.link))
                      .map(item => ({ title: item.title, link: item.link, category: favoritePublications.get(item.link) }))
        }
    ];

    for (const file of files) {
        if (file.data.length === 0) continue;

        const jsonString = JSON.stringify(file.data, null, 2);
        const encodedContent = btoa(unescape(encodeURIComponent(jsonString)));

        try {
            // 1. 기존 파일의 SHA 값을 가져오기 위해 GET 요청
            const checkRes = await fetch(`/api/file?path=${file.path}`);
            let sha = null;
            if (checkRes.ok) {
                const checkData = await checkRes.json();
                sha = checkData.sha;
            }

            // 2. PUT 요청으로 파일 업로드
            const putRes = await fetch('/api/file', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: file.path,
                    message: `update ${file.path}`,
                    content: encodedContent,
                    sha: sha // 기존 파일이 있으면 sha 포함
                })
            });

            if (putRes.ok) console.log(`✅ ${file.type} 저장 완료`);
            else {
                const err = await putRes.json();
                console.error(`❌ 업로드 실패: ${err.message}`);
            }
        } catch (e) {
            console.error("업로드 중 에러", e);
        }
    }
    alert("✅ 데이터 업로드 로직 수행 완료");
});

// 사이드바 토글
const sidebarToggle = document.getElementById('sidebarToggle');
const container = document.querySelector('.container');
sidebarToggle.addEventListener('click', () => {
    if (window.innerWidth <= 768) container.classList.toggle('sidebar-open');
    else container.classList.toggle('sidebar-collapsed');
});

// ----------------------------------------------------------------------
// [중요 변경] 데이터 삭제 로직 (Vercel API 사용)
// ----------------------------------------------------------------------
document.getElementById('deleteCodesBtn').addEventListener('click', async function () {
    const confirmMsg = "⚠️ 경고: 모든 데이터를 삭제합니다. 이 작업은 되돌릴 수 없습니다.";
    if (!confirm(confirmMsg)) return;

    const folderPath = "codes"; 

    try {
        // 1. codes 폴더 목록 가져오기 (GET)
        const res = await fetch(`/api/file?path=${folderPath}`);
        if (!res.ok) {
            alert("❌ codes 폴더를 불러오지 못했습니다.");
            return;
        }
        const files = await res.json();
        const targetFiles = files.filter(file => file.type === "file" && (file.name.endsWith(".json") || file.name.endsWith(".txt")));

        if (targetFiles.length === 0) {
            alert("삭제할 데이터가 없습니다.");
            return;
        }

        // 2. 파일 개별 삭제 (DELETE)
        for (const file of targetFiles) {
            const deleteRes = await fetch('/api/file', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: file.path,
                    sha: file.sha,
                    message: `delete ${file.path}`
                })
            });

            if (deleteRes.ok) console.log(`🗑 삭제 완료: ${file.name}`);
            else console.error(`❌ 삭제 실패: ${file.name}`);
        }

        alert(`✅ 데이터 초기화 완료\n잠시후 페이지를 새로고침하세요.`);
    } catch (error) {
        console.error(error);
        alert("❌ 삭제 중 오류 발생");
    }
});