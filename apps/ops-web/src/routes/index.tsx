export function OpsShell() {
  return (
    <main className="ops-shell" data-testid="ops-shell">
      <header>
        <span>TrueCare Ops</span>
        <strong>Local</strong>
      </header>
      <section>
        <h1>Operations</h1>
        <div className="metrics" aria-label="Operations overview">
          <span>Admissions 0</span>
          <span>Complaints 0</span>
          <span>Commission 0 VND</span>
          <span>Stale merchants 0</span>
        </div>
      </section>
    </main>
  );
}
