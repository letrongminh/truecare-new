import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { usePrincipal } from "../../../lib/principal";

type Summary = { services_completed: number; total_revenue: number; qr_revenue: number; cash_revenue: number; complaint_count: number };

export default function MerchantSummaryScreen() {
  const { principal, token } = usePrincipal();
  const merchantId = principal.data?.merchant_id || null;
  const summary = useQuery({
    queryKey: ["merchant-summary", token, merchantId],
    enabled: !!token && !!merchantId,
    queryFn: () => apiRequest<Summary>("get_v1_merchants_by_id_daily_summary", { token, params: { id: merchantId || "" } })
  });
  const state = !token ? "forbidden" : principal.isLoading ? "loading" : !merchantId ? "empty" : summary.isLoading ? "loading" : summary.isError ? "error" : "ready";
  return (
    <StateScaffold
      testIDPrefix="merchant-summary"
      title="Tong ket ngay"
      subtitle="Doanh thu QR/tien mat, khieu nai va CSV."
      state={state}
      primaryAction="Xuat CSV"
      onPrimaryAction={() => summary.refetch()}
      onSecondaryAction={() => summary.refetch()}
    >
      <DataRow label="Merchant" value={merchantId || "Chua co merchant"} />
      <DataRow label="Hoan tat" value={String(summary.data?.services_completed ?? 0)} />
      <DataRow label="Doanh thu" value={`${(summary.data?.total_revenue || 0).toLocaleString("vi-VN")} VND`} />
      <DataRow label="QR/Tien mat" value={`${(summary.data?.qr_revenue || 0).toLocaleString("vi-VN")} / ${(summary.data?.cash_revenue || 0).toLocaleString("vi-VN")}`} />
      <DataRow label="Khieu nai" value={String(summary.data?.complaint_count ?? 0)} />
    </StateScaffold>
  );
}
