import { useMutation } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../components/StateScaffold";
import { apiRequest } from "../../lib/api";
import { useStoredSession } from "../../lib/session-query";

export default function QuickProfileScreen() {
  const session = useStoredSession();
  const save = useMutation({
    mutationFn: async () => {
      if (!session.data?.accessToken) {
        throw new Error("missing_session");
      }
      await apiRequest("patch_v1_me_profile", {
        token: session.data.accessToken,
        body: { display_name: "TrueCare user", locale: "vi" }
      });
      return apiRequest("post_v1_me_vehicles", {
        token: session.data.accessToken,
        body: { kind: "sedan", license_plate: "30A-00000", is_default: true }
      });
    }
  });
  return (
    <StateScaffold
      testIDPrefix="quick-profile"
      title="Ho so nhanh"
      subtitle="Thong tin nay giup tiem nhan dien xe va lien he khi can."
      state={!session.data?.accessToken ? "forbidden" : save.isError ? "error" : save.isPending ? "loading" : "ready"}
      primaryAction="Luu ho so"
      onPrimaryAction={() => save.mutate()}
    >
      <DataRow label="Ten hien thi" value={save.isSuccess ? "TrueCare user" : "Chua cap nhat"} />
      <DataRow label="Xe" value={save.isSuccess ? "30A-00000" : "Them sau"} />
      <DataRow label="Ngon ngu" value="Tieng Viet" />
    </StateScaffold>
  );
}
