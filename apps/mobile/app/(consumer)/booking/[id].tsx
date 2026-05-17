import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Booking = { id: string; status: string; bay_number: number; total_amount: number; deposit_amount?: number | null; expires_at: string; check_in_token?: string };

export default function BookingDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const session = useStoredSession();
  const booking = useQuery({
    queryKey: ["booking-detail", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Booking>("get_v1_bookings_by_id", { token: session.data?.accessToken, params: { id } })
  });
  const arrived = useMutation({
    mutationFn: () => apiRequest<Booking>("post_v1_bookings_by_id_arrived", { token: session.data?.accessToken, params: { id } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["booking-detail", id, session.data?.accessToken] })
  });
  const cancel = useMutation({
    mutationFn: () =>
      apiRequest<Booking>("post_v1_bookings_by_id_cancel", {
        token: session.data?.accessToken,
        params: { id },
        body: { reason: "mobile_user_cancelled" }
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["booking-detail", id, session.data?.accessToken] })
  });
  const state = booking.isLoading ? "loading" : booking.isError ? "error" : !booking.data ? "empty" : "ready";

  return (
    <StateScaffold
      testIDPrefix="booking-detail"
      title="Lich hen"
      subtitle="Theo doi trang thai giu cho va check-in."
      state={arrived.isError || cancel.isError ? "error" : state}
      primaryAction={arrived.isPending ? "Dang bao da den" : "Toi da den"}
      secondaryAction={cancel.isPending ? "Dang huy" : "Huy lich"}
      onPrimaryAction={() => arrived.mutate()}
      onSecondaryAction={() => cancel.mutate()}
    >
      <DataRow label="Trang thai" value={booking.data?.status || "-"} />
      <DataRow label="Vi tri" value={String(booking.data?.bay_number ?? "-")} />
      <DataRow label="Thanh tien" value={`${(booking.data?.total_amount || 0).toLocaleString("vi-VN")} VND`} />
      <DataRow label="Dat coc" value={booking.data?.deposit_amount ? `${booking.data.deposit_amount.toLocaleString("vi-VN")} VND` : "Khong yeu cau"} />
      <DataRow label="Het han" value={booking.data?.expires_at || "-"} />
      <DataRow label="Ma ngan" value={(booking.data?.check_in_token || "").slice(0, 6).toUpperCase() || "-"} />
    </StateScaffold>
  );
}
