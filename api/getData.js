// api/getData.js
export default async function handler(req, res) {
  // 1. Vercel 환경변수에서 키를 가져옵니다. (코드에 직접 안 씀!)
  const apiKey = process.env.Git_TOKEN; 
  
  // 2. 실제 데이터를 요청할 외부 URL (예: OpenWeatherMap, OpenAI 등)
  // 클라이언트에서 보낸 파라미터(예: city)를 받을 수도 있습니다.
  const { city } = req.query; 
  const endpoint = `https://api.example.com/weather?q=${city}&appid=${apiKey}`;

  try {
    // 3. 서버에서 외부 API로 요청
    const response = await fetch(endpoint);
    const data = await response.json();

    // 4. 결과를 내 프론트엔드(index.html)로 돌려줍니다.
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: 'API 요청 실패' });
  }
}