import { ReactNode } from "react";
import { ApiProblem } from "../lib/api";

export type OpsSurfaceState = "ready" | "loading" | "empty" | "error" | "offline" | "forbidden";

export type OpsStateSurfaceProps = {
  testIDPrefix: string;
  title: string;
  subtitle: string;
  state: OpsSurfaceState;
  children?: ReactNode;
  onRetry?: () => void;
};

const stateCopy: Record<Exclude<OpsSurfaceState, "ready">, string> = {
  loading: "Loading operational data",
  empty: "No matching records yet",
  error: "Unable to load this workflow",
  offline: "API is unreachable from this browser",
  forbidden: "Ops role or token is required"
};

export function deriveOpsState(input: {
  enabled: boolean;
  loading?: boolean;
  error?: unknown;
  empty?: boolean;
}): OpsSurfaceState {
  if (!input.enabled) {
    return "forbidden";
  }
  if (input.loading) {
    return "loading";
  }
  if (input.error instanceof ApiProblem && [401, 403].includes(input.error.status)) {
    return "forbidden";
  }
  if (input.error instanceof TypeError) {
    return "offline";
  }
  if (input.error) {
    return "error";
  }
  if (input.empty) {
    return "empty";
  }
  return "ready";
}

export function OpsStateSurface({ testIDPrefix, title, subtitle, state, children, onRetry }: OpsStateSurfaceProps) {
  return (
    <section className="ops-route" data-testid={`${testIDPrefix}-screen`}>
      <div className="route-heading">
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <button data-testid={`${testIDPrefix}-retry`} type="button" onClick={onRetry}>
          Retry
        </button>
      </div>

      {state !== "ready" ? (
        <div className={`state-banner ${state}`} data-testid={`${testIDPrefix}-${state}`}>
          {stateCopy[state]}
        </div>
      ) : null}

      <div className="state-contract" aria-hidden="true">
        {(["loading", "empty", "error", "offline", "forbidden"] as const).map((item) => (
          <span key={item} data-testid={`${testIDPrefix}-state-contract-${item}`} />
        ))}
      </div>

      {state === "ready" ? children : null}
    </section>
  );
}

export function OpsTable({ children, headers }: { headers: string[]; children: ReactNode }) {
  return (
    <table className="ops-table">
      <thead>
        <tr>
          {headers.map((header) => (
            <th key={header}>{header}</th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  );
}
