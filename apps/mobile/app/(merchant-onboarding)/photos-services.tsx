import { useState } from "react";
import { TextInput } from "react-native";
import { DataRow, StateScaffold } from "../../components/StateScaffold";
import { apiRequest } from "../../lib/api";
import { getMerchantOnboardingId, setMerchantOnboardingId } from "../../lib/merchant-onboarding-store";
import { useStoredSession } from "../../lib/session-query";

type MerchantAdmissionDto = {
  id: string;
  photo_status: string;
  storefront_photo_url?: string | null;
  bay_photo_url?: string | null;
};

const inputStyle = { minHeight: 48, borderWidth: 1, borderColor: "#d0d5dd", borderRadius: 8, paddingHorizontal: 12 };

export default function MerchantPhotosServicesScreen() {
  const session = useStoredSession();
  const [merchantId, setMerchantId] = useState(getMerchantOnboardingId());
  const [state, setState] = useState<"ready" | "loading" | "empty" | "error">("ready");
  const [merchant, setMerchant] = useState<MerchantAdmissionDto | null>(null);

  async function submit() {
    if (!session.data?.accessToken || !merchantId) {
      setState("empty");
      return;
    }
    setState("loading");
    try {
      const response = await apiRequest<MerchantAdmissionDto>("post_v1_merchants_by_id_confirm_photo", {
        token: session.data.accessToken,
        params: { id: merchantId },
        body: {
          storefront_object_key: `merchant/${merchantId}/storefront.jpg`,
          bay_object_key: `merchant/${merchantId}/bay.jpg`
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
    <StateScaffold testIDPrefix="merchant-photos-services" title="Anh va dich vu" subtitle="Chup anh mat tien, khu rua va cau hinh dich vu." state={screenState} primaryAction="Gui duyet" onPrimaryAction={submit} onSecondaryAction={() => setState("ready")}>
      <TextInput testID="merchant-photos-services-merchant-id" placeholder="Merchant ID" value={merchantId} onChangeText={setMerchantId} style={inputStyle} />
      <DataRow label="Anh mat tien" value={merchant?.storefront_photo_url || "merchant/{id}/storefront.jpg"} />
      <DataRow label="Anh bay" value={merchant?.bay_photo_url || "merchant/{id}/bay.jpg"} />
      <DataRow label="Trang thai anh" value={merchant?.photo_status || "missing"} />
      <DataRow label="Dich vu tuy chinh" value="Toi da 3 active" />
    </StateScaffold>
  );
}
