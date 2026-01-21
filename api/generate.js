export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method Not Allowed' });
    }

    const { items, type } = req.body;
    const apiKey = process.env.GOOGLE_API_KEY;

    if (!apiKey) {
        return res.status(500).json({ error: 'Server Configuration Error: GOOGLE_API_KEY not found' });
    }

    if (!items || !Array.isArray(items) || items.length === 0) {
        return res.status(200).json({ selected: [] });
    }

    try {
        // Construct prompt based on type
        const itemText = items.map((item, index) =>
            `${index}. [${item.site}] ${item.title} (${item.link})`
        ).join('\n');

        let systemInstruction = "";
        let userPrompt = "";

        if (type === 'ARTICLE') {
            systemInstruction = `
당신은 대한민국 국방 및 AI 동향 분석 전문가입니다.
주어진 기사 목록 중에서 '국방 AI', '국방 기술', 'AI 최신 트렌드', '주요 기술 정책'과 관련된 중요 기사를 선정해주세요.
선정 기준:
1. 국방/군사 분야와 직접 관련된 AI/IT 기사 (최우선)
2. AI 기술의 획기적인 발전이나 주요 기업(Google, OpenAI 등)의 핵심 발표
3. 정부(과기정통부 등)의 주요 AI/SW 정책

각 선정된 기사에 대해 다음 카테고리 중 하나를 지정해야 합니다:
- 국방: 국방부, 방사청 등 직접적 국방 관련
- 육군: 육군 관련 특화 내용
- 민간: 일반 기업, 기술 트렌드, 해외 동향
- 기관: 정부 기관, 공공 정책, 연구소
- 기타: 그 외

응답 형식은 반드시 유효한 JSON 배열이어야 합니다. 마크다운이나 코드 블록 없이 순수 JSON만 반환하세요.
형식:
[
  { "index": 0, "category": "국방", "reason": "선정 이유 요약" },
  ...
]
`;
            userPrompt = `다음 기사 목록에서 중요 기사를 선정하고 카테고리를 분류해 주세요:\n\n${itemText}`;
        } else {
            systemInstruction = `
당신은 AI 및 IT 기술 간행물 분석 전문가입니다.
주어진 간행물(보고서) 목록 중에서 국방 및 AI 기술 연구 개발에 도움이 될만한 핵심 간행물을 선정해주세요.
선정 기준:
1. 국방, 안보, 보안 관련 기술 보고서
2. 생성형 AI, LLM, 반도체 등 최신 핵심 기술 동향 보고서
3. 주요 정책 연구 보고서

카테고리는 모두 '간행물'로 통일하거나, 필요시 구분하되 여기서는 '간행물'로 지정하거나 내용을 잘 설명하는 키워드를 써도 되지만, 시스템은 '기타' 또는 '간행물'로 처리할 것입니다. 
하지만 사용자 요청에 따라 카테고리는 '국방', '육군', '민간', '기관', '기타' 중 하나로 매핑해 주세요. 간행물의 성격에 맞춰 분류 바랍니다.

응답 형식은 반드시 유효한 JSON 배열이어야 합니다. 마크다운이나 코드 블록 없이 순수 JSON만 반환하세요.
형식:
[
  { "index": 0, "category": "기관", "reason": "선정 이유 요약" },
  ...
]
`;
            userPrompt = `다음 간행물 목록에서 중요 항목을 선정하고 분류해 주세요:\n\n${itemText}`;
        }

        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${apiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contents: [{
                    role: "user",
                    parts: [{ text: systemInstruction + "\n\n" + userPrompt }]
                }],
                generationConfig: {
                    responseMimeType: "application/json"
                }
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`Gemini API Error: ${errorData.error?.message || response.statusText}`);
        }

        const data = await response.json();
        const generatedText = data.candidates[0].content.parts[0].text;

        let selectedItems;
        try {
            selectedItems = JSON.parse(generatedText);
        } catch (e) {
            console.error("JSON Parse Error:", generatedText);
            // Try to cleanup markdown if present (though system prompt forbids it, purely defensive)
            const cleanText = generatedText.replace(/```json/g, '').replace(/```/g, '').trim();
            selectedItems = JSON.parse(cleanText);
        }

        // Map back to original items including link and title for safety
        const results = selectedItems.map(selection => {
            const originalItem = items[selection.index];
            if (!originalItem) return null;
            return {
                ...originalItem,
                category: selection.category,
                reason: selection.reason
            };
        }).filter(item => item !== null);

        res.status(200).json({ selected: results });

    } catch (error) {
        console.error("API Handler Error:", error);
        res.status(500).json({ error: error.message });
    }
}
