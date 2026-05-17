import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../components/StateScaffold";
import { apiRequest } from "../../lib/api";
import { useStoredSession } from "../../lib/session-query";

type NearbyResponse = { merchants: Array<{ id: string; name: string; available_bays: number }>; gps_fallback: boolean };

export default function ConsumerHomeScreen() {
  const session = useStoredSession();
  const nearby = useQuery({
    queryKey: ["consumer-home", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () =>
      apiRequest<NearbyResponse>("get_v1_merchants_nearby", {
        token: session.data?.accessToken,
        query: { lat: 21.0285, lng: 105.8542 }
      })
  });

  const state = session.isLoading || nearby.isLoading ? "loading" : nearby.isError ? "error" : nearby.data?.merchants.length === 0 ? "empty" : "ready";

  return (
    <StateScaffold testIDPrefix="consumer-home" title="Gan ban" subtitle="Danh sach tiem dang mo theo vi tri hien tai." state={state} primaryAction="Dat lich">
      {(nearby.data?.merchants || []).map((merchant) => (
        <DataRow key={merchant.id} label={merchant.name} value={`${merchant.available_bays} vi tri trong`} />
      ))}
    </StateScaffold>
  );
}
