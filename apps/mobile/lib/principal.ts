import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./api";
import { useStoredSession } from "./session-query";

export type AuthPrincipal = {
  user_id: string;
  tenant_id: string;
  roles: string[];
  locale?: string | null;
  merchant_id?: string | null;
  merchant_status?: string | null;
  merchant_pipeline_status?: string | null;
};

export function usePrincipal() {
  const session = useStoredSession();
  const principal = useQuery({
    queryKey: ["auth", "principal", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<AuthPrincipal>("get_v1_auth_me", { token: session.data?.accessToken })
  });
  return { session, principal, token: session.data?.accessToken || null };
}
