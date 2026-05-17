import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { usePrincipal } from "../../../lib/principal";

type Queue = { queue: Array<{ id: string; status: string; bay_number: number }> };

export default function MerchantQueueScreen() {
  const { principal, token } = usePrincipal();
  const merchantId = principal.data?.merchant_id || null;
  const queue = useQuery({
    queryKey: ["merchant-queue", token, merchantId],
    enabled: !!token && !!merchantId,
    queryFn: () => apiRequest<Queue>("get_v1_merchants_by_id_queue", { token, params: { id: merchantId || "" } })
  });
  const state = !token ? "forbidden" : principal.isLoading ? "loading" : !merchantId ? "empty" : queue.isLoading ? "loading" : queue.isError ? "error" : queue.data?.queue.length === 0 ? "empty" : "ready";
  return (
    <StateScaffold
      testIDPrefix="merchant-queue"
      title="Hang doi"
      subtitle="Bang dieu hanh live cho tung vi tri rua."
      state={state}
      primaryAction="Quet QR"
      onPrimaryAction={() => queue.refetch()}
      onSecondaryAction={() => queue.refetch()}
    >
      <DataRow label="Merchant" value={merchantId || "Chua co merchant"} />
      {(queue.data?.queue || []).map((item) => (
        <DataRow key={item.id} label={`Bay ${item.bay_number}`} value={item.status} />
      ))}
    </StateScaffold>
  );
}
