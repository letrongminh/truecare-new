import type { ComponentType } from "react";
import { AdmissionsRoute } from "../routes/admissions";
import { AuditLogRoute } from "../routes/audit-log";
import { CommissionRoute } from "../routes/commission";
import { ComplaintsRoute } from "../routes/complaints";
import { GrowthEkycRoute } from "../routes/growth-ekyc";
import { NetworkHealthRoute } from "../routes/network-health";

export type OpsRouteProps = {
  token: string;
  canUseApi: boolean;
};

export type OpsRouteDefinition = {
  id: string;
  label: string;
  testIDPrefix: string;
  Component: ComponentType<OpsRouteProps>;
};

export const opsRoutes: OpsRouteDefinition[] = [
  {
    id: "admissions",
    label: "Admissions",
    testIDPrefix: "ops-admissions",
    Component: AdmissionsRoute
  },
  {
    id: "commission",
    label: "Commission",
    testIDPrefix: "ops-commission",
    Component: CommissionRoute
  },
  {
    id: "complaints",
    label: "Complaints",
    testIDPrefix: "ops-complaints",
    Component: ComplaintsRoute
  },
  {
    id: "network-health",
    label: "Network health",
    testIDPrefix: "ops-network-health",
    Component: NetworkHealthRoute
  },
  {
    id: "growth-ekyc",
    label: "Growth/eKYC",
    testIDPrefix: "ops-growth-ekyc",
    Component: GrowthEkycRoute
  },
  {
    id: "audit-log",
    label: "Audit log",
    testIDPrefix: "ops-audit-log",
    Component: AuditLogRoute
  }
];

export function routeFromHash(hash: string) {
  const id = hash.replace(/^#\/?/, "") || "admissions";
  return opsRoutes.find((route) => route.id === id) || opsRoutes[0];
}
