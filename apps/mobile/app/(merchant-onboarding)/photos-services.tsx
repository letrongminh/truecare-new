import { DataRow, StateScaffold } from "../../components/StateScaffold";

export default function MerchantPhotosServicesScreen() {
  return (
    <StateScaffold testIDPrefix="merchant-photos-services" title="Anh va dich vu" subtitle="Chup anh mat tien, khu rua va cau hinh dich vu." primaryAction="Gui duyet">
      <DataRow label="Anh mat tien" value="Hang doi upload" />
      <DataRow label="Anh bay" value="Hang doi upload" />
      <DataRow label="Dich vu tuy chinh" value="Toi da 3 active" />
    </StateScaffold>
  );
}
