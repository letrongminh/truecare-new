import { DataRow, StateScaffold } from "../../../components/StateScaffold";

export default function MerchantSlotsScreen() {
  return (
    <StateScaffold testIDPrefix="merchant-slots" title="Lich va vi tri" subtitle="Quan ly bay, bao tri, gio vang va gia dich vu." primaryAction="Cap nhat lich">
      <DataRow label="Bay dang mo" value="Theo slot_capacity" />
      <DataRow label="Bao tri" value="Chua dat" />
      <DataRow label="Golden hour" value="P0 backend ready" />
    </StateScaffold>
  );
}
