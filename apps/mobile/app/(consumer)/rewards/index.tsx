import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type Progress = { finalized_stamps: number; pending_stamps: number; threshold: number; next_reward_at: number };

export default function RewardsScreen() {
  const session = useStoredSession();
  const progress = useQuery({
    queryKey: ["rewards", session.data?.accessToken],
    enabled: !!session.data?.accessToken,
    queryFn: () => apiRequest<Progress>("get_v1_rewards_progress", { token: session.data?.accessToken })
  });
  return (
    <StateScaffold testIDPrefix="rewards" title="Reward Center" subtitle="Theo doi stamp va voucher kha dung." state={progress.isLoading ? "loading" : progress.isError ? "error" : "ready"} primaryAction="Doi thuong">
      <DataRow label="Stamp da chot" value={String(progress.data?.finalized_stamps ?? 0)} />
      <DataRow label="Stamp dang cho" value={String(progress.data?.pending_stamps ?? 0)} />
      <DataRow label="Can them" value={String(progress.data?.next_reward_at ?? 5)} />
    </StateScaffold>
  );
}
