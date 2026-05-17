import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

const merchantId = "00000000-0000-0000-0000-000000000000";
type Queue = { queue: Array<{ id: string; status: string; bay_number: number }> };

export default function MerchantQueueScreen() {
  const session = useStoredSession();
  const queue = useQuery({
    queryKey: ["merchant-queue", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Queue>("get_v1_merchants_by_id_queue", { token: session.data?.accessToken, params: { id: merchantId } })
  });
  return (
    <StateScaffold testIDPrefix="merchant-queue" title="Hang doi" subtitle="Bang dieu hanh live cho tung vi tri rua." state={queue.isLoading ? "loading" : queue.isError ? "error" : queue.data?.queue.length === 0 ? "empty" : "ready"} primaryAction="Quet QR">
      {(queue.data?.queue || []).map((item) => (
        <DataRow key={item.id} label={`Bay ${item.bay_number}`} value={item.status} />
      ))}
    </StateScaffold>
  );
}
