const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
const API_V1 = `${API_BASE}/api/v1`;

export async function listConversations(userId) {
  if (!userId) return { conversations: [] };
  const res = await fetch(`${API_V1}/conversations/user/${encodeURIComponent(userId)}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  // If user has no conversations or backend returns not-found, just show empty list.
  if (res.status === 404) return { conversations: [] };
  if (!res.ok) throw new Error((data && data.detail) || 'Failed to load conversations');

  if (!data || !Array.isArray(data.conversations)) return { conversations: [] };
  return data;
}

export async function createConversation(userId) {
  if (!userId) throw new Error('Missing user_id');
  const res = await fetch(`${API_V1}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to create conversation');
  return data;
}

export async function getConversation(conversationId) {
  if (!conversationId) return null;
  const res = await fetch(`${API_V1}/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });
  if (res.status === 404) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to load conversation');
  return data;
}

export async function deleteConversation(conversationId) {
  if (!conversationId) return;
  const res = await fetch(`${API_V1}/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to delete conversation');
  }
}

export async function sendMessage(conversationId, message) {
  if (!conversationId || !message?.trim()) throw new Error('Missing conversation or message');
  const res = await fetch(`${API_V1}/messages/${encodeURIComponent(conversationId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: message.trim() }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to send message');
  return data;
}

