import { useMutation, useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Progress = { finalized_stamps: number; pending_stamps: number; threshold: number; next_reward_at: number };
type Referral = { referral_code?: string | null; referrals: Array<{ id: string; status: string; reward_status: string }> };

export default function RewardsScreen() {
  const session = useStoredSession();
  const progress = useQuery({
    queryKey: ["rewards", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Progress>("get_v1_rewards_progress", { token: session.data?.accessToken })
  });
  const referral = useQuery({
    queryKey: ["referrals", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Referral>("get_v1_referrals_me", { token: session.data?.accessToken })
  });
  const share = useMutation({
    mutationFn: () =>
      apiRequest("post_v1_referrals_share_event", {
        token: session.data?.accessToken,
        body: { channel: "mobile_share" }
      })
  });
  return (
    <StateScaffold
      testIDPrefix="rewards"
      title="Reward Center"
      subtitle="Theo doi stamp va voucher kha dung."
      state={share.isError || progress.isError || referral.isError ? "error" : progress.isLoading || referral.isLoading ? "loading" : "ready"}
      primaryAction={share.isPending ? "Dang chia se" : "Chia se ma moi"}
      onPrimaryAction={() => share.mutate()}
      onSecondaryAction={() => {
        progress.refetch();
        referral.refetch();
      }}
    >
      <DataRow label="Stamp da chot" value={String(progress.data?.finalized_stamps ?? 0)} />
      <DataRow label="Stamp dang cho" value={String(progress.data?.pending_stamps ?? 0)} />
      <DataRow label="Can them" value={String(progress.data?.next_reward_at ?? 5)} />
      <DataRow label="Ma moi" value={referral.data?.referral_code || "-"} />
      <DataRow label="Luot gioi thieu" value={String(referral.data?.referrals.length ?? 0)} />
    </StateScaffold>
  );
}
