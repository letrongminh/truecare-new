import React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { queryClient } from "./lib/query-client";
import { OpsShell } from "./routes";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <OpsShell />
    </QueryClientProvider>
  </React.StrictMode>
);
