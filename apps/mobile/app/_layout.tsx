import { Stack } from "expo-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { TamaguiProvider } from "tamagui";

import config from "../tamagui.config";
import { queryClient } from "../lib/query-client";

export default function RootLayout() {
  return (
    <TamaguiProvider config={config} defaultTheme="light">
      <QueryClientProvider client={queryClient}>
        <Stack screenOptions={{ headerShown: false }} />
      </QueryClientProvider>
    </TamaguiProvider>
  );
}
