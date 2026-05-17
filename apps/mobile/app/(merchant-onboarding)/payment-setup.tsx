import { useState } from "react";
import { TextInput } from "react-native";
import { DataRow, StateScaffold } from "../../components/StateScaffold";
import { apiRequest } from "../../lib/api";
import { getMerchantOnboardingId, setMerchantOnboardingId } from "../../lib/merchant-onboarding-store";
import { useStoredSession } from "../../lib/session-query";

type MerchantAdmissionDto = {
  id: string;
  payment_recipient_status: string;
};

type MerchantEkycStatusResponse = {
  ekyc_status: string;
  submissions: { kind: string }[];
};

const inputStyle = { minHeight: 48, borderWidth: 1, borderColor: "#d0d5dd", borderRadius: 8, paddingHorizontal: 12 };

export default function MerchantPaymentSetupScreen() {
  const session = useStoredSession();
  const [merchantId, setMerchantId] = useState(getMerchantOnboardingId());
  const [bankName, setBankName] = useState("VCB");
  const [accountNumber, setAccountNumber] = useState("0123456789");
  const [accountHolderName, setAccountHolderName] = useState("TRUECARE OWNER");
  const [merchant, setMerchant] = useState<MerchantAdmissionDto | null>(null);
  const [ekyc, setEkyc] = useState<MerchantEkycStatusResponse | null>(null);
  const [state, setState] = useState<"ready" | "loading" | "empty" | "error">("ready");

  async function submit() {
    if (!session.data?.accessToken || !merchantId) {
      setState("empty");
      return;
    }
    setState("loading");
    try {
      const response = await apiRequest<MerchantAdmissionDto>("post_v1_merchants_by_id_payment_setup", {
        token: session.data.accessToken,
        params: { id: merchantId },
        body: {
          bank_name: bankName,
          account_number: accountNumber,
          account_holder_name: accountHolderName,
          qr_object_key: `merchant/${merchantId}/payment-qr.png`
        }
      });
      let latest: MerchantEkycStatusResponse | null = null;
      for (const kind of ["cmnd", "selfie", "bank"]) {
        latest = await apiRequest<MerchantEkycStatusResponse>(`post_v1_merchants_by_id_ekyc_${kind}`, {
          token: session.data.accessToken,
          params: { id: merchantId },
          body: { object_key: `merchant/${merchantId}/ekyc/${kind}.jpg` }
        });
      }
      setMerchant(response);
      setEkyc(latest);
      setMerchantOnboardingId(response.id);
      setState("ready");
    } catch {
      setState("error");
    }
  }

  const screenState = !session.data?.accessToken ? "forbidden" : session.isLoading || state === "loading" ? "loading" : state;

  return (
    <StateScaffold testIDPrefix="merchant-payment-setup" title="Cai dat thanh toan" subtitle="Tai QR ngan hang va thong tin nguoi nhan." state={screenState} primaryAction="Gui xac minh" onPrimaryAction={submit} onSecondaryAction={() => setState("ready")}>
      <TextInput testID="merchant-payment-setup-merchant-id" placeholder="Merchant ID" value={merchantId} onChangeText={setMerchantId} style={inputStyle} />
      <TextInput testID="merchant-payment-setup-bank" placeholder="Ngan hang" value={bankName} onChangeText={setBankName} style={inputStyle} />
      <TextInput testID="merchant-payment-setup-account-number" placeholder="So tai khoan" value={accountNumber} onChangeText={setAccountNumber} style={inputStyle} />
      <TextInput testID="merchant-payment-setup-account-holder" placeholder="Chu tai khoan" value={accountHolderName} onChangeText={setAccountHolderName} style={inputStyle} />
      <DataRow label="QR" value={`merchant/${merchantId || "{id}"}/payment-qr.png`} />
      <DataRow label="Thanh toan" value={merchant?.payment_recipient_status || "missing"} />
      <DataRow label="eKYC" value={ekyc?.ekyc_status || "not_submitted"} />
      <DataRow label="Ho so eKYC" value={String(ekyc?.submissions.length || 0)} />
    </StateScaffold>
  );
}
