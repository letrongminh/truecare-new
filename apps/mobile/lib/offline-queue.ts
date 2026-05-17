import * as FileSystem from "expo-file-system/legacy";
import { apiRequest, type ApiSession } from "./api";

export type OfflineMutation = {
  id: string;
  operationId: string;
  params?: Record<string, string>;
  body?: unknown;
  createdAt: number;
  attempts: number;
};

const queueFile = `${FileSystem.documentDirectory || ""}truecare-offline-queue.json`;
let memoryQueue: OfflineMutation[] = [];

async function readQueue() {
  if (!FileSystem.documentDirectory) {
    return memoryQueue;
  }
  try {
    const encoded = await FileSystem.readAsStringAsync(queueFile);
    memoryQueue = JSON.parse(encoded) as OfflineMutation[];
  } catch {
    memoryQueue = [];
  }
  return memoryQueue;
}

async function writeQueue(queue: OfflineMutation[]) {
  memoryQueue = queue;
  if (!FileSystem.documentDirectory) {
    return;
  }
  await FileSystem.writeAsStringAsync(queueFile, JSON.stringify(queue));
}

export async function enqueueMutation(mutation: Omit<OfflineMutation, "id" | "createdAt" | "attempts">) {
  const queue = await readQueue();
  const item: OfflineMutation = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    createdAt: Date.now(),
    attempts: 0,
    ...mutation
  };
  await writeQueue([...queue, item]);
  return item;
}

export async function getOfflineQueue() {
  return readQueue();
}

export async function flushOfflineQueue(session: ApiSession) {
  const queue = await readQueue();
  const remaining: OfflineMutation[] = [];
  for (const item of queue) {
    try {
      await apiRequest(item.operationId, {
        params: item.params,
        body: item.body,
        token: session.accessToken
      });
    } catch {
      remaining.push({ ...item, attempts: item.attempts + 1 });
    }
  }
  await writeQueue(remaining);
  return { flushed: queue.length - remaining.length, remaining: remaining.length };
}
