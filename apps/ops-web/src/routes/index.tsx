import { FormEvent, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiBaseUrl } from "../lib/api";
import { getCurrentPrincipal, hasOpsRole, readOpsToken, saveOpsToken } from "../lib/auth";
import { opsRoutes, routeFromHash } from "../lib/routes";

function useCurrentRoute() {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const listener = () => setHash(window.location.hash);
    window.addEventListener("hashchange", listener);
    return () => window.removeEventListener("hashchange", listener);
  }, []);

  return useMemo(() => routeFromHash(hash), [hash]);
}

export function OpsShell() {
  const currentRoute = useCurrentRoute();
  const [tokenInput, setTokenInput] = useState(readOpsToken);
  const [savedToken, setSavedToken] = useState(readOpsToken);
  const principal = useQuery({
    queryKey: ["ops-principal", savedToken],
    enabled: Boolean(savedToken),
    queryFn: () => getCurrentPrincipal(savedToken)
  });
  const canUseApi = Boolean(savedToken && principal.data && hasOpsRole(principal.data));
  const RouteComponent = currentRoute.Component;

  function saveToken(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveOpsToken(tokenInput);
    setSavedToken(tokenInput.trim());
  }

  function clearToken() {
    saveOpsToken("");
    setTokenInput("");
    setSavedToken("");
  }

  return (
    <main className="ops-shell" data-testid="ops-shell">
      <header className="topbar">
        <span>TrueCare Ops</span>
        <strong>{apiBaseUrl}</strong>
      </header>

      <div className="ops-layout">
        <aside className="sidebar" aria-label="Ops navigation">
          <form className="token-panel" onSubmit={saveToken}>
            <label htmlFor="ops-token">Ops access token</label>
            <textarea
              id="ops-token"
              data-testid="ops-token-input"
              value={tokenInput}
              onChange={(event) => setTokenInput(event.target.value)}
              placeholder="Paste bearer token from /v1/auth/login"
              rows={4}
            />
            <div className="button-row">
              <button type="submit" data-testid="ops-token-save">
                Save
              </button>
              <button type="button" data-testid="ops-token-clear" onClick={clearToken}>
                Clear
              </button>
            </div>
            <p data-testid="ops-auth-status">
              {principal.isLoading
                ? "Checking token"
                : canUseApi
                  ? `Ops role: ${principal.data?.roles.join(", ")}`
                  : savedToken
                    ? "Token is missing an ops role"
                    : "No token saved"}
            </p>
          </form>

          <nav>
            {opsRoutes.map((route) => (
              <a
                key={route.id}
                className={route.id === currentRoute.id ? "active" : ""}
                data-testid={`${route.testIDPrefix}-nav`}
                href={`#/${route.id}`}
              >
                {route.label}
              </a>
            ))}
          </nav>
        </aside>

        <RouteComponent token={savedToken} canUseApi={canUseApi} />
      </div>
    </main>
  );
}
