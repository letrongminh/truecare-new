import { useState } from "react";
import { TextInput } from "react-native";
import { DataRow, StateScaffold } from "../../components/StateScaffold";
import { apiRequest } from "../../lib/api";
import { setMerchantOnboardingId } from "../../lib/merchant-onboarding-store";
import { useStoredSession } from "../../lib/session-query";

type MerchantAdmissionDto = {
  id: string;
  status: string;
  pipeline_status: string;
};

const inputStyle = { minHeight: 48, borderWidth: 1, borderColor: "#d0d5dd", borderRadius: 8, paddingHorizontal: 12 };

export default function MerchantShopInfoScreen() {
  const session = useStoredSession();
  const [name, setName] = useState("TrueCare Pilot Wash");
  const [address, setAddress] = useState("7 Nguyen Trai, Ha Dong, Ha Noi");
  const [phone, setPhone] = useState("+84901234567");
  const [bayCount, setBayCount] = useState("2");
  const [merchant, setMerchant] = useState<MerchantAdmissionDto | null>(null);
  const [state, setState] = useState<"ready" | "loading" | "error">("ready");

  async function submit() {
    if (!session.data?.accessToken) {
      return;
    }
    setState("loading");
    try {
      const response = await apiRequest<MerchantAdmissionDto>("post_v1_merchants_applications", {
        token: session.data.accessToken,
        body: {
          name,
          address,
          phone,
          latitude: 21.0278,
          longitude: 105.8342,
          bay_count: Number.parseInt(bayCount, 10) || 1,
          operating_hours_start: "08:00",
          operating_hours_end: "20:00"
        }
      });
      setMerchant(response);
      setMerchantOnboardingId(response.id);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  const screenState = !session.data?.accessToken ? "forbidden" : session.isLoading || state === "loading" ? "loading" : state;

  return (
    <StateScaffold testIDPrefix="merchant-shop-info" title="Thong tin cua tiem" subtitle="Dia chi, so bay, gio hoat dong." state={screenState} primaryAction="Luu thong tin" onPrimaryAction={submit} onSecondaryAction={() => setState("ready")}>
      <TextInput testID="merchant-shop-info-name" placeholder="Ten tiem" value={name} onChangeText={setName} style={inputStyle} />
      <TextInput testID="merchant-shop-info-address" placeholder="Dia chi" value={address} onChangeText={setAddress} style={inputStyle} />
      <TextInput testID="merchant-shop-info-phone" placeholder="So dien thoai" value={phone} onChangeText={setPhone} style={inputStyle} />
      <TextInput testID="merchant-shop-info-bay-count" placeholder="So bay" value={bayCount} onChangeText={setBayCount} keyboardType="number-pad" style={inputStyle} />
      <DataRow label="Merchant ID" value={merchant?.id || "Chua tao"} />
      <DataRow label="Trang thai" value={merchant?.status || "pending_review"} />
      <DataRow label="Pipeline" value={merchant?.pipeline_status || "pending_setup"} />
    </StateScaffold>
  );
}
