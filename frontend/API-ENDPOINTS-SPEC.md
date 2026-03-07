# API Endpoints Specification — Backend Requirements for Frontend

This document describes the **API endpoints the backend must implement** so the Digirett frontend can connect and work seamlessly. All paths are relative to the API base (e.g. `https://your-backend.com/api/v1`).

---

## Base URL & Prefix

- **REST base:** `{REACT_APP_API_BASE_URL}{REACT_APP_API_V1_PREFIX}` → e.g. `https://auto.axtr.in/api/v1`
- **Content-Type:** `application/json` for request/response bodies
- **Optional:** `Authorization: Bearer <token>` when auth is enabled

---

## 1. Conversations

### 1.1 Create conversation

**Purpose:** Start a new chat. Frontend calls this when the user clicks “New chat” or sends the first message in a new thread.

| Item | Value |
|------|--------|
| **Method** | `POST` |
| **Path** | `/conversations` |
| **Env path var** | `REACT_APP_ENDPOINT_CONVERSATIONS` |

**Request body:**

```json
{
  "user_id": "uuid-string",
  "title": "Optional title"
}
```

- `user_id` (required): string (UUID). From `REACT_APP_DEFAULT_USER_ID` or auth.
- `title` (optional): string. If omitted, frontend uses “New Conversation”.

**Response (success):** `201` or `200` with body that includes at least:

- `conversation_id` or `id` (string, UUID) — **required** so the frontend can open the new thread and send messages to it.

**Example:**

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "New Conversation",
  "created_at": "2025-03-06T12:00:00Z"
}
```

---

### 1.2 List conversations by user

**Purpose:** Load the sidebar list of conversations (latest first). Frontend sorts by `updated_at` descending.

| Item | Value |
|------|--------|
| **Method** | `GET` |
| **Path** | `/conversations/user/{user_id}` |
| **Env path var** | `REACT_APP_ENDPOINT_CONVERSATIONS_USER` |

**Path parameter:**

- `user_id`: string (UUID).

**Response (success):** `200` with either:

- A **JSON array** of conversation objects, or  
- An object with a **`conversations`** array: `{ "conversations": [ ... ] }`

**Each conversation object must include:**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `conversation_id` or `id` | string (UUID) | Yes | Used as unique key and for GET/DELETE. |
| `title` | string | No | Shown in sidebar; fallback in UI: “New Conversation”. |
| `updated_at` | string (ISO 8601) | Yes | Used to sort “latest first”. |

**Example:**

```json
[
  {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Contract review",
    "updated_at": "2025-03-06T14:30:00Z",
    "created_at": "2025-03-06T12:00:00Z"
  }
]
```

---

### 1.3 Get conversation by ID (with messages)

**Purpose:** Load a single conversation and its messages when the user selects a thread. Frontend uses this to render the chat history.

| Item | Value |
|------|--------|
| **Method** | `GET` |
| **Path** | `/conversations/{conversation_id}` |
| **Env path var** | `REACT_APP_ENDPOINT_CONVERSATION_BY_ID` |

**Path parameter:**

- `conversation_id`: string (UUID).

**Response (success):** `200`. Frontend accepts any of these shapes:

- **A.** Array of messages only: `[ { message_id, role, content, ... }, ... ]`  
- **B.** Object with messages: `{ "messages": [ ... ] }`  
- **C.** Object with nested conversation: `{ "conversation": { "messages": [ ... ] } }`

**Each message object must include:**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `message_id` or `id` | string | Yes | Unique per message. |
| `role` | string | Yes | `"user"` or `"assistant"`. |
| `content` | string | Yes | Displayed as message body; can be `""`. |
| `created_at` | string (ISO 8601) | No | Shown as timestamp. |
| `sources` | array | No | List of source objects for citations (see Sources section). |

**Example (shape B):**

```json
{
  "conversation": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Contract review"
  },
  "messages": [
    {
      "message_id": "msg-1",
      "role": "user",
      "content": "Summarize this contract.",
      "created_at": "2025-03-06T12:00:00Z",
      "sources": []
    },
    {
      "message_id": "msg-2",
      "role": "assistant",
      "content": "The contract covers...",
      "created_at": "2025-03-06T12:00:05Z",
      "sources": [
        { "url": "https://example.com/doc", "title": "Sample Document" }
      ]
    }
  ]
}
```

**Error:** `404` if conversation not found. Frontend will still handle `500` on delete; for GET, a clear 404 is preferred.

---

### 1.4 Delete conversation

**Purpose:** Remove a conversation from the list when the user deletes it in the UI.

| Item | Value |
|------|--------|
| **Method** | `DELETE` |
| **Path** | `/conversations/{conversation_id}` |
| **Env path var** | `REACT_APP_ENDPOINT_CONVERSATION_BY_ID` |

**Path parameter:**

- `conversation_id`: string (UUID).

**Response (success):** `200` or `204` with optional body. Frontend treats `404` and `500` as “removed” (no hard error to user).

**Error:** `404` if not found; optional body with `detail` or `message` for debugging.

---

## 2. Chat (WebSocket)

**Purpose:** Real-time streaming chat. Frontend sends one message and expects a stream of tokens plus a final “complete” event with metadata and sources.

| Item | Value |
|------|--------|
| **Protocol** | WebSocket |
| **URL** | Full URL from `REACT_APP_WS_CHAT_URL`, or `{wss_base}/api/v1/chat/ws` (path from `REACT_APP_ENDPOINT_CHAT_WS`) |
| **Env** | `REACT_APP_WS_CHAT_URL` or `REACT_APP_ENDPOINT_CHAT_WS` |

### 2.1 Client → Server (single message)

**Sent once after connection open.** JSON object:

```json
{
  "query": "User message text",
  "user_id": "uuid-string",
  "top_k": 3,
  "temperature": 0.7,
  "conversation_id": "uuid-string or null"
}
```

- `query` (required): string, the user’s message.
- `user_id` (required): string (UUID).
- `conversation_id` (optional): string (UUID) if continuing a thread; omit or `null` for new conversation.
- `top_k`, `temperature`: optional; frontend sends `3` and `0.7` by default.

### 2.2 Server → Client (streaming events)

Each WebSocket message is a **JSON object** with a **`type`** field. Frontend handles:

| `type` | When to send | Frontend behavior |
|--------|----------------|--------------------|
| `sources` | Optional; e.g. before or with tokens | `event.data` = array of source objects. Stored and attached to the assistant message on `complete`. |
| `token` | For each streamed chunk of the reply | `event.data` = string (chunk). Appended and shown in real time. |
| `complete` | When the full reply is done | Frontend closes the socket and finalizes the message. Uses `event.metadata` for IDs and full text. |
| `error` | On failure | `event.message` = string. Frontend calls error handler and closes. |

**Event shapes:**

- **sources**
  ```json
  { "type": "sources", "data": [ { "url": "...", "title": "..." }, ... ] }
  ```
- **token**
  ```json
  { "type": "token", "data": " chunk of text " }
  ```
- **complete**
  ```json
  {
    "type": "complete",
    "metadata": {
      "conversation_id": "uuid",
      "message_id": "string",
      "full_answer": "entire assistant message text"
    }
  }
  ```
  - `conversation_id`: required if this was a new conversation (so frontend can switch to it).
  - `message_id`: optional; used for loading sources later.
  - `full_answer`: optional; if present, frontend uses it instead of concatenated tokens.
- **error**
  ```json
  { "type": "error", "message": "Human-readable error" }
  ```

**Source object (in `sources` or in message payload):**

- `url` (string): link to citation.
- `title` (string, optional): display label; frontend falls back to `url`.

---

## 3. Messages (REST)

**Purpose:** Optional way to load messages for a conversation (e.g. pagination or sync). Frontend currently loads messages via **GET conversation by ID** (1.3). This endpoint is reserved for future use (e.g. “load more” or dedicated messages API).

| Item | Value |
|------|--------|
| **Method** | `GET` |
| **Path** | `/messages/{conversation_id}` |
| **Env path var** | `REACT_APP_ENDPOINT_MESSAGES` |

**Path parameter:**

- `conversation_id`: string (UUID).

**Response (success):** `200` with an array of message objects (same shape as in section 1.3).

---

## 4. Sources

**Purpose:** Fetch source citations for a given message (e.g. when the frontend loads a conversation and messages don’t already include `sources`, or for “refresh sources”).

| Item | Value |
|------|--------|
| **Method** | `GET` |
| **Path** | `/sources` |
| **Env path var** | `REACT_APP_ENDPOINT_SOURCES` |
| **Query** | `message_id` (required): string. |

**Example:** `GET /sources?message_id=msg-123`

**Response (success):** `200` with a JSON array of source objects:

```json
[
  { "url": "https://example.com/doc.pdf", "title": "Document Title" }
]
```

- `url`: string (required).
- `title`: string (optional). Frontend uses `title` or `url` for display.

---

## 5. Health

**Purpose:** Backend liveness/readiness check (e.g. for load balancers or status pages).

| Item | Value |
|------|--------|
| **Method** | `GET` |
| **Path** | `/health` |
| **Env path var** | `REACT_APP_ENDPOINT_HEALTH` |

**Response (success):** `200` with any JSON body (e.g. `{ "status": "ok" }`).

---

## 6. Error handling (frontend expectations)

Frontend handles these HTTP statuses consistently:

| Status | Frontend behavior |
|--------|--------------------|
| `401` | Logs “Unauthorized”; can trigger re-login when auth is enabled. |
| `403` | Logs “Access forbidden”. |
| `404` | Used for “not found” (e.g. conversation). For DELETE, frontend treats as success. |
| `500` | Shows “Server error. Please try again.” For DELETE conversation, frontend may treat as success. |
| Network / no response | “Server not reachable” or “Network error”. |

Error response body can include a `detail` or `message` field; frontend may show it to the user when available.

---

## 7. Checklist for backend implementation

Use this to ensure the frontend works seamlessly:

- [ ] **POST** `/conversations` — body: `user_id`, optional `title`; response includes `conversation_id` (or `id`).
- [ ] **GET** `/conversations/user/{user_id}` — returns array (or `{ conversations: [] }`) with `conversation_id`, `title`, `updated_at`.
- [ ] **GET** `/conversations/{conversation_id}` — returns conversation + messages (array or `messages` or `conversation.messages`); each message has `message_id`, `role`, `content`, optional `created_at`, `sources`.
- [ ] **DELETE** `/conversations/{conversation_id}` — returns 200/204 (404/500 tolerated).
- [ ] **WebSocket** `/chat/ws` (or path from env) — accepts JSON with `query`, `user_id`, optional `conversation_id`; sends `token`, optional `sources`, `complete` (with `metadata.conversation_id`, `message_id`, `full_answer`), and `error` on failure.
- [ ] **GET** `/sources?message_id=...` — returns array of `{ url, title? }`.
- [ ] **GET** `/health` — returns 200.
- [ ] **CORS** allows the frontend origin.
- [ ] **Optional:** `Authorization: Bearer <token>` for authenticated requests when enabled.

Once these are implemented and the frontend env points to your base URL and paths, the app should connect and work seamlessly.
