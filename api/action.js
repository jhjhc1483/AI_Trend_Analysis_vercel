// api/action.js
export default async function handler(req, res) {
  const { workflowId } = req.body;
  const { GIT_TOKEN, GIT_OWNER, GIT_REPO, GIT_BRANCH } = process.env;

  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');

  const url = `https://api.github.com/repos/${GIT_OWNER}/${GIT_REPO}/actions/workflows/${workflowId}/dispatches`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${GIT_TOKEN}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ ref: GIT_BRANCH }),
    });

    if (response.status === 204) {
      res.status(200).json({ message: 'Success' });
    } else {
      const errorData = await response.json();
      res.status(response.status).json(errorData);
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}