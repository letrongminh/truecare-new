import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Booking = { id: string; status: string; bay_number: number; total_amount: number; expires_at: string; check_in_token?: string };

export default function BookingDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = useStoredSession();
  const booking = useQuery({
    queryKey: ["booking-detail", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Booking>("get_v1_bookings_by_id", { token: session.data?.accessToken, params: { id } })
  });
  const state = booking.isLoading ? "loading" : booking.isError ? "error" : !booking.data ? "empty" : "ready";

  return (
    <StateScaffold testIDPrefix="booking-detail" title="Lich hen" subtitle="Theo doi trang thai giu cho va check-in." state={state} primaryAction="Mo ma QR">
      <DataRow label="Trang thai" value={booking.data?.status || "-"} />
      <DataRow label="Vi tri" value={String(booking.data?.bay_number ?? "-")} />
      <DataRow label="Thanh tien" value={`${(booking.data?.total_amount || 0).toLocaleString("vi-VN")} VND`} />
      <DataRow label="Het han" value={booking.data?.expires_at || "-"} />
    </StateScaffold>
  );
}
