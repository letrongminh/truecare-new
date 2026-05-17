import { useLocalSearchParams } from "expo-router";
import { useRouter } from "expo-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Merchant = { id: string; name: string; address: string; phone?: string; available_bays: number };
type Services = { services: Array<{ id: string; name: string; price: number; duration_min: number; duration_max: number }> };

export default function MerchantDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
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
  const hold = useMutation({
    mutationFn: async () => {
      const firstService = services.data?.services[0];
      if (!id || !firstService || !session.data?.accessToken) {
        throw new Error("missing_booking_context");
      }
      return apiRequest<{ id: string }>("post_v1_bookings_holds", {
        token: session.data.accessToken,
        body: {
          merchant_id: id,
          merchant_service_id: firstService.id,
          bay_number: 1,
          idempotency_key: `mobile-hold-${Date.now()}`
        }
      });
    },
    onSuccess: (booking) => router.push(`/(consumer)/booking/${booking.id}`)
  });
  const state = merchant.isLoading ? "loading" : merchant.isError ? "error" : !merchant.data ? "empty" : "ready";

  return (
    <StateScaffold
      testIDPrefix="merchant-detail"
      title={merchant.data?.name || "Chi tiet tiem"}
      subtitle={merchant.data?.address}
      state={hold.isError ? "error" : state}
      primaryAction={hold.isPending ? "Dang giu cho" : "Giu cho"}
      onPrimaryAction={() => hold.mutate()}
      onSecondaryAction={() => {
        merchant.refetch();
        services.refetch();
      }}
    >
      <DataRow label="Vi tri trong" value={String(merchant.data?.available_bays ?? 0)} />
      <DataRow label="Dien thoai" value={merchant.data?.phone || "Chua co"} />
      <DataRow label="Trang thai giu cho" value={hold.isError ? "Can thu lai" : hold.isSuccess ? "Da tao" : "San sang"} />
      {(services.data?.services || []).map((service) => (
        <DataRow key={service.id} label={service.name} value={`${service.price.toLocaleString("vi-VN")} VND`} />
      ))}
    </StateScaffold>
  );
}
