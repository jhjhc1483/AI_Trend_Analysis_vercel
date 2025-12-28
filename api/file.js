// api/file.js
export default async function handler(req, res) {
  const { path, sha, content, message } = req.body || req.query; // GET은 query, 나머지는 body
  const method = req.method;
  const { GIT_TOKEN, GIT_OWNER, GIT_REPO, GIT_BRANCH } = process.env;

  // path가 없으면 에러 (단, 폴더 조회가 아닐 경우)
  const targetPath = req.query.path || req.body.path || ''; 
  const url = `https://api.github.com/repos/${GIT_OWNER}/${GIT_REPO}/contents/${targetPath}?ref=${GIT_BRANCH}`;

  const headers = {
    'Authorization': `Bearer ${GIT_TOKEN}`,
    'Accept': 'application/vnd.github.v3+json',
    'Content-Type': 'application/json',
  };

  try {
    let response;
    
    if (method === 'GET') {
      // 파일 읽기 또는 폴더 목록 조회
      response = await fetch(url, { headers });
    } else if (method === 'PUT') {
      // 파일 생성/수정
      response = await fetch(url, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          message: message || `update ${targetPath}`,
          content: content, // Base64 content
          branch: GIT_BRANCH,
          ...(sha && { sha }) // sha가 있으면(수정 시) 포함
        })
      });
    } else if (method === 'DELETE') {
      // 파일 삭제
      response = await fetch(url, {
        method: 'DELETE',
        headers,
        body: JSON.stringify({
          message: message || `delete ${targetPath}`,
          sha: sha,
          branch: GIT_BRANCH
        })
      });
    }

    if (!response.ok) {
       // 에러 처리
       const errData = await response.json().catch(() => ({})); 
       return res.status(response.status).json(errData);
    }

    const data = await response.json();
    res.status(200).json(data);

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}