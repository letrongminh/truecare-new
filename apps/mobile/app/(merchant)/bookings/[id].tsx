import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Booking = { id: string; status: string; bay_number: number; check_in_token?: string };

export default function MerchantBookingScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const session = useStoredSession();
  const booking = useQuery({
    queryKey: ["merchant-booking", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Booking>("get_v1_bookings_by_id", { token: session.data?.accessToken, params: { id } })
  });
  const transition = useMutation({
    mutationFn: () => {
      const status = booking.data?.status;
      if (status === "held") {
        return apiRequest("post_v1_bookings_by_id_check_in", {
          token: session.data?.accessToken,
          params: { id },
          body: { code: booking.data?.check_in_token || "" }
        });
      }
      if (status === "checked_in") {
        return apiRequest("post_v1_bookings_by_id_start_service", { token: session.data?.accessToken, params: { id } });
      }
      return apiRequest("post_v1_bookings_by_id_complete_service", { token: session.data?.accessToken, params: { id } });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["merchant-booking", id, session.data?.accessToken] })
  });
  const nextLabel = booking.data?.status === "held" ? "Check-in" : booking.data?.status === "checked_in" ? "Bat dau rua" : "Hoan tat";
  return (
    <StateScaffold
      testIDPrefix="merchant-booking"
      title="Xu ly dich vu"
      subtitle="Check-in, anh truoc/sau, bat dau va hoan tat dich vu."
      state={transition.isError ? "error" : booking.isLoading ? "loading" : booking.isError ? "error" : "ready"}
      primaryAction={transition.isPending ? "Dang gui" : nextLabel}
      onPrimaryAction={() => transition.mutate()}
      onSecondaryAction={() => booking.refetch()}
    >
      <DataRow label="Booking" value={booking.data?.id || "-"} />
      <DataRow label="Trang thai" value={booking.data?.status || "-"} />
      <DataRow label="Bay" value={String(booking.data?.bay_number ?? "-")} />
      <DataRow label="Ma QR" value={(booking.data?.check_in_token || "").slice(0, 6).toUpperCase() || "-"} />
      <DataRow label="Mutation" value={transition.isPending ? "Dang gui" : "San sang"} />
    </StateScaffold>
  );
}
