import { StoneTablet } from "../components/StoneTablet";

const PLACEHOLDER_ADRS = [
  {
    id: "adr-0001",
    title: "Founding mandate",
    date: "2026-05-01",
    pods: ["alice"],
    body: "Placeholder ADR. The decisions MCP and doc backend are not yet wired into the UI.",
  },
  {
    id: "adr-0002",
    title: "Adopt NATS as bus",
    date: "2026-05-02",
    pods: ["alice", "bob"],
    body: "Placeholder ADR — once decisions.list is available the Tabularium will mirror it.",
  },
];

export function Tabularium() {
  return (
    <section>
      <h2>Tabularium</h2>
      <p>
        Archive of ADRs (Architecture Decision Records). Placeholder until the
        decisions MCP exposes a list endpoint.
      </p>
      {PLACEHOLDER_ADRS.map((adr) => (
        <StoneTablet
          key={adr.id}
          title={`${adr.id} — ${adr.title}`}
          meta={`${adr.date} · ${adr.pods.join(", ")}`}
        >
          <p>{adr.body}</p>
        </StoneTablet>
      ))}
    </section>
  );
}
