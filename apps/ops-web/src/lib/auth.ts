import { apiRequest } from "./api";

const OPS_TOKEN_KEY = "truecare.ops.accessToken.v1";

export type AuthMeResponse = {
  user_id: string;
  tenant_id: string;
  roles: string[];
  locale?: string | null;
};

export const opsRoles = new Set(["ops", "admin", "finance_ops", "quality_ops"]);

export function readOpsToken() {
  return window.localStorage.getItem(OPS_TOKEN_KEY) || "";
}

export function saveOpsToken(token: string) {
  if (token.trim()) {
    window.localStorage.setItem(OPS_TOKEN_KEY, token.trim());
  } else {
    window.localStorage.removeItem(OPS_TOKEN_KEY);
  }
}

export function hasOpsRole(principal?: AuthMeResponse) {
  return Boolean(principal?.roles.some((role) => opsRoles.has(role)));
}

export function getCurrentPrincipal(token: string) {
  return apiRequest<AuthMeResponse>("get_v1_auth_me", { token });
}
