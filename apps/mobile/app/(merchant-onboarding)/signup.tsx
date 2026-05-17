import { DataRow, StateScaffold } from "../../components/StateScaffold";

export default function MerchantSignupScreen() {
  return (
    <StateScaffold testIDPrefix="merchant-signup" title="Dang ky doi tac" subtitle="Tao ho so chu tiem va ma moi." primaryAction="Bat dau">
      <DataRow label="Vai tro" value="merchant_pending" />
      <DataRow label="Trang thai" value="Cho bo sung thong tin" />
    </StateScaffold>
  );
}
