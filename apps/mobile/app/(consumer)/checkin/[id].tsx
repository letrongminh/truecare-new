import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Booking = { id: string; status: string; check_in_token?: string };

export default function CheckInScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = useStoredSession();
  const booking = useQuery({
    queryKey: ["checkin", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Booking>("get_v1_bookings_by_id", { token: session.data?.accessToken, params: { id } })
  });
  return (
    <StateScaffold testIDPrefix="checkin" title="Check-in" subtitle="Dua ma nay cho tiem quet hoac doc 6 ky tu dau." state={booking.isLoading ? "loading" : booking.isError ? "error" : "ready"} primaryAction="Da den tiem">
      <DataRow label="Ma ngan" value={(booking.data?.check_in_token || "").slice(0, 6).toUpperCase() || "-"} />
      <DataRow label="Token QR" value={booking.data?.check_in_token || "-"} />
    </StateScaffold>
  );
}
