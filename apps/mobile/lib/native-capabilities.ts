import { Camera, scanFromURLAsync } from "expo-camera";
import * as Device from "expo-device";
import * as FileSystem from "expo-file-system/legacy";
import * as Location from "expo-location";
import * as Notifications from "expo-notifications";
import { apiRequest, type ApiSession } from "./api";
import { enqueueMutation } from "./offline-queue";

export type LocationFix = {
  lat: number;
  lng: number;
  accuracy?: number | null;
  denied?: boolean;
};

export async function requestCurrentLocation(): Promise<LocationFix> {
  const permission = await Location.requestForegroundPermissionsAsync();
  if (permission.status !== "granted") {
    return { lat: 21.0285, lng: 105.8542, denied: true };
  }
  const fix = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
  return {
    lat: fix.coords.latitude,
    lng: fix.coords.longitude,
    accuracy: fix.coords.accuracy,
    denied: false
  };
}

export async function ensureCameraReady() {
  const permission = await Camera.requestCameraPermissionsAsync();
  return permission.status === "granted";
}

export async function scanQrFromFile(uri: string) {
  const results = await scanFromURLAsync(uri, ["qr"]);
  return results[0]?.data || null;
}

export async function persistEvidenceFile(sourceUri: string, bookingId: string, type: "before" | "after" | "other") {
  if (!FileSystem.documentDirectory) {
    return sourceUri;
  }
  const target = `${FileSystem.documentDirectory}evidence-${bookingId}-${type}-${Date.now()}.jpg`;
  await FileSystem.copyAsync({ from: sourceUri, to: target });
  return target;
}

export async function queueEvidenceUpload(input: {
  bookingId: string;
  type: "before" | "after" | "other";
  localUri: string;
  contentType?: string;
}) {
  return enqueueMutation({
    operationId: "post_v1_evidence_by_booking_id_presign",
    params: { booking_id: input.bookingId },
    body: { type: input.type, content_type: input.contentType || "image/jpeg", local_uri: input.localUri }
  });
}

export async function registerPushToken(session: ApiSession) {
  const permission = await Notifications.requestPermissionsAsync();
  if (permission.status !== "granted") {
    return { registered: false, reason: "permission_denied" };
  }
  const token = await Notifications.getExpoPushTokenAsync();
  await apiRequest("post_v1_me_notifications_register", {
    token: session.accessToken,
    body: {
      token: token.data,
      platform: Device.osName || "unknown",
      device_id: Device.modelId || Device.modelName || "unknown-device"
    }
  });
  return { registered: true, token: token.data };
}
