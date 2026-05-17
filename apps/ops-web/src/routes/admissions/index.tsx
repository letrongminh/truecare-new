import { useQuery } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type PendingMerchant = {
  id: string;
  name?: string;
  address?: string;
  status?: string;
  payment_recipient_status?: string;
};

type PendingMerchantsResponse = {
  merchants: PendingMerchant[];
};

export function AdmissionsRoute({ token, canUseApi }: OpsRouteProps) {
  const query = useQuery({
    queryKey: ["ops-admissions", token],
    enabled: canUseApi,
    queryFn: () => apiRequest<PendingMerchantsResponse>("get_v1_ops_merchants_pending", { token })
  });
  const merchants = query.data?.merchants || [];
  const state = deriveOpsState({
    enabled: canUseApi,
    loading: query.isLoading,
    error: query.error,
    empty: merchants.length === 0
  });

  return (
    <OpsStateSurface
      testIDPrefix="ops-admissions"
      title="Admissions"
      subtitle="Review merchant applications, payment recipient ownership, and go-live decisions."
      state={state}
      onRetry={() => query.refetch()}
    >
      <OpsTable headers={["Merchant", "Address", "Status", "Payment recipient", "Actions"]}>
        {merchants.map((merchant) => (
          <tr key={merchant.id}>
            <td>{merchant.name || merchant.id}</td>
            <td>{merchant.address || "Missing address"}</td>
            <td>{merchant.status || "pending_review"}</td>
            <td>{merchant.payment_recipient_status || "needs_verification"}</td>
            <td>
              <div className="button-row">
                <button type="button" data-testid="ops-admissions-approve">
                  Approve
                </button>
                <button type="button" data-testid="ops-admissions-verify-payment">
                  Verify payment
                </button>
                <button type="button" data-testid="ops-admissions-suspend">
                  Suspend
                </button>
              </div>
            </td>
          </tr>
        ))}
      </OpsTable>
    </OpsStateSurface>
  );
}
