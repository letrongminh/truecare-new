import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Me = { user_id: string; tenant_id: string; roles: string[]; locale?: string };

export default function ProfileScreen() {
  const session = useStoredSession();
  const me = useQuery({
    queryKey: ["profile", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Me>("get_v1_auth_me", { token: session.data?.accessToken })
  });
  return (
    <StateScaffold testIDPrefix="profile" title="Ho so" subtitle="Thong tin tai khoan, quyen rieng tu va phien dang nhap." state={me.isLoading ? "loading" : me.isError ? "error" : "ready"} primaryAction="Cap nhat">
      <DataRow label="User" value={me.data?.user_id || "-"} />
      <DataRow label="Tenant" value={me.data?.tenant_id || "-"} />
      <DataRow label="Vai tro" value={(me.data?.roles || []).join(", ") || "-"} />
      <DataRow label="Locale" value={me.data?.locale || "vi"} />
    </StateScaffold>
  );
}
