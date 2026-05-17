import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Booking = { id: string; status: string; check_in_token?: string };

export default function CheckInScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const session = useStoredSession();
  const booking = useQuery({
    queryKey: ["checkin", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Booking>("get_v1_bookings_by_id", { token: session.data?.accessToken, params: { id } })
  });
  const arrived = useMutation({
    mutationFn: () => apiRequest<Booking>("post_v1_bookings_by_id_arrived", { token: session.data?.accessToken, params: { id } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["checkin", id, session.data?.accessToken] })
  });
  return (
    <StateScaffold
      testIDPrefix="checkin"
      title="Check-in"
      subtitle="Dua ma nay cho tiem quet hoac doc 6 ky tu dau."
      state={arrived.isError ? "error" : booking.isLoading ? "loading" : booking.isError ? "error" : "ready"}
      primaryAction={arrived.isPending ? "Dang bao toi noi" : "Da den tiem"}
      onPrimaryAction={() => arrived.mutate()}
      onSecondaryAction={() => booking.refetch()}
    >
      <DataRow label="Ma ngan" value={(booking.data?.check_in_token || "").slice(0, 6).toUpperCase() || "-"} />
      <DataRow label="Token QR" value={booking.data?.check_in_token || "-"} />
      <DataRow label="Trang thai" value={booking.data?.status || "-"} />
    </StateScaffold>
  );
}
