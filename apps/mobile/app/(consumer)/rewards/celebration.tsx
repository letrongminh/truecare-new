import { DataRow, StateScaffold } from "../../../components/StateScaffold";

export default function RewardCelebrationScreen() {
  return (
    <StateScaffold testIDPrefix="reward-celebration" title="Chuc mung" subtitle="Ban da dat nguong thuong moi." primaryAction="Doi ngay">
      <DataRow label="Trang thai" value="Voucher da san sang" />
      <DataRow label="Lua chon" value="Doi ngay hoac de sau" />
    </StateScaffold>
  );
}
