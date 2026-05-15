import { useState } from "react";

type Runtime = "compose" | "k3d" | "byo-k8s";
type Bus = "nats" | "redis";
type Repo = "github" | "gitlab";
type Doc = "gh-issues" | "obsidian";
type Trace = "otel-tempo" | "linkerd";
type Logs = "stdout" | "loki";
type Notify = "email" | "telegram";

type WizardState = {
  runtime: Runtime;
  bus: Bus;
  repo: Repo;
  doc: Doc;
  trace: Trace;
  logs: Logs;
  notify: Notify;
  anthropicKey: string;
  repoToken: string;
};

const DEFAULTS: WizardState = {
  runtime: "compose",
  bus: "nats",
  repo: "github",
  doc: "obsidian",
  trace: "otel-tempo",
  logs: "stdout",
  notify: "email",
  anthropicKey: "",
  repoToken: "",
};

function renderYaml(s: WizardState): string {
  return [
    "conclave:",
    "  version: 0.1",
    `  runtime: ${s.runtime}`,
    "  slots:",
    `    bus: ${s.bus}`,
    `    repo: ${s.repo}`,
    `    doc: ${s.doc}`,
    `    trace: ${s.trace}`,
    `    logs: ${s.logs}`,
    `    notify: ${s.notify}`,
    "  credentials:",
    `    anthropic_api_key: ${s.anthropicKey ? "<set>" : "<missing>"}`,
    `    repo_token: ${s.repoToken ? "<set>" : "<missing>"}`,
  ].join("\n");
}

export function Wizard() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [state, setState] = useState<WizardState>(DEFAULTS);
  const [saved, setSaved] = useState<string | null>(null);

  function update<K extends keyof WizardState>(key: K, value: WizardState[K]) {
    setState((prev) => ({ ...prev, [key]: value }));
  }

  function handleSave() {
    const yaml = renderYaml(state);
    console.log("wizard-save", { state, yaml });
    setSaved(yaml);
  }

  return (
    <section>
      <h2>Wizard</h2>
      <p>Bootstrap configuration for this Conclave. Step {step} of 3.</p>

      {step === 1 ? (
        <fieldset style={{ border: "1px solid var(--stone)", padding: "1rem" }}>
          <legend>Step 1 — Where will this run?</legend>
          {(["compose", "k3d", "byo-k8s"] as Runtime[]).map((r) => (
            <label key={r} style={{ display: "block", marginBottom: "0.5rem" }}>
              <input
                type="radio"
                name="runtime"
                value={r}
                checked={state.runtime === r}
                onChange={() => update("runtime", r)}
              />{" "}
              {r}
            </label>
          ))}
        </fieldset>
      ) : null}

      {step === 2 ? (
        <fieldset style={{ border: "1px solid var(--stone)", padding: "1rem" }}>
          <legend>Step 2 — Pick your stack</legend>
          <Row label="Bus">
            <select
              value={state.bus}
              onChange={(e) => update("bus", e.target.value as Bus)}
            >
              <option value="nats">NATS</option>
              <option value="redis">Redis Streams</option>
            </select>
          </Row>
          <Row label="Repo host">
            <select
              value={state.repo}
              onChange={(e) => update("repo", e.target.value as Repo)}
            >
              <option value="github">GitHub</option>
              <option value="gitlab">GitLab</option>
            </select>
          </Row>
          <Row label="Doc backend">
            <select
              value={state.doc}
              onChange={(e) => update("doc", e.target.value as Doc)}
            >
              <option value="gh-issues">GH Issues</option>
              <option value="obsidian">Obsidian vault</option>
            </select>
          </Row>
          <Row label="Traces">
            <select
              value={state.trace}
              onChange={(e) => update("trace", e.target.value as Trace)}
            >
              <option value="otel-tempo">OTel + Tempo</option>
              <option value="linkerd">Linkerd</option>
            </select>
          </Row>
          <Row label="Logs">
            <select
              value={state.logs}
              onChange={(e) => update("logs", e.target.value as Logs)}
            >
              <option value="stdout">stdout</option>
              <option value="loki">Loki + Grafana</option>
            </select>
          </Row>
          <Row label="Notifications">
            <select
              value={state.notify}
              onChange={(e) => update("notify", e.target.value as Notify)}
            >
              <option value="email">Email</option>
              <option value="telegram">Telegram</option>
            </select>
          </Row>
        </fieldset>
      ) : null}

      {step === 3 ? (
        <fieldset style={{ border: "1px solid var(--stone)", padding: "1rem" }}>
          <legend>Step 3 — Credentials</legend>
          <Row label="Anthropic API key">
            <input
              type="password"
              value={state.anthropicKey}
              onChange={(e) => update("anthropicKey", e.target.value)}
            />
          </Row>
          <Row label="Repo token">
            <input
              type="password"
              value={state.repoToken}
              onChange={(e) => update("repoToken", e.target.value)}
            />
          </Row>
        </fieldset>
      ) : null}

      <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
        <button
          type="button"
          disabled={step === 1}
          onClick={() => setStep((s) => (s - 1) as 1 | 2 | 3)}
        >
          Back
        </button>
        {step < 3 ? (
          <button
            type="button"
            onClick={() => setStep((s) => (s + 1) as 1 | 2 | 3)}
          >
            Next
          </button>
        ) : (
          <button type="button" onClick={handleSave}>
            Launch
          </button>
        )}
      </div>

      {saved ? (
        <div style={{ marginTop: "1.5rem" }}>
          <h3>conclave.config.yaml (preview)</h3>
          <pre
            style={{
              background: "var(--ink)",
              color: "var(--marble)",
              padding: "1rem",
              fontFamily: '"JetBrains Mono", monospace',
              overflow: "auto",
            }}
          >
            {saved}
          </pre>
          <p style={{ color: "var(--stone)" }}>
            Would POST to <code>/api/wizard/save</code> — backend not wired yet.
          </p>
        </div>
      ) : null}
    </section>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label
      style={{
        display: "grid",
        gridTemplateColumns: "160px 1fr",
        gap: "0.5rem",
        marginBottom: "0.5rem",
        alignItems: "center",
      }}
    >
      <span>{label}</span>
      {children}
    </label>
  );
}
