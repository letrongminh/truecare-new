import { DataRow, StateScaffold } from "../../components/StateScaffold";

export default function MerchantShopInfoScreen() {
  return (
    <StateScaffold testIDPrefix="merchant-shop-info" title="Thong tin cua tiem" subtitle="Dia chi, so bay, gio hoat dong." primaryAction="Luu thong tin">
      <DataRow label="Dia chi" value="Can cap nhat" />
      <DataRow label="So bay" value="0" />
      <DataRow label="Gio mo cua" value="08:00-20:00" />
    </StateScaffold>
  );
}
