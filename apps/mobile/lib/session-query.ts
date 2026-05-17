import { useQuery } from "@tanstack/react-query";
import { getStoredSession } from "./auth-store";

export function useStoredSession() {
  return useQuery({
    queryKey: ["auth", "session"],
    queryFn: getStoredSession
  });
}
