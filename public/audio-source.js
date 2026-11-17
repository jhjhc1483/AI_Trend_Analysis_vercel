// 오늘 브리핑 오디오(mp3) 주소를 정해 <audio>에 연결합니다. (index, visualizer, visualizer_brief, public/bf.html 공용)
//
// gen_audio.py 가 만드는 public/audio.json 에 Vercel Blob 주소가 있으면 그 주소를 쓰고
// (mp3를 매일 git에 커밋하지 않아 저장소 용량이 늘지 않음),
// 없거나 읽지 못하면 기존처럼 public/audio.mp3 를 씁니다.
// 주소 뒤에 갱신 시각을 붙여 브라우저가 어제 파일을 재생하지 않게 합니다.
window.loadBriefingAudio = async function (player, publicDir) {
    if (!player) return;
    const base = publicDir || '';
    try {
        const res = await fetch(`${base}audio.json?t=${Date.now()}`);
        if (res.ok) {
            const info = await res.json();
            if (info && info.url) {
                player.src = `${info.url}?v=${encodeURIComponent(info.updated_at || Date.now())}`;
                return;
            }
        }
    } catch (e) {
        console.warn('audio.json을 읽지 못해 기본 오디오 파일을 사용합니다:', e);
    }
    player.src = `${base}audio.mp3?t=${Date.now()}`;
};
