import { useQuery } from "@tanstack/react-query";
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
  const query = useQuery({
    queryKey: ["ops-complaints", token],
    enabled: canUseApi,
    queryFn: () => apiRequest<ComplaintResponse>("get_v1_ops_complaints", { token })
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
      <OpsTable headers={["Created", "Booking", "Category", "Status", "Decision"]}>
        {complaints.map((complaint) => (
          <tr key={complaint.id}>
            <td>{new Date(complaint.created_at).toLocaleString("vi-VN")}</td>
            <td>{complaint.booking_id}</td>
            <td>{complaint.category}</td>
            <td>{complaint.status}</td>
            <td>
              {complaint.refund_approved ? "Refund" : complaint.voucher_action || complaint.resolution || "Pending"}
            </td>
          </tr>
        ))}
      </OpsTable>
    </OpsStateSurface>
  );
}
