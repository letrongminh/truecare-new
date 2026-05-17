import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type PendingMerchant = {
  id: string;
  name?: string;
  address?: string;
  status?: string;
  payment_recipient_status?: string;
  photo_status?: string;
  ekyc_status?: string;
  go_live_blockers?: string[];
};

type PendingMerchantsResponse = {
  merchants: PendingMerchant[];
};

export function AdmissionsRoute({ token, canUseApi }: OpsRouteProps) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["ops-admissions", token],
    enabled: canUseApi,
    queryFn: () => apiRequest<PendingMerchantsResponse>("get_v1_ops_merchants_pending", { token })
  });
  const decision = useMutation({
    mutationFn: (input: { operationId: string; merchantId: string; body?: unknown }) =>
      apiRequest<PendingMerchant>(input.operationId, {
        token,
        params: { id: input.merchantId },
        body: input.body
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ops-admissions", token] })
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
      <OpsTable headers={["Merchant", "Address", "Status", "Checklist", "Actions"]}>
        {merchants.map((merchant) => (
          <tr key={merchant.id}>
            <td>{merchant.name || merchant.id}</td>
            <td>{merchant.address || "Missing address"}</td>
            <td>{merchant.status || "pending_review"}</td>
            <td>
              photo {merchant.photo_status || "missing"} / payment {merchant.payment_recipient_status || "missing"} / eKYC {merchant.ekyc_status || "not_submitted"}
            </td>
            <td>
              <div className="button-row">
                <button
                  type="button"
                  data-testid="ops-admissions-approve"
                  disabled={decision.isPending}
                  onClick={() => decision.mutate({ operationId: "post_v1_ops_merchants_by_id_approve", merchantId: merchant.id })}
                >
                  Approve
                </button>
                <button
                  type="button"
                  data-testid="ops-admissions-verify-payment"
                  disabled={decision.isPending}
                  onClick={() => decision.mutate({ operationId: "post_v1_ops_merchants_by_id_verify_payment_recipient", merchantId: merchant.id })}
                >
                  Verify payment
                </button>
                <button
                  type="button"
                  data-testid="ops-admissions-reject"
                  disabled={decision.isPending}
                  onClick={() => decision.mutate({ operationId: "post_v1_ops_merchants_by_id_reject", merchantId: merchant.id, body: { reason: "ops_review_rejected" } })}
                >
                  Reject
                </button>
                <button
                  type="button"
                  data-testid="ops-admissions-suspend"
                  disabled={decision.isPending}
                  onClick={() => decision.mutate({ operationId: "post_v1_ops_merchants_by_id_suspend", merchantId: merchant.id, body: { reason: "ops_suspended" } })}
                >
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
