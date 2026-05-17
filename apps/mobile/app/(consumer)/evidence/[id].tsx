import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { useStoredSession } from "../../../lib/session-query";

type EvidenceResponse = { evidence: Array<{ id: string; type: string; status: string; quality: string }> };

export default function EvidenceScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const session = useStoredSession();
  const evidence = useQuery({
    queryKey: ["evidence", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<EvidenceResponse>("get_v1_evidence_by_booking_id", { token: session.data?.accessToken, params: { booking_id: id } })
  });

  return (
    <StateScaffold testIDPrefix="evidence" title="Bang chung" subtitle="Anh truoc/sau duoc hang doi offline xu ly khi mat mang." state={evidence.isLoading ? "loading" : evidence.isError ? "error" : evidence.data?.evidence.length === 0 ? "empty" : "ready"} primaryAction="Chup anh">
      {(evidence.data?.evidence || []).map((item) => (
        <DataRow key={item.id} label={item.type} value={`${item.status}/${item.quality}`} />
      ))}
    </StateScaffold>
  );
}
