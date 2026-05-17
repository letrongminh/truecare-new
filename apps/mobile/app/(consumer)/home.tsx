import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../components/StateScaffold";
import { apiRequest } from "../../lib/api";
import { requestCurrentLocation } from "../../lib/native-capabilities";
import { useStoredSession } from "../../lib/session-query";

type NearbyResponse = { merchants: Array<{ id: string; name: string; available_bays: number }>; gps_fallback: boolean };

export default function ConsumerHomeScreen() {
  const session = useStoredSession();
  const location = useQuery({
    queryKey: ["consumer-home", "location"],
    queryFn: requestCurrentLocation
  });
  const nearby = useQuery({
    queryKey: ["consumer-home", session.data?.accessToken, location.data?.lat, location.data?.lng],
    enabled: !!session.data?.accessToken && !!location.data,
    queryFn: () =>
      apiRequest<NearbyResponse>("get_v1_merchants_nearby", {
        token: session.data?.accessToken,
        query: { lat: location.data?.lat || 21.0285, lng: location.data?.lng || 105.8542 }
      })
  });

  const state = !session.data?.accessToken ? "forbidden" : session.isLoading || location.isLoading || nearby.isLoading ? "loading" : location.isError || nearby.isError ? "error" : nearby.data?.merchants.length === 0 ? "empty" : location.data?.denied ? "offline" : "ready";

  return (
    <StateScaffold
      testIDPrefix="consumer-home"
      title="Gan ban"
      subtitle="Danh sach tiem dang mo theo vi tri hien tai."
      state={state}
      primaryAction="Lam moi"
      onPrimaryAction={() => {
        location.refetch();
        nearby.refetch();
      }}
      onSecondaryAction={() => nearby.refetch()}
    >
      <DataRow label="GPS" value={location.data?.denied ? "fallback Ha Noi" : "dang dung vi tri hien tai"} />
      {(nearby.data?.merchants || []).map((merchant) => (
        <DataRow key={merchant.id} label={merchant.name} value={`${merchant.available_bays} vi tri trong`} />
      ))}
    </StateScaffold>
  );
}
