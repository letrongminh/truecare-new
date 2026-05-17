import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { enqueueMutation } from "../../../lib/offline-queue";
import { useStoredSession } from "../../../lib/session-query";

type Payment = { id: string; amount: number; method: string; status: string; commission_status: string };

export default function PaymentScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = useStoredSession();
  const payment = useQuery({
    queryKey: ["payment", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<Payment>("get_v1_payments_by_id", { token: session.data?.accessToken, params: { id } })
  });

  async function queueClaim() {
    await enqueueMutation({ operationId: "post_v1_payments_by_id_user_claimed", params: { id } });
  }

  return (
    <StateScaffold testIDPrefix="payment" title="Thanh toan" subtitle="QR va tien mat deu duoc xu ly idempotent." state={payment.isLoading ? "loading" : payment.isError ? "error" : "ready"} primaryAction="Da chuyen">
      <DataRow label="So tien" value={`${(payment.data?.amount || 0).toLocaleString("vi-VN")} VND`} />
      <DataRow label="Phuong thuc" value={payment.data?.method || "-"} />
      <DataRow label="Trang thai" value={payment.data?.status || "-"} />
      <DataRow label="Offline queue" value="user-claimed mutation ready" />
      {id ? <DataRow label="Queue action" value="Tap primary; persisted if offline" /> : null}
    </StateScaffold>
  );
}
