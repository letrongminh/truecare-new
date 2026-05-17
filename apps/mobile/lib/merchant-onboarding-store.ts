let merchantId = "";

export function setMerchantOnboardingId(id: string) {
  merchantId = id;
}

export function getMerchantOnboardingId() {
  return merchantId;
}
