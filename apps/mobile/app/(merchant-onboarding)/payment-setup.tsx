import { DataRow, StateScaffold } from "../../components/StateScaffold";

export default function MerchantPaymentSetupScreen() {
  return (
    <StateScaffold testIDPrefix="merchant-payment-setup" title="Cai dat thanh toan" subtitle="Tai QR ngan hang va thong tin nguoi nhan." primaryAction="Gui xac minh">
      <DataRow label="Ngan hang" value="Chua cap nhat" />
      <DataRow label="QR" value="Can xac minh" />
      <DataRow label="Trang thai" value="pending_review" />
    </StateScaffold>
  );
}
