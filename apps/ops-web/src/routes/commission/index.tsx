import { useMutation, useQuery } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type CommissionReceivable = {
  merchant_id: string;
  merchant_name: string;
  total_bookings: number;
  total_revenue: number;
  commission_receivable: number;
  commission_status: string;
};

type CommissionResponse = {
  receivables: CommissionReceivable[];
};

function vnd(value: number) {
  return `${value.toLocaleString("vi-VN")} VND`;
}

export function CommissionRoute({ token, canUseApi }: OpsRouteProps) {
  const query = useQuery({
    queryKey: ["ops-commission", token],
    enabled: canUseApi,
    queryFn: () => apiRequest<CommissionResponse>("get_v1_ops_commission_receivables", { token })
  });
  const exportCsv = useMutation({
    mutationFn: () =>
      apiRequest("post_v1_ops_exports", {
        token,
        body: { section: "commission", format: "csv" }
      })
  });
  const rows = query.data?.receivables || [];
  const total = rows.reduce((sum, row) => sum + row.commission_receivable, 0);
  const state = deriveOpsState({
    enabled: canUseApi,
    loading: query.isLoading,
    error: query.error,
    empty: rows.length === 0
  });

  return (
    <OpsStateSurface
      testIDPrefix="ops-commission"
      title="Commission"
      subtitle="Track receivables, payout status, and CSV export readiness."
      state={state}
      onRetry={() => query.refetch()}
    >
      <div className="metric-strip" data-testid="ops-commission-total">
        Commission receivable {vnd(total)}
      </div>
      <button type="button" data-testid="ops-commission-export" disabled={exportCsv.isPending} onClick={() => exportCsv.mutate()}>
        Export CSV
      </button>
      {exportCsv.isSuccess ? <div className="metric-strip" data-testid="ops-commission-export-status">Export requested</div> : null}
      <OpsTable headers={["Merchant", "Bookings", "Revenue", "Receivable", "Status"]}>
        {rows.map((row) => (
          <tr key={row.merchant_id}>
            <td>{row.merchant_name}</td>
            <td>{row.total_bookings}</td>
            <td>{vnd(row.total_revenue)}</td>
            <td>{vnd(row.commission_receivable)}</td>
            <td>{row.commission_status}</td>
          </tr>
        ))}
      </OpsTable>
    </OpsStateSurface>
  );
}
