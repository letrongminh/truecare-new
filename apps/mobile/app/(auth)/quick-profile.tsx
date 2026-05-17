import { DataRow, StateScaffold } from "../../components/StateScaffold";

export default function QuickProfileScreen() {
  return (
    <StateScaffold testIDPrefix="quick-profile" title="Ho so nhanh" subtitle="Thong tin nay giup tiem nhan dien xe va lien he khi can." primaryAction="Luu ho so">
      <DataRow label="Ten hien thi" value="Chua cap nhat" />
      <DataRow label="Xe" value="Them sau" />
      <DataRow label="Ngon ngu" value="Tieng Viet" />
    </StateScaffold>
  );
}
