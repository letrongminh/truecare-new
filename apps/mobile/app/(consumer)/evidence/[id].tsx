import { useLocalSearchParams } from "expo-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DataRow, StateScaffold } from "../../../components/StateScaffold";
import { apiRequest } from "../../../lib/api";
import { ensureCameraReady, queueEvidenceUpload } from "../../../lib/native-capabilities";
import { useStoredSession } from "../../../lib/session-query";

type EvidenceResponse = { evidence: Array<{ id: string; type: string; status: string; quality: string }> };
type EvidencePresign = { evidence_id: string; object_key: string; upload_url: string };

export default function EvidenceScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const queryClient = useQueryClient();
  const session = useStoredSession();
  const evidence = useQuery({
    queryKey: ["evidence", id, session.data?.accessToken],
    enabled: !!id && !!session.data?.accessToken,
    queryFn: () => apiRequest<EvidenceResponse>("get_v1_evidence_by_booking_id", { token: session.data?.accessToken, params: { booking_id: id } })
  });
  const capture = useMutation({
    mutationFn: async () => {
      const cameraReady = await ensureCameraReady();
      const localUri = `local://evidence/${id}/before-${Date.now()}.jpg`;
      if (!cameraReady || !session.data?.accessToken) {
        return queueEvidenceUpload({ bookingId: id, type: "before", localUri });
      }
      const presign = await apiRequest<EvidencePresign>("post_v1_evidence_by_booking_id_presign", {
        token: session.data.accessToken,
        params: { booking_id: id },
        body: { type: "before", content_type: "image/jpeg" }
      });
      return apiRequest("post_v1_evidence_by_evidence_id_confirm", {
        token: session.data.accessToken,
        params: { evidence_id: presign.evidence_id },
        body: { object_key: presign.object_key, perceptual_hash: `mobile-${Date.now()}` }
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["evidence", id, session.data?.accessToken] })
  });

  return (
    <StateScaffold
      testIDPrefix="evidence"
      title="Bang chung"
      subtitle="Anh truoc/sau duoc hang doi offline xu ly khi mat mang."
      state={capture.isError ? "error" : evidence.isLoading ? "loading" : evidence.isError ? "error" : evidence.data?.evidence.length === 0 ? "empty" : "ready"}
      primaryAction={capture.isPending ? "Dang xu ly" : "Chup anh"}
      onPrimaryAction={() => capture.mutate()}
      onSecondaryAction={() => evidence.refetch()}
    >
      {(evidence.data?.evidence || []).map((item) => (
        <DataRow key={item.id} label={item.type} value={`${item.status}/${item.quality}`} />
      ))}
      <DataRow label="Hang doi anh" value={capture.isSuccess ? "Da gui hoac da luu offline" : "San sang"} />
    </StateScaffold>
  );
}
