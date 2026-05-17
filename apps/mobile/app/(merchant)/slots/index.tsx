import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { usePrincipal } from "../../../lib/principal";

type Calendar = { bays: Array<{ bay_number: number; time_slot: string; status: string }> };
type GoldenHour = { rules: Array<{ day_of_week: number; start_time: string; end_time: string; discount_percent: number }> };

export default function MerchantSlotsScreen() {
  const { principal, token } = usePrincipal();
  const queryClient = useQueryClient();
  const merchantId = principal.data?.merchant_id || null;
  const calendar = useQuery({
    queryKey: ["merchant-slots", token, merchantId],
    enabled: !!token && !!merchantId,
    queryFn: () => apiRequest<Calendar>("get_v1_merchants_by_id_calendar", { token, params: { id: merchantId || "" } })
  });
  const goldenHour = useQuery({
    queryKey: ["merchant-golden-hour", token, merchantId],
    enabled: !!token && !!merchantId,
    queryFn: () => apiRequest<GoldenHour>("get_v1_merchants_by_id_golden_hour", { token, params: { id: merchantId || "" } })
  });
  const maintenance = useMutation({
    mutationFn: () => {
      const firstBay = calendar.data?.bays[0];
      if (!merchantId || !firstBay) {
        throw new Error("missing_slot");
      }
      return apiRequest("post_v1_merchants_by_id_calendar_maintenance", {
        token,
        params: { id: merchantId },
        body: { bay_number: firstBay.bay_number, time_slot: firstBay.time_slot, status: "maintenance" }
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["merchant-slots", token, merchantId] })
  });
  const state = !token ? "forbidden" : principal.isLoading ? "loading" : !merchantId ? "empty" : maintenance.isError || calendar.isError || goldenHour.isError ? "error" : calendar.isLoading || goldenHour.isLoading ? "loading" : "ready";
  return (
    <StateScaffold
      testIDPrefix="merchant-slots"
      title="Lich va vi tri"
      subtitle="Quan ly bay, bao tri, gio vang va gia dich vu."
      state={state}
      primaryAction={maintenance.isPending ? "Dang dong bay" : "Dong bay dau tien"}
      onPrimaryAction={() => maintenance.mutate()}
      onSecondaryAction={() => {
        calendar.refetch();
        goldenHour.refetch();
      }}
    >
      <DataRow label="Merchant" value={merchantId || "Chua co merchant"} />
      <DataRow label="Bay dang mo" value={String(calendar.data?.bays.filter((bay) => bay.status === "available").length ?? 0)} />
      <DataRow label="Bao tri" value={String(calendar.data?.bays.filter((bay) => bay.status === "maintenance" || bay.status === "closed").length ?? 0)} />
      <DataRow label="Golden hour" value={String(goldenHour.data?.rules.length ?? 0)} />
    </StateScaffold>
  );
}
