import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { enqueueMutation } from "../../../lib/offline-queue";
import { useStoredSession } from "../../../lib/session-query";

type Payment = { id: string; amount: number; method: string; status: string; commission_status: string };

export default function PaymentScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const session = useStoredSession();
  const payment = useQuery({
    queryKey: ["payment", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Payment>("get_v1_payments_by_id", { token: session.data?.accessToken, params: { id } })
  });

  async function queueClaim() {
    await enqueueMutation({ operationId: "post_v1_payments_by_id_user_claimed", params: { id } });
  }
  const claim = useMutation({
    mutationFn: async () => {
      if (!session.data?.accessToken) {
        await queueClaim();
        return null;
      }
      return apiRequest<Payment>("post_v1_payments_by_id_user_claimed", { token: session.data.accessToken, params: { id } });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["payment", id, session.data?.accessToken] })
  });
  const switchToCash = useMutation({
    mutationFn: () =>
      apiRequest<Payment>("post_v1_payments_by_id_switch_method", {
        token: session.data?.accessToken,
        params: { id },
        body: { method: "cash" }
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["payment", id, session.data?.accessToken] })
  });

  return (
    <StateScaffold
      testIDPrefix="payment"
      title="Thanh toan"
      subtitle="QR va tien mat deu duoc xu ly idempotent."
      state={claim.isError || switchToCash.isError ? "error" : payment.isLoading ? "loading" : payment.isError ? "error" : "ready"}
      primaryAction={claim.isPending ? "Dang xac nhan" : "Da chuyen"}
      secondaryAction={switchToCash.isPending ? "Dang doi" : "Tra tien mat"}
      onPrimaryAction={() => claim.mutate()}
      onSecondaryAction={() => switchToCash.mutate()}
    >
      <DataRow label="So tien" value={`${(payment.data?.amount || 0).toLocaleString("vi-VN")} VND`} />
      <DataRow label="Phuong thuc" value={payment.data?.method || "-"} />
      <DataRow label="Trang thai" value={payment.data?.status || "-"} />
      <DataRow label="Offline queue" value={claim.data === null ? "Da luu user-claimed" : "San sang"} />
      {id ? <DataRow label="Queue action" value="Tap primary; persisted if offline" /> : null}
    </StateScaffold>
  );
}
