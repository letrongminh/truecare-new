import { useQuery } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type AuditRow = {
  id: string;
  actor_user_id?: string;
  action?: string;
  target_kind?: string;
  target_id?: string;
  recorded_at?: string;
};

type AuditLogResponse = {
  audit_log?: AuditRow[];
  items?: AuditRow[];
};

export function AuditLogRoute({ token, canUseApi }: OpsRouteProps) {
  const query = useQuery({
    queryKey: ["ops-audit-log", token],
    enabled: canUseApi,
    queryFn: () => apiRequest<AuditLogResponse>("get_v1_ops_audit_log", { token })
  });
  const rows = query.data?.audit_log || query.data?.items || [];
  const state = deriveOpsState({
    enabled: canUseApi,
    loading: query.isLoading,
    error: query.error,
    empty: rows.length === 0
  });

  return (
    <OpsStateSurface
      testIDPrefix="ops-audit-log"
      title="Audit log"
      subtitle="Trace ops decisions, fallback actions, and support-sensitive mutations."
      state={state}
      onRetry={() => query.refetch()}
    >
      <OpsTable headers={["Recorded", "Actor", "Action", "Target"]}>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>{row.recorded_at ? new Date(row.recorded_at).toLocaleString("vi-VN") : "Unknown"}</td>
            <td>{row.actor_user_id || "system"}</td>
            <td>{row.action || "recorded"}</td>
            <td>{[row.target_kind, row.target_id].filter(Boolean).join(":") || "n/a"}</td>
          </tr>
        ))}
      </OpsTable>
    </OpsStateSurface>
  );
}
