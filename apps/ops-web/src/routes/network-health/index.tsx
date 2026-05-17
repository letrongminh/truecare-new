import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type NetworkHealthResponse = {
  stale_merchants?: Array<{ id: string; name?: string; stale_since?: string; reason?: string }>;
  fallback_actions?: Array<{ id: string; label: string; status: string }>;
};

export function NetworkHealthRoute({ token, canUseApi }: OpsRouteProps) {
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState("");
  const [merchantId, setMerchantId] = useState("");
  const [serviceId, setServiceId] = useState("");
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
  const fallbackBooking = useMutation({
    mutationFn: () =>
      apiRequest("post_v1_ops_bookings", {
        token,
        body: {
          user_id: userId,
          merchant_id: merchantId,
          merchant_service_id: serviceId,
          bay_number: 1,
          reason: "ops_web_network_fallback"
        }
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ops-network-health", token] })
  });
  const state = deriveOpsState({
    enabled: canUseApi,
    loading: query.isLoading || fallbackBooking.isPending,
    error: query.error || fallbackBooking.error,
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
      <div className="fallback-panel" data-testid="ops-network-health-fallback-panel">
        <input data-testid="ops-network-health-user-id" placeholder="User ID" value={userId} onChange={(event) => setUserId(event.target.value)} />
        <input data-testid="ops-network-health-merchant-id" placeholder="Merchant ID" value={merchantId} onChange={(event) => setMerchantId(event.target.value)} />
        <input data-testid="ops-network-health-service-id" placeholder="Service ID" value={serviceId} onChange={(event) => setServiceId(event.target.value)} />
        <button type="button" data-testid="ops-network-health-create-booking" onClick={() => fallbackBooking.mutate()}>
          Create fallback booking
        </button>
      </div>
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
