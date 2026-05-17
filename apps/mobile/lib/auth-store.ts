import * as SecureStore from "expo-secure-store";
import { apiRequest, type ApiSession } from "./api";

const SESSION_KEY = "truecare.session.v1";

type TokenPair = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
};

let memorySession: ApiSession | null = null;

async function storageAvailable() {
  try {
    return await SecureStore.isAvailableAsync();
  } catch {
    return false;
  }
}

export async function saveSession(session: ApiSession | null) {
  memorySession = session;
  if (!(await storageAvailable())) {
    return;
  }
  if (!session) {
    await SecureStore.deleteItemAsync(SESSION_KEY);
    return;
  }
  await SecureStore.setItemAsync(SESSION_KEY, JSON.stringify(session));
}

export async function getStoredSession() {
  if (memorySession) {
    return memorySession;
  }
  if (!(await storageAvailable())) {
    return null;
  }
  const encoded = await SecureStore.getItemAsync(SESSION_KEY);
  if (!encoded) {
    return null;
  }
  memorySession = JSON.parse(encoded) as ApiSession;
  return memorySession;
}

function toSession(pair: TokenPair): ApiSession {
  return {
    accessToken: pair.access_token,
    refreshToken: pair.refresh_token,
    expiresAt: Date.now() + pair.expires_in * 1000
  };
}

export async function signup(identifier: string, password: string, displayName?: string, inviteCode?: string) {
  const pair = await apiRequest<TokenPair>("post_v1_auth_signup", {
    body: { identifier, password, display_name: displayName, invite_code: inviteCode || "PILOT-HA01" },
    headers: { "x-device-id": "truecare-mobile-dev-device" }
  });
  const session = toSession(pair);
  await saveSession(session);
  return session;
}

export async function login(identifier: string, password: string) {
  const pair = await apiRequest<TokenPair>("post_v1_auth_login", {
    body: { identifier, password }
  });
  const session = toSession(pair);
  await saveSession(session);
  return session;
}

export async function refreshSession(session: ApiSession) {
  const pair = await apiRequest<TokenPair>("post_v1_auth_refresh", {
    body: { refresh_token: session.refreshToken }
  });
  const next = toSession(pair);
  await saveSession(next);
  return next;
}

export async function logout() {
  const session = await getStoredSession();
  if (session) {
    await apiRequest("post_v1_auth_logout", {
      body: { refresh_token: session.refreshToken }
    }).catch(() => undefined);
  }
  await saveSession(null);
}
