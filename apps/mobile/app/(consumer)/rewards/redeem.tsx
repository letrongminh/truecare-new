import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Vouchers = { vouchers: Array<{ id: string; status: string; expires_at: string }> };

export default function RewardRedeemScreen() {
  const session = useStoredSession();
  const vouchers = useQuery({
    queryKey: ["reward-redeem", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Vouchers>("get_v1_rewards_vouchers", { token: session.data?.accessToken })
  });
  return (
    <StateScaffold testIDPrefix="reward-redeem" title="Doi voucher" subtitle="Chon voucher phu hop dich vu." state={vouchers.isLoading ? "loading" : vouchers.isError ? "error" : vouchers.data?.vouchers.length === 0 ? "empty" : "ready"} primaryAction="Ap dung">
      {(vouchers.data?.vouchers || []).map((voucher) => (
        <DataRow key={voucher.id} label={voucher.status} value={voucher.expires_at} />
      ))}
    </StateScaffold>
  );
}
