// const token = "github_pat_***REMOVED***" + prompt("⚠️코드를 입력하세요.\n입력한 코드는 저장되지 않습니다.\n코드를 모르면 'ESC'키를 누르세요.");    
const OWNER = "jhjhc1483";
const REPO = "AI_Trend_Analysis";
const BRANCH = "main";
document.getElementById('runActionBtn').addEventListener('click', async function() {

// if (!token) {
//     alert("토큰이 입력되지 않았습니다.");
//     return;
// }
async function getWeather() {
    // 내 Vercel 서버로 요청 (키가 필요 없음)
    const response = await fetch('/api/getData?city=Seoul');
    const data = await response.json();
    
    console.log(data); // 결과 확인
  }
  
  getWeather();
token = data
const message = "⚠️기사 업데이트를 진행하시겠습니까?⚠️\n\n" +
            "✅기사는 지정된 시간에 맞춰 자동으로 업데이트 됩니다.\n" +
            "✅수동으로 기사 업데이트 시 최소 5분 이상의 시간이 소요 됩니다.";

if (!confirm(message)) {
    // '아니오(취소)'를 클릭한 경우 함수 종료
    return;
}
const WORKFLOW_ID = "main.yml";
const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;
try {
    const res1 = await fetch(url, {
        method: 'POST',
        headers: {
            "Authorization": `token ${token}`,
            "Accept": "application/vnd.github.v3+json",
        },
        body: JSON.stringify({ ref: "main" })    
    }); 
    if (res1.status === 204) {
        alert("✅ 실행 성공! 최소 5분의 시간이 소요 됩니다.\n페이지를 새로고침 하세요.");
    } else if (res1.status === 401) {
        alert("❌ 실패: 토큰이 유효하지 않습니다. (401 Unauthorized)");
    } else if (res1.status === 404) {
        alert("❌ 실패: 저장소나 워크플로우를 찾을 수 없습니다. (404 Not Found)");
    } else {
        const errorData = await res1.json();
        alert(`❌ 실패: ${res1.status}\n메시지: ${errorData.message}`);
    }
} catch (error) {
    console.error('Error:', error);
    alert("네트워크 오류가 발생했습니다.");
}
});

//github 레포에 있는 data.txt를 그대로 긁어와서 팝업창에 띄우기
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
    
    const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${PATH}?ref=${BRANCH}`;
    const headers = token ? { Authorization: `token ${token}` } : {};
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    
    const data = await res.json();
    // 한글 깨짐 없이 디코딩
    const text = base64ToUtf8(data.content);            
    contentDiv.textContent = text; // 내용 표시
    popup.style.display = 'block';
    overlay.style.display = 'block';
    console.log(text);
} catch (error) {
    console.error(error);
    alert("파일을 불러오는 중 오류 발생: " + error.message);
}
});

// 닫기 버튼
document.getElementById('closeBtn').addEventListener('click', () => {
popup.style.display = 'none';
overlay.style.display = 'none';
});

// 복사 버튼
document.getElementById('copyBtn2').addEventListener('click', () => {
navigator.clipboard.writeText(contentDiv.textContent)
    .then(() => alert("복사 완료!"))
    .catch(err => alert("복사 실패: " + err));
});
document.getElementById('runActionBtn2').addEventListener('click', async function() {

if (!token) {
alert("토큰이 입력되지 않았습니다.");
return;
}
const WORKFLOW_ID = "json_to_txt.yml";
const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_ID}/dispatches`;
try {
const res2 = await fetch(url, {
    method: 'POST',
    headers: {
        "Authorization": `token ${token}`,
        "Accept": "application/vnd.github.v3+json",
    },
    body: JSON.stringify({ ref: "main" })    
});        
if (res2.status === 204) {
    alert("✅ 즐겨찾기에 있는 목록을 일일 동향을 텍스트로 만듭니다.\n\n약 30초 후 페이지를 새로고침 하고 대시보드에서 \n'텍스트추출'을 누르세요.");
} else if (res2.status === 401) {
    alert("❌ 실패: 토큰이 유효하지 않습니다. (401 Unauthorized)");
} else if (res2.status === 404) {
    alert("❌ 실패: 저장소나 워크플로우를 찾을 수 없습니다. (404 Not Found)");
} else {
    const errorData = await res2.json();
    alert(`❌ 실패: ${res2.status}\n메시지: ${errorData.message}`);
}
} catch (error) {
console.error('Error:', error);
alert("네트워크 오류가 발생했습니다.");
}
});


// -----------------------------------------------------
// 1. 전역 변수 설정 및 데이터 로드 파일 정의
// -----------------------------------------------------
// -----------------------------------------------------
let articleData = []; // 기사 데이터 (AI Times, ETNEWS, AINEWS, MND, kookbang, DAPA, MSIT)
let publicationData = []; // 간행물 데이터 (NIA, IITP, STEPI, NIPA, KISDI, KISTI, KISA, TTA)
let allDataLoaded;
let debounceTimeout;
let currentView = 'HOME'; // 현재 활성화된 뷰

// 즐겨찾기 상태 저장 변수
let favoriteArticles = new Map();
let favoritePublications = new Map(); 

// 캐시 방지를 위한 타임스탬프 생성
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

// -----------------------------------------------------
// 2. 데이터 로딩 함수
// -----------------------------------------------------
function loadData() {
    // 로컬 스토리지에서 즐겨찾기 로드
    const favArticlesStr = localStorage.getItem('favoriteArticles');
    const favPublicationsStr = localStorage.getItem('favoritePublications');
    
    // 기사 즐겨찾기 로드 (하위 호환성 처리 및 Map 변환)
    if (favArticlesStr) {
        const parsed = JSON.parse(favArticlesStr);
        if (Array.isArray(parsed) && parsed.length > 0 && Array.isArray(parsed[0])) {
            // 신규 방식: [[link, category], ...] 형태의 배열
            favoriteArticles = new Map(parsed);
        } else if (Array.isArray(parsed)) {
            // 구 방식: ['link1', 'link2'] 형태의 배열 -> 카테고리 '기타'로 초기화
            favoriteArticles = new Map(parsed.map(link => [link, '기타']));
        }
    }

    // 간행물 즐겨찾기 로드 (하위 호환성 처리 및 Map 변환)
    if (favPublicationsStr) {
        const parsed = JSON.parse(favPublicationsStr);
        if (Array.isArray(parsed) && parsed.length > 0 && Array.isArray(parsed[0])) {
            // 신규 방식: [[link, category], ...] 형태의 배열
            favoritePublications = new Map(parsed);
        } else if (Array.isArray(parsed)) {
            // 구 방식: ['link1', 'link2'] 형태의 배열 -> 카테고리 '기타'로 초기화
            favoritePublications = new Map(parsed.map(link => [link, '기타']));
        }
    }            

    const promises = FILES_TO_LOAD.map(file => {
        return fetch(file.url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to load ${file.url}: ${response.statusText}`);
                }
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
                    if (siteData[0].isArticle) {
                        articleData = articleData.concat(siteData);
                    } else {
                        publicationData = publicationData.concat(siteData);
                    }
                }
            });

            allDataLoaded = true;
            console.log(`총 ${articleData.length}개의 기사 데이터와 ${publicationData.length}개의 간행물 데이터 로드 완료.`);
            
            showTab('HOME');
        })
        .catch(error => {
            console.error("Critical error in Promise.all:", error);
            document.getElementById('no-data').textContent = "데이터 로드 중 치명적인 오류 발생.";
        });
}

// -----------------------------------------------------
// 3. 정렬 함수
// -----------------------------------------------------
function sortData(data, sortBy) {
    const sortedData = [...data];

    sortedData.sort((a, b) => {
        const getDateString = (item) => `${item.년 || '0000'}${item.월 || '00'}${item.일 || '00'}${item.시 || '00'}${item.분 || '00'}`;
        const dateA = getDateString(a);
        const dateB = getDateString(b);
        const titleA = a.title;
        const titleB = b.title;
        const siteA = a.site;
        const siteB = b.site;
        const categoryA = a.category;
        const categoryB = b.category;

        switch (sortBy) {
            case 'date_asc': return dateA.localeCompare(dateB);
            case 'date_desc': return dateB.localeCompare(dateA);
            case 'title_asc': return titleA.localeCompare(titleB);
            case 'site_asc': 
                if (siteA !== siteB) return siteA.localeCompare(siteB);
                return dateB.localeCompare(dateA);
            case 'category_asc': 
                if (categoryA !== categoryB) return categoryA.localeCompare(categoryB);
                return dateB.localeCompare(dateA);
            default: return 0;
        }
    });
    return sortedData;
}


// -----------------------------------------------------
// 4. 탭 전환 및 렌더링 함수
// -----------------------------------------------------
function showTab(sourceName) {
    currentView = sourceName;
    
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeTab = document.querySelector(`.tab-button[data-source="${sourceName}"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }

    const isHome = sourceName === 'HOME';
    const isArticleView = sourceName.includes('ARTICLE') || ['AITIMES', 'ETNEWS', 'AINEWS', 'MND', 'kookbang', 'DAPA', 'MSIT'].includes(sourceName);
    const isPublicationView = sourceName.includes('PUBLICATION') || ['NIA', 'IITP','STEPI', 'NIPA', 'KISDI', 'KISTI','KISA','TTA'].includes(sourceName);

    document.getElementById('dashboard-view').style.display = isHome ? 'block' : 'none';
    document.getElementById('list-view').style.display = isHome ? 'none' : 'block';

    document.getElementById('article-controls').style.display = isArticleView ? 'flex' : 'none';
    document.getElementById('publication-controls').style.display = isPublicationView ? 'flex' : 'none';
    
    document.getElementById('main-content-title').textContent = activeTab ? activeTab.textContent.replace(/^(🏠|📰|⭐️|📚) /, '') : 'AI 동향 분석';

    if (isHome) {
        renderDashboard();
    } else {
        renderList(sourceName);
    }
}

function renderCurrentView() {
    showTab(currentView);
}

// -----------------------------------------------------
// 5. 대시보드 렌더링 함수
// -----------------------------------------------------
function renderDashboard() {
    // 통계 업데이트
    document.getElementById('stat-articles').textContent = articleData.length;
    document.getElementById('stat-publications').textContent = publicationData.length;
    document.getElementById('stat-fav-articles').textContent = favoriteArticles.size;
    document.getElementById('stat-fav-publications').textContent = favoritePublications.size;

    // 최신 기사 5개
    const sortedArticles = sortData(articleData, 'date_desc');
    const latestArticles = sortedArticles.slice(0, 5);
    document.getElementById('latest-articles').innerHTML = latestArticles.map(item => `
        <li class="latest-item">
            <a href="#" onclick="openPopup('${item.link}', '${item.title}'); return false;">${item.title}</a>
            <span>${item.displayName} | ${item.년}.${item.월}.${item.일}</span>
        </li>
    `).join('');

    // 최신 간행물 5개
    const sortedPublications = sortData(publicationData, 'date_desc');
    const latestPublications = sortedPublications.slice(0, 5);
    document.getElementById('latest-publications').innerHTML = latestPublications.map(item => `
        <li class="latest-item">
            <a href="#" onclick="openPopup('${item.link}', '${item.title}'); return false;">${item.title}</a>
            <span>${item.displayName} | ${item.년}.${item.월}.${item.일}</span>
        </li>
    `).join('');
}

// -----------------------------------------------------
// 6. 목록 렌더링 함수 (기사 및 간행물 공통)
// -----------------------------------------------------
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
        
        if (isFav) {
            // 즐겨찾기 기사 필터링 (Map 사용)
            data = articleData.filter(a => favoriteArticles.has(a.link));
        } else if (isAll) {
            data = articleData;
        } else {
            data = articleData.filter(a => a.site === sourceName);
        }
    } else { // Publication
        sortBy = document.getElementById('sort-by-publication').value;
        searchTerm = document.getElementById('search-term-publication').value.toLowerCase();
        dataLabel = '간행물';

        if (isFav) {
            // 즐겨찾기 간행물 필터링 (Set 사용)
            data = publicationData.filter(p => favoritePublications.has(p.link));
        } else if (isAll) {
            data = publicationData;
        } else {
            data = publicationData.filter(p => p.site === sourceName);
        }
    }

    if (searchTerm) {
        data = data.filter(item => item.title.toLowerCase().includes(searchTerm));
    }

    const filteredAndSortedData = sortData(data, sortBy);
    const listContainer = document.getElementById('data-list-container');
    const noDataMsg = document.getElementById('no-data');

    if (filteredAndSortedData.length === 0) {
        listContainer.innerHTML = '';
        noDataMsg.style.display = 'block';
        noDataMsg.textContent = searchTerm 
            ? `검색어 "${searchTerm}"에 해당하는 ${dataLabel}가(이) 없습니다.` 
            : `${document.querySelector(`.tab-button[data-source="${sourceName}"]`).textContent.replace(/^(📰|⭐️|📚) /, '')} ${dataLabel} 데이터가 없습니다.`;
    } else {
        listContainer.innerHTML = filteredAndSortedData.map(item => createListItem(item)).join('');
        noDataMsg.style.display = 'none';
    }
}

function createListItem(item) {
    const timeInfo = (item.시 && item.분) 
        ? `${item.시.padStart(2, '0')}:${item.분.padStart(2, '0')}` 
        : '';
    const fullDate = `${item.년}.${item.월}.${item.일} ${timeInfo}`;

    // 즐겨찾기 여부 확인
    let isFavorite = false;
    let categoryBadge = '';

    if (item.isArticle) {
        isFavorite = favoriteArticles.has(item.link);
        // 기사이고 즐겨찾기 된 경우, 카테고리 뱃지 생성
        if (isFavorite) {
            const savedCat = favoriteArticles.get(item.link);
            // let colorClass = 'cat-etc'; // 기본값 (기타/노랑)

            // 카테고리별 색상 지정
            if (savedCat === '국방') colorClass = 'cat-defense';
            else if (savedCat === '육군') colorClass = 'cat-army';
            else if (savedCat === '민간') colorClass = 'cat-civil';
            else if (savedCat === '기타') colorClass = 'cat-etc';
            else colorClass = 'cat-default'; // 입력값이 정확히 일치하지 않아도 기타 처리 혹은 그대로 표시

            categoryBadge = `<span class="category-badge ${colorClass}">${savedCat}</span>`;
        }
    } else {
        isFavorite = favoritePublications.has(item.link);
        if(isFavorite) {
            const savedCat = favoritePublications.get(item.link);
            let colorClass = 'cat-pub';
            categoryBadge = `<span class="category-badge ${colorClass}">${savedCat}</span>`;
        }
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

// -----------------------------------------------------
// 7. 즐겨찾기 토글 함수 (카테고리 지정 기능 추가)
// -----------------------------------------------------
function toggleFavorite(event, link, isArticle) {
    event.stopPropagation();
    const btn = event.currentTarget;
    let isFav;

    if (isArticle) {
        isFav = favoriteArticles.has(link);
        if (isFav) {
            // 이미 즐겨찾기 됨 -> 삭제
            favoriteArticles.delete(link);
        } else {
            // 즐겨찾기 추가 -> 카테고리 입력 받기
            let categoryInput = prompt("카테고리를 입력하세요 (국방, 육군, 민간, 기관, 기타)", "");
            
            // 취소 버튼을 누른 경우 아무 동작 안 함
            if (categoryInput === null) return;
            
            // 공백 제거
            categoryInput = categoryInput.trim();
            
            // 입력값이 비어있으면 '기타'로 처리
            if (categoryInput === "") categoryInput = "기타";

            favoriteArticles.set(link, categoryInput);
        }
        // Map을 Array로 변환하여 저장
        localStorage.setItem('favoriteArticles', JSON.stringify(Array.from(favoriteArticles.entries())));
    } else {
        // 간행물 (카테고리 지정 없음)
        isFav = favoritePublications.has(link);
        if (isFav) {
            favoritePublications.delete(link);
        } else {
            favoritePublications.set(link, "간행물");
        }
        localStorage.setItem('favoritePublications', JSON.stringify(Array.from(favoritePublications.entries())));
    }

    // UI 업데이트: 즉시 뷰 갱신
    // 즐겨찾기 목록이거나, 뱃지 표시를 위해 전체 뷰도 갱신 필요
    renderCurrentView();

    // 대시보드 통계 업데이트 (뷰가 HOME일 때)
    if (currentView === 'HOME') {
        document.getElementById(isArticle ? 'stat-fav-articles' : 'stat-fav-publications').textContent = isArticle ? favoriteArticles.size : favoritePublications.size;
    }
}

function clearFavorites(type) {
    if (!confirm(`${type === 'ARTICLE' ? '기사' : '간행물'} 즐겨찾기를 모두 삭제하시겠습니까?`)) return;
    if (type === 'ARTICLE') {
        favoriteArticles.clear();
        localStorage.setItem('favoriteArticles', JSON.stringify([]));
    } else {
        favoritePublications.clear();
        localStorage.setItem('favoritePublications', JSON.stringify([]));
    }
    renderCurrentView();
}   

// -----------------------------------------------------
// 8. 유틸리티 함수
// -----------------------------------------------------
function openPopup(link, title) {
        if (link && link !== '#') {
            window.open(link, '_blank');
        } else {
            alert(`"${title}"의 링크 정보가 없습니다.`);
        }
}

function debounce(func, delay) {
    return function(...args) {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}
const debounceSearchArticles = debounce(renderCurrentView, 300);
const debounceSearchPublications = debounce(renderCurrentView, 300);

// -----------------------------------------------------
// 9. 이벤트 리스너 및 초기화
// -----------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            showTab(e.target.getAttribute('data-source'));
        });
    });

    loadData();
});

//github에 즐겨찾기에 있는 목록을 json으로 저장
document.getElementById('uploadFavoritesBtn').addEventListener('click', async function() {

    // 두 가지 타입 처리
    const files = [
        {
            type: "ARTICLE",
            path: "codes/favorites/favorite_articles.json",
            data: articleData
                .filter(item => favoriteArticles.has(item.link))
                .map(item => ({
                    title: item.title,
                    link: item.link,
                    category: favoriteArticles.get(item.link)
                }))
        },
        {
            type: "PUBLICATION",
            path: "codes/favorites/favorite_publications.json",
            data: publicationData
                .filter(item => favoritePublications.has(item.link))
                .map(item => ({
                    title: item.title,
                    link: item.link,
                    category: favoritePublications.get(item.link)
                }))
        }
    ];

    for (const file of files) {
        if (file.data.length === 0) {
            console.log(`${file.type} 업로드할 데이터 없음, 건너뜀`);
            continue;
        }

        const jsonString = JSON.stringify(file.data, null, 2);
        const encodedContent = btoa(unescape(encodeURIComponent(jsonString)));

        // 기존 파일 SHA 조회
        let sha = null;
        const getUrl = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${file.path}`;
        const getRes = await fetch(getUrl, {
            headers: { Authorization: `Bearer ${token}` }
        });
        if (getRes.ok) {
            const fileData = await getRes.json();
            sha = fileData.sha;
        }

        // 파일 업로드 (PUT)
        const putRes = await fetch(getUrl, {
            method: "PUT",
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: `update ${file.path}`,
                content: encodedContent,
                branch: BRANCH,
                ...(sha && { sha })
            })
        });

        if (putRes.ok) {
            console.log(`✅ ${file.type} JSON 파일 저장 완료`);
        } else {
            const err = await putRes.json();
            console.error(`❌ ${file.type} 업로드 실패: ${err.message}`);
        }
    }

    alert("✅ 모든 데이터 업로드 완료");
});

    //로컬로 즐겨찾기에 있는 목록을 json으로 추출하는 함수(안쓰고 있음)
function exportFavoritesToJSON(type) {
    let data = [];

    if (type === 'ARTICLE') {
        data = articleData
            .filter(item => favoriteArticles.has(item.link))
            .map(item => ({
                title: item.title,
                link: item.link,
                category: favoriteArticles.get(item.link)
            }));
    } else {
        data = publicationData
            .filter(item => favoritePublications.has(item.link))
            .map(item => ({
                title: item.title,
                link: item.link,
                category: favoritePublications.get(item.link)
            }));
    }

    if (data.length === 0) {
        alert("추출할 즐겨찾기 데이터가 없습니다.");
        return;
    }

    const blob = new Blob(
        [JSON.stringify(data, null, 2)],
        { type: "application/json;charset=utf-8;" }
    );

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");

    a.href = url;
    a.download = type === 'ARTICLE'
        ? "favorite_articles.json"
        : "favorite_publications.json";

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
// ===============================
// 사이드바 토글
// ===============================
const sidebarToggle = document.getElementById('sidebarToggle');
const container = document.querySelector('.container');

sidebarToggle.addEventListener('click', () => {
// 모바일
if (window.innerWidth <= 768) {
    container.classList.toggle('sidebar-open');
} 
// 데스크톱
else {
    container.classList.toggle('sidebar-collapsed');
}
});
document.getElementById('deleteCodesBtn').addEventListener('click', async function () {

if (!token) {
    alert("토큰이 입력되지 않았습니다.");
    return;
}

const confirmMsg =
    "⚠️ 경고 ⚠️\n\n" +
    "모든 데이터를 삭제합니다.\n" +
    "이 작업은 되돌릴 수 없습니다.\n\n" +
    "정말 삭제하시겠습니까?";

if (!confirm(confirmMsg)) return;

const API_BASE = `https://api.github.com/repos/${OWNER}/${REPO}/contents/codes`;

try {
    // 1. codes 폴더 파일 목록 조회
    const res = await fetch(API_BASE, {
        headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
        alert("❌ codes 폴더를 불러오지 못했습니다.");
        return;
    }

    const files = await res.json();

    // 2. json / txt 파일만 필터
    const targetFiles = files.filter(file =>
        file.type === "file" &&
        (file.name.endsWith(".json") || file.name.endsWith(".txt"))
    );

    if (targetFiles.length === 0) {
        alert("삭제할 데이터가 없습니다.");
        return;
    }

    // 3. 파일 개별 삭제
    for (const file of targetFiles) {
        const deleteRes = await fetch(file.url, {
            method: "DELETE",
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: `delete ${file.path}`,
                sha: file.sha,
                branch: BRANCH
            })
        });

        if (!deleteRes.ok) {
            const err = await deleteRes.json();
            console.error(`❌ 삭제 실패: ${file.name}`, err.message);
        } else {
            console.log(`🗑 삭제 완료: ${file.name}`);
        }
    }

    alert(`✅ 데이터 초기화 완료\n잠시후 페이지를 새로고침하세요.`);

} catch (error) {
    console.error(error);
    alert("❌ 삭제 중 오류 발생");
}
});