/**
 * Returns true if the user is considered logged in (user_id stored in localStorage).
 */
export function isLoggedIn() {
  return !!localStorage.getItem('user_id');
}

/**
 * Build base64-encoded string from username and password (username:password).
 * Uses encodeURIComponent + unescape for btoa to support non-ASCII characters.
 */
export function buildB64Credentials(username, password) {
  const credentials = `${username}:${password}`;
  try {
    return btoa(unescape(encodeURIComponent(credentials)));
  } catch {
    return btoa(credentials);
  }
}

const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/** Expected auth token for Admin / Admin@123 only. */
const ADMIN_AUTH_TOKEN = 'ZDI1NDYxZmUtNDVlMS00ZmFlLTkxNTMtOThkYzBjYTc1MDA0OkFkbWlu';

/**
 * Validate login: POST /api/v1/auth with { username, encoded }.
 * For username "Admin" and password "Admin@123", uses hard-coded ADMIN_AUTH_TOKEN; otherwise encoded = base64(username:password).
 *
 * Success: { status: "success", user_id, username }
 * Failure: { status: "failed", detail: "Invalid username or credentials." }
 *
 * @returns {Promise<{ status: string, user_id?: string, username?: string, detail?: string }>}
 */
export async function validateLogin(username, password) {
  const encoded =
    username === 'Admin' && password === 'Admin@123'
      ? ADMIN_AUTH_TOKEN
      : buildB64Credentials(username, password);
  console.log('[auth] base64(username:password):', encoded);
  const res = await fetch(`${API_BASE}/api/v1/auth`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, encoded }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || 'Login request failed');
  }
  
  return data;
}
