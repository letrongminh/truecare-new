import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

const merchantId = "00000000-0000-0000-0000-000000000000";
type Summary = { services_completed: number; total_revenue: number; qr_revenue: number; cash_revenue: number; complaint_count: number };

export default function MerchantSummaryScreen() {
  const session = useStoredSession();
  const summary = useQuery({
    queryKey: ["merchant-summary", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Summary>("get_v1_merchants_by_id_daily_summary", { token: session.data?.accessToken, params: { id: merchantId } })
  });
  return (
    <StateScaffold testIDPrefix="merchant-summary" title="Tong ket ngay" subtitle="Doanh thu QR/tien mat, khieu nai va CSV." state={summary.isLoading ? "loading" : summary.isError ? "error" : "ready"} primaryAction="Xuat CSV">
      <DataRow label="Hoan tat" value={String(summary.data?.services_completed ?? 0)} />
      <DataRow label="Doanh thu" value={`${(summary.data?.total_revenue || 0).toLocaleString("vi-VN")} VND`} />
      <DataRow label="Khieu nai" value={String(summary.data?.complaint_count ?? 0)} />
    </StateScaffold>
  );
}
