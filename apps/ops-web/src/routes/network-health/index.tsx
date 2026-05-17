import { useQuery } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type NetworkHealthResponse = {
  stale_merchants?: Array<{ id: string; name?: string; stale_since?: string; reason?: string }>;
  fallback_actions?: Array<{ id: string; label: string; status: string }>;
};

export function NetworkHealthRoute({ token, canUseApi }: OpsRouteProps) {
  const query = useQuery({
    queryKey: ["ops-network-health", token],
    enabled: canUseApi,
    queryFn: () =>
      apiRequest<NetworkHealthResponse>("get_v1_ops_data_room_by_section", {
        token,
        params: { section: "network-health" }
      })
  });
  const staleMerchants = query.data?.stale_merchants || [];
  const fallbackActions = query.data?.fallback_actions || [];
  const state = deriveOpsState({
    enabled: canUseApi,
    loading: query.isLoading,
    error: query.error,
    empty: staleMerchants.length === 0 && fallbackActions.length === 0
  });

  return (
    <OpsStateSurface
      testIDPrefix="ops-network-health"
      title="Network health"
      subtitle="Monitor stale merchants, live queue gaps, and manual fallback actions."
      state={state}
      onRetry={() => query.refetch()}
    >
      <OpsTable headers={["Merchant", "Stale since", "Reason", "Fallback"]}>
        {staleMerchants.map((merchant) => (
          <tr key={merchant.id}>
            <td>{merchant.name || merchant.id}</td>
            <td>{merchant.stale_since || "Unknown"}</td>
            <td>{merchant.reason || "No heartbeat"}</td>
            <td>Open fallback action</td>
          </tr>
        ))}
        {fallbackActions.map((action) => (
          <tr key={action.id}>
            <td>{action.label}</td>
            <td>Manual</td>
            <td>{action.status}</td>
            <td>Queued</td>
          </tr>
        ))}
      </OpsTable>
    </OpsStateSurface>
  );
}
