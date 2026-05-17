import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type Complaint = {
  id: string;
  booking_id: string;
  category: string;
  description: string;
  status: string;
  resolution?: string | null;
  refund_approved: boolean;
  voucher_action?: string | null;
  created_at: string;
};

type ComplaintResponse = {
  complaints: Complaint[];
};

export function ComplaintsRoute({ token, canUseApi }: OpsRouteProps) {
  const queryClient = useQueryClient();
  const [voucherUserId, setVoucherUserId] = useState("");
  const query = useQuery({
    queryKey: ["ops-complaints", token],
    enabled: canUseApi,
    queryFn: () => apiRequest<ComplaintResponse>("get_v1_ops_complaints", { token })
  });
  const resolve = useMutation({
    mutationFn: (complaintId: string) =>
      apiRequest<Complaint>("patch_v1_ops_complaints_by_id", {
        token,
        params: { id: complaintId },
        body: {
          status: "resolved",
          resolution: "ops_resolved_from_web",
          refund_approved: false,
          voucher_action: "manual_review"
        }
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ops-complaints", token] })
  });
  const mintVoucher = useMutation({
    mutationFn: () =>
      apiRequest("post_v1_ops_reward_voucher", {
        token,
        body: { user_id: voucherUserId, reason: "ops_web_complaint_recovery" }
      })
  });
  const complaints = query.data?.complaints || [];
  const state = deriveOpsState({
    enabled: canUseApi,
    loading: query.isLoading,
    error: query.error,
    empty: complaints.length === 0
  });

  return (
    <OpsStateSurface
      testIDPrefix="ops-complaints"
      title="Complaints"
      subtitle="Triage category, refund, voucher, and SLA resolution decisions."
      state={state}
      onRetry={() => query.refetch()}
    >
      <div className="fallback-panel" data-testid="ops-complaints-voucher-panel">
        <input data-testid="ops-complaints-voucher-user-id" placeholder="User ID for recovery voucher" value={voucherUserId} onChange={(event) => setVoucherUserId(event.target.value)} />
        <button type="button" data-testid="ops-complaints-mint-voucher" disabled={mintVoucher.isPending} onClick={() => mintVoucher.mutate()}>
          Mint voucher
        </button>
      </div>
      <OpsTable headers={["Created", "Booking", "Category", "Status", "Decision", "Actions"]}>
        {complaints.map((complaint) => (
          <tr key={complaint.id}>
            <td>{new Date(complaint.created_at).toLocaleString("vi-VN")}</td>
            <td>{complaint.booking_id}</td>
            <td>{complaint.category}</td>
            <td>{complaint.status}</td>
            <td>
              {complaint.refund_approved ? "Refund" : complaint.voucher_action || complaint.resolution || "Pending"}
            </td>
            <td>
              <button type="button" data-testid="ops-complaints-resolve" disabled={resolve.isPending} onClick={() => resolve.mutate(complaint.id)}>
                Resolve
              </button>
            </td>
          </tr>
        ))}
      </OpsTable>
    </OpsStateSurface>
  );
}
