import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Merchant = { id: string; name: string; address: string; phone?: string; available_bays: number };
type Services = { services: Array<{ id: string; name: string; price: number; duration_min: number; duration_max: number }> };

export default function MerchantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = useStoredSession();
  const merchant = useQuery({
    queryKey: ["merchant-detail", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Merchant>("get_v1_merchants_by_id", { token: session.data?.accessToken, params: { id } })
  });
  const services = useQuery({
    queryKey: ["merchant-services", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Services>("get_v1_merchants_by_id_services", { token: session.data?.accessToken, params: { id } })
  });
  const state = merchant.isLoading ? "loading" : merchant.isError ? "error" : !merchant.data ? "empty" : "ready";

  return (
    <StateScaffold testIDPrefix="merchant-detail" title={merchant.data?.name || "Chi tiet tiem"} subtitle={merchant.data?.address} state={state} primaryAction="Giu cho">
      <DataRow label="Vi tri trong" value={String(merchant.data?.available_bays ?? 0)} />
      <DataRow label="Dien thoai" value={merchant.data?.phone || "Chua co"} />
      {(services.data?.services || []).map((service) => (
        <DataRow key={service.id} label={service.name} value={`${service.price.toLocaleString("vi-VN")} VND`} />
      ))}
    </StateScaffold>
  );
}
