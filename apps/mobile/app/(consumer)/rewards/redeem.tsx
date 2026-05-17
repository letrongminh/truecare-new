import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Vouchers = { vouchers: Array<{ id: string; status: string; expires_at: string }> };

export default function RewardRedeemScreen() {
  const session = useStoredSession();
  const queryClient = useQueryClient();
  const vouchers = useQuery({
    queryKey: ["reward-redeem", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Vouchers>("get_v1_rewards_vouchers", { token: session.data?.accessToken })
  });
  const firstVoucher = vouchers.data?.vouchers[0];
  const reserve = useMutation({
    mutationFn: () => {
      if (!firstVoucher) {
        throw new Error("missing_voucher");
      }
      return apiRequest("post_v1_rewards_vouchers_by_id_reserve", {
        token: session.data?.accessToken,
        params: { id: firstVoucher.id },
        body: {}
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reward-redeem", session.data?.accessToken] })
  });
  const redeem = useMutation({
    mutationFn: () => {
      if (!firstVoucher) {
        throw new Error("missing_voucher");
      }
      return apiRequest("post_v1_rewards_vouchers_by_id_redeem", {
        token: session.data?.accessToken,
        params: { id: firstVoucher.id },
        body: {}
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reward-redeem", session.data?.accessToken] })
  });
  return (
    <StateScaffold
      testIDPrefix="reward-redeem"
      title="Doi voucher"
      subtitle="Chon voucher phu hop dich vu."
      state={reserve.isError || redeem.isError ? "error" : vouchers.isLoading ? "loading" : vouchers.isError ? "error" : vouchers.data?.vouchers.length === 0 ? "empty" : "ready"}
      primaryAction={reserve.isPending ? "Dang giu" : "Giu voucher"}
      secondaryAction={redeem.isPending ? "Dang doi" : "Doi voucher"}
      onPrimaryAction={() => reserve.mutate()}
      onSecondaryAction={() => redeem.mutate()}
    >
      {(vouchers.data?.vouchers || []).map((voucher) => (
        <DataRow key={voucher.id} label={voucher.status} value={voucher.expires_at} />
      ))}
    </StateScaffold>
  );
}
