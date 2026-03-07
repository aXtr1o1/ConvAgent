// All config from env with fallbacks. See .env.example for variable names.

const env = (key, fallback) => {
  const v = process.env[key];
  return v !== undefined && v !== "" ? v : fallback;
};

// Normalize hex color from env (add # if missing)
export const getEnvColor = (key, fallback) => {
  const v = env(key, fallback);
  if (!v) return fallback || "";
  return v.startsWith("#") ? v : `#${v}`;
};

// -----------------------------------------------------------------------------
// API & Endpoints
// -----------------------------------------------------------------------------
export const API_BASE_URL = env("REACT_APP_API_BASE_URL", "https://auto.axtr.in").replace(
  /\/+$/,
  ""
);
export const API_V1_PREFIX = env("REACT_APP_API_V1_PREFIX", "/api/v1").replace(/^\/?/, "/");
export const WS_CHAT_URL =
  env("REACT_APP_WS_CHAT_URL", "").trim() ||
  `${API_BASE_URL.replace(/^https/, "wss").replace(/^http/, "ws")}${API_V1_PREFIX}${env("REACT_APP_ENDPOINT_CHAT_WS", "/chat/ws")}`;

const EP = (key, fallback) => env(key, fallback);
const CONV = EP("REACT_APP_ENDPOINT_CONVERSATIONS", "/conversations");
const CONV_BY_ID = EP("REACT_APP_ENDPOINT_CONVERSATION_BY_ID", "/conversations");
const CONV_USER = EP("REACT_APP_ENDPOINT_CONVERSATIONS_USER", "/conversations/user");
const MSGS = EP("REACT_APP_ENDPOINT_MESSAGES", "/messages");
const CHAT_STREAM = EP("REACT_APP_ENDPOINT_CHAT_STREAM", "/chat/stream");
const HEALTH = EP("REACT_APP_ENDPOINT_HEALTH", "/health");
const SOURCES = EP("REACT_APP_ENDPOINT_SOURCES", "/sources");

export const API_ENDPOINTS = {
  CONVERSATIONS: {
    CREATE: CONV,
    LIST: (userId) => `${CONV_USER}/${userId}`,
    GET: (conversationId) => `${CONV_BY_ID}/${conversationId}`,
    DELETE: (conversationId) => `${CONV_BY_ID}/${conversationId}`,
  },
  MESSAGES: {
    LIST: (conversationId) => `${MSGS}/${conversationId}`,
  },
  CHAT: {
    STREAM: CHAT_STREAM,
    WS: env("REACT_APP_ENDPOINT_CHAT_WS", "/chat/ws"),
  },
  HEALTH,
  SOURCES: {
    GET: SOURCES,
  },
};

// Full base URL for REST (base + prefix)
export const API_FULL_BASE = `${API_BASE_URL}${API_V1_PREFIX}`;

// -----------------------------------------------------------------------------
// Auth & App
// -----------------------------------------------------------------------------
export const DEFAULT_USER_ID = env(
  "REACT_APP_DEFAULT_USER_ID",
  "2a06144d-4675-4c38-b7f8-13c02da91af5"
);

// -----------------------------------------------------------------------------
// Theme
// -----------------------------------------------------------------------------
export const DEFAULT_THEME = env("REACT_APP_DEFAULT_THEME", "dark");

// -----------------------------------------------------------------------------
// Color palette (use getEnvColor for #hex)
// -----------------------------------------------------------------------------
export const COLORS = {
  primary: () => getEnvColor("REACT_APP_COLOR_PRIMARY", "#3B82F6"),
  primaryHover: () => getEnvColor("REACT_APP_COLOR_PRIMARY_HOVER", "#2563EB"),
  primaryActive: () => getEnvColor("REACT_APP_COLOR_PRIMARY_ACTIVE", "#1D4ED8"),
  danger: () => getEnvColor("REACT_APP_COLOR_DANGER", "#ef4444"),
  dangerHover: () => getEnvColor("REACT_APP_COLOR_DANGER_HOVER", "#dc2626"),
  bgDark: () => getEnvColor("REACT_APP_COLOR_BG_DARK", "#0A0A0A"),
  bgDarkElevated: () => getEnvColor("REACT_APP_COLOR_BG_DARK_ELEVATED", "#111111"),
  bgDarkCard: () => getEnvColor("REACT_APP_COLOR_BG_DARK_CARD", "#1a1a1a"),
  bgDarkCardHover: () => getEnvColor("REACT_APP_COLOR_BG_DARK_CARD_HOVER", "#2a2a2a"),
  bgDarkInput: () => getEnvColor("REACT_APP_COLOR_BG_DARK_INPUT", "#111111"),
  borderDark: () => getEnvColor("REACT_APP_COLOR_BORDER_DARK", "#374151"),
  textDark: () => getEnvColor("REACT_APP_COLOR_TEXT_DARK", "#ffffff"),
  textMutedDark: () => getEnvColor("REACT_APP_COLOR_TEXT_MUTED_DARK", "#6b7280"),
  textSecondaryDark: () => getEnvColor("REACT_APP_COLOR_TEXT_SECONDARY_DARK", "#d1d5db"),
  bgLight: () => getEnvColor("REACT_APP_COLOR_BG_LIGHT", "#FAFAFA"),
  bgLightElevated: () => getEnvColor("REACT_APP_COLOR_BG_LIGHT_ELEVATED", "#F5F5F5"),
  bgLightCard: () => getEnvColor("REACT_APP_COLOR_BG_LIGHT_CARD", "#ffffff"),
  textLight: () => getEnvColor("REACT_APP_COLOR_TEXT_LIGHT", "#111827"),
  textMutedLight: () => getEnvColor("REACT_APP_COLOR_TEXT_MUTED_LIGHT", "#9ca3af"),
  textSecondaryLight: () => getEnvColor("REACT_APP_COLOR_TEXT_SECONDARY_LIGHT", "#374151"),
  accentOrange: () => getEnvColor("REACT_APP_COLOR_ACCENT_ORANGE", "#f97316"),
  accentOrangeAlt: () => getEnvColor("REACT_APP_COLOR_ACCENT_ORANGE_ALT", "#ea580c"),
  scrollbar: () => getEnvColor("REACT_APP_COLOR_SCROLLBAR", "#888"),
  scrollbarHover: () => getEnvColor("REACT_APP_COLOR_SCROLLBAR_HOVER", "#555"),
  white: () => getEnvColor("REACT_APP_COLOR_WHITE", "#ffffff"),
  gray100: () => getEnvColor("REACT_APP_COLOR_GRAY_100", "#f3f4f6"),
  gray200: () => getEnvColor("REACT_APP_COLOR_GRAY_200", "#e5e7eb"),
};

// -----------------------------------------------------------------------------
// Message & error constants (unchanged)
// -----------------------------------------------------------------------------
export const MESSAGE_ROLES = {
  USER: "user",
  ASSISTANT: "assistant",
};

export const ERROR_MESSAGES = {
  NETWORK_ERROR: "Network error. Please check your connection.",
  AUTH_ERROR: "Authentication failed. Please sign in again.",
  GENERIC_ERROR: "Something went wrong. Please try again.",
};
