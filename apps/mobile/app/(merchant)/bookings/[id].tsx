import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Booking = { id: string; status: string; bay_number: number; check_in_token?: string };

export default function MerchantBookingScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = useStoredSession();
  const booking = useQuery({
    queryKey: ["merchant-booking", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Booking>("get_v1_bookings_by_id", { token: session.data?.accessToken, params: { id } })
  });
  const start = useMutation({
    mutationFn: () => apiRequest("post_v1_bookings_by_id_start_service", { token: session.data?.accessToken, params: { id } })
  });
  return (
    <StateScaffold testIDPrefix="merchant-booking" title="Xu ly dich vu" subtitle="Check-in, anh truoc/sau, bat dau va hoan tat dich vu." state={booking.isLoading ? "loading" : booking.isError ? "error" : "ready"} primaryAction="Bat dau rua">
      <DataRow label="Booking" value={booking.data?.id || "-"} />
      <DataRow label="Trang thai" value={booking.data?.status || "-"} />
      <DataRow label="Bay" value={String(booking.data?.bay_number ?? "-")} />
      <DataRow label="Mutation" value={start.isPending ? "Dang gui" : "San sang"} />
    </StateScaffold>
  );
}
