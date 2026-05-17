import { useMutation, useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { registerPushToken } from "../../../lib/native-capabilities";
import { useStoredSession } from "../../../lib/session-query";

type Profile = {
  user_id: string;
  tenant_id: string;
  display_name: string;
  locale: string;
  email?: string;
  phone?: string;
  referral_code?: string;
  no_show_count: number;
};
type VehicleList = { vehicles: Array<{ id: string; kind: string; license_plate?: string; is_default: boolean }> };
type Sessions = { sessions: Array<{ id: string; current: boolean; created_at: string }> };
type Preferences = { booking_updates: boolean; golden_hour: boolean; referral_reward: boolean; wash_reminder: boolean };

export default function ProfileScreen() {
  const session = useStoredSession();
  const token = session.data?.accessToken;
  const profile = useQuery({
    queryKey: ["profile", session.data?.accessToken],
    enabled: !!token,
    queryFn: () => apiRequest<Profile>("get_v1_me_profile", { token })
  });
  const vehicles = useQuery({
    queryKey: ["profile", "vehicles", token],
    enabled: !!token,
    queryFn: () => apiRequest<VehicleList>("get_v1_me_vehicles", { token })
  });
  const sessions = useQuery({
    queryKey: ["profile", "sessions", token],
    enabled: !!token,
    queryFn: () => apiRequest<Sessions>("get_v1_me_sessions", { token })
  });
  const preferences = useQuery({
    queryKey: ["profile", "preferences", token],
    enabled: !!token,
    queryFn: () => apiRequest<Preferences>("get_v1_me_notifications_preferences", { token })
  });
  const push = useMutation({
    mutationFn: async () => {
      if (!session.data) {
        throw new Error("missing_session");
      }
      return registerPushToken(session.data);
    }
  });
  const dataExport = useMutation({
    mutationFn: () => apiRequest("post_v1_me_data_export", { token })
  });
  const loading = profile.isLoading || vehicles.isLoading || sessions.isLoading || preferences.isLoading;
  const error = profile.isError || vehicles.isError || sessions.isError || preferences.isError;
  return (
    <StateScaffold
      testIDPrefix="profile"
      title="Ho so"
      subtitle="Thong tin tai khoan, quyen rieng tu va phien dang nhap."
      state={!token ? "forbidden" : push.isError || dataExport.isError || error ? "error" : loading ? "loading" : "ready"}
      primaryAction={push.isPending ? "Dang dang ky" : "Dang ky push"}
      secondaryAction={dataExport.isPending ? "Dang tao" : "Xuat du lieu"}
      onPrimaryAction={() => push.mutate()}
      onSecondaryAction={() => dataExport.mutate()}
    >
      <DataRow label="Ten" value={profile.data?.display_name || "-"} />
      <DataRow label="Tai khoan" value={profile.data?.email || profile.data?.phone || "-"} />
      <DataRow label="Ma gioi thieu" value={profile.data?.referral_code || "-"} />
      <DataRow label="So xe" value={String(vehicles.data?.vehicles.length ?? 0)} />
      <DataRow label="Phien dang nhap" value={String(sessions.data?.sessions.length ?? 0)} />
      <DataRow label="Thong bao dat lich" value={preferences.data?.booking_updates ? "bat" : "tat"} />
      <DataRow label="Golden Hour" value={preferences.data?.golden_hour ? "bat" : "tat"} />
      <DataRow label="Locale" value={profile.data?.locale || "vi"} />
      <DataRow label="No-show" value={String(profile.data?.no_show_count ?? 0)} />
      <DataRow label="Push" value={push.data?.registered ? "da dang ky" : push.data?.reason || "chua dang ky"} />
      <DataRow label="Data export" value={dataExport.isSuccess ? "da tao yeu cau" : "chua tao"} />
    </StateScaffold>
  );
}
