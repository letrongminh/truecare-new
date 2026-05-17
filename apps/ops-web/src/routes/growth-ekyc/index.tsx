import { useQuery } from "@tanstack/react-query";
import { OpsTable, OpsStateSurface, deriveOpsState } from "../../components/OpsStateSurface";
import { apiRequest } from "../../lib/api";
import type { OpsRouteProps } from "../../lib/routes";

type PipelineRow = {
  id: string;
  merchant_name?: string;
  stage?: string;
  ekyc_status?: string;
  payment_status?: string;
};

type GrowthEkycResponse = {
  pipeline?: PipelineRow[];
};

export function GrowthEkycRoute({ token, canUseApi }: OpsRouteProps) {
  const query = useQuery({
    queryKey: ["ops-growth-ekyc", token],
    enabled: canUseApi,
    queryFn: () =>
      apiRequest<GrowthEkycResponse>("get_v1_ops_data_room_by_section", {
        token,
        params: { section: "merchant_pipeline" }
      })
  });
  const pipeline = query.data?.pipeline || [];
  const state = deriveOpsState({
    enabled: canUseApi,
    loading: query.isLoading,
    error: query.error,
    empty: pipeline.length === 0
  });

  return (
    <OpsStateSurface
      testIDPrefix="ops-growth-ekyc"
      title="Growth/eKYC"
      subtitle="Review merchant pipeline stages, bank evidence, and go-live blockers."
      state={state}
      onRetry={() => query.refetch()}
    >
      <OpsTable headers={["Merchant", "Pipeline stage", "eKYC", "Payment recipient"]}>
        {pipeline.map((row) => (
          <tr key={row.id}>
            <td>{row.merchant_name || row.id}</td>
            <td>{row.stage || "pending_review"}</td>
            <td>{row.ekyc_status || "not_submitted"}</td>
            <td>{row.payment_status || "needs_verification"}</td>
          </tr>
        ))}
      </OpsTable>
    </OpsStateSurface>
  );
}
