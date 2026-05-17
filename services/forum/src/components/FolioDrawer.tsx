/** Spec/09 §6.8 — Folio drawer. Right-side Radix Sheet that opens
 * whenever a domain entity is clicked. Three vertical bands:
 *   1. Identity
 *   2. Live transcript (where it applies)
 *   3. Neighbours — clickable cross-references
 *
 * Every entity kind has a folio shape; the renderer matches on
 * `ref.kind` and queries the appropriate observer endpoint(s). */

import * as Dialog from "@radix-ui/react-dialog";
import { Cross1Icon, ChevronLeftIcon } from "@radix-ui/react-icons";
import useSWR from "swr";
import {
  fetcher,
  type Pod,
  type Proclamation,
  type Proposal,
  type Decision,
  type Council,
  type CouncilMessage,
  type EndpointRow,
} from "../api";
import { useFolio, type EntityRef } from "../folio";
import { Markdown } from "./Markdown";
import { Linkified } from "./Linkified";
import { Phylactery } from "./Phylactery";
import { Plate } from "./Plate";
import { ProposalCartouche } from "./ProposalCartouche";
import { EntityLink } from "./EntityLink";
import { C, monogram, toRoman } from "../theme";

export function FolioDrawer() {
  const { stack, pop, clear } = useFolio();
  const top = stack[stack.length - 1] ?? null;
  const open = top !== null;
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o) clear();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(31,26,20,0.35)",
            zIndex: 40,
          }}
        />
        <Dialog.Content
          aria-describedby={undefined}
          style={{
            position: "fixed",
            right: 0,
            top: 0,
            height: "100vh",
            width: 520,
            maxWidth: "90vw",
            background: C.vellum,
            borderLeft: `0.5px solid ${C.ink}`,
            zIndex: 50,
            overflowY: "auto",
            color: C.ink,
            fontFamily: "var(--f-body)",
          }}
        >
          <header
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 16px",
              borderBottom: `0.5px solid ${C.inkFaded}`,
              background: C.parchment,
              position: "sticky",
              top: 0,
            }}
          >
            {stack.length > 1 ? (
              <button
                type="button"
                onClick={pop}
                aria-label="back"
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  display: "inline-flex",
                }}
              >
                <ChevronLeftIcon />
              </button>
            ) : null}
            <Dialog.Title asChild>
              <h2
                className="c-display"
                style={{
                  margin: 0,
                  fontSize: 13,
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {top ? renderTitle(top) : "—"}
              </h2>
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="close"
                style={{
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  display: "inline-flex",
                }}
              >
                <Cross1Icon />
              </button>
            </Dialog.Close>
          </header>
          <div style={{ padding: 16 }}>
            {top ? <FolioBody ref={top} /> : null}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function renderTitle(ref: EntityRef): string {
  const label = ref.label ?? ref.id;
  switch (ref.kind) {
    case "pod":
      return `Pod ${label}`;
    case "proclamation":
      return `Proclamation ${label}`;
    case "decision":
      return `Decision ${label}`;
    case "proposal":
      return `Proposal ${label}`;
    case "council":
      return `Council ${label}`;
    case "endpoint":
      return `Endpoint ${label}`;
    case "app":
      return `App ${label}`;
  }
}

function FolioBody({ ref }: { ref: EntityRef }) {
  switch (ref.kind) {
    case "pod":
      return <PodFolio podId={ref.id} />;
    case "proclamation":
      return <ProclamationFolio seq={ref.id} />;
    case "decision":
      return <DecisionFolio decisionId={ref.id} />;
    case "proposal":
      return <ProposalFolio proposalId={ref.id} />;
    case "council":
      return <CouncilFolio councilId={ref.id} />;
    case "endpoint":
      return <EndpointFolio compositeId={ref.id} />;
    case "app":
      return <PodFolio podId={ref.id} />;
  }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ margin: "12px 0" }}>
      <h3
        className="c-display-sm c-faded"
        style={{ margin: "0 0 6px 0", letterSpacing: "0.12em" }}
      >
        {title}
      </h3>
      {children}
    </section>
  );
}

function PodFolio({ podId }: { podId: string }) {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher);
  const { data: charter } = useSWR<{ body: string } | { detail: string }>(
    `/state/pods/${podId}/charter`,
    fetcher,
  );
  const { data: endpoints } = useSWR<EndpointRow[]>("/state/endpoints", fetcher);
  const { data: turns } = useSWR<
    Array<{ pod_id: string; turn_id: string; started_at: string; ended_at: string | null; tokens_in: number | null; tokens_out: number | null }>
  >(`/state/pods/${podId}/turns`, fetcher);

  const pod = pods?.find((p) => p.pod_id === podId);
  if (!pod) return <p className="c-faded">Pod not found.</p>;
  const podEndpoints = (endpoints ?? []).filter((e) => e.pod_id === podId);

  return (
    <>
      <Section title="Identity">
        <p style={{ margin: 0 }}>
          <strong className="c-display">{pod.display_role}</strong>
        </p>
        <p className="c-mono c-faded" style={{ margin: 0 }}>
          {pod.pod_id}
        </p>
        <p style={{ margin: "4px 0", fontSize: 13 }}>
          runtime <span className="c-rubric">{pod.runtime_status}</span> · agent{" "}
          <span className="c-rubric">{pod.agent_state}</span>
          {pod.admitted ? " · admitted" : " · placeholder"}
        </p>
      </Section>
      {charter && "body" in charter ? (
        <Section title="Charter">
          <Markdown body={charter.body} />
        </Section>
      ) : null}
      {turns && turns.length > 0 ? (
        <Section title="Thinking">
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {turns.slice(0, 12).map((t) => (
              <li
                key={t.turn_id}
                className="c-mono"
                style={{ padding: "2px 0", fontSize: 12 }}
              >
                <span className="c-faded">{formatHHMM(t.started_at)}</span>{" "}
                turn {t.turn_id.slice(0, 8)}{" "}
                {t.tokens_in != null ? (
                  <>
                    <span className="c-faded">·</span> {t.tokens_in}/{t.tokens_out} tok
                  </>
                ) : (
                  <span className="c-faded">…</span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      {podEndpoints.length > 0 ? (
        <Section title="Endpoints">
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {podEndpoints.map((e) => (
              <li key={`${e.method}|${e.path}`} className="c-mono" style={{ fontSize: 12 }}>
                <EntityLink
                  kind="endpoint"
                  id={`${e.pod_id}|${e.method}|${e.path}`}
                  label={`${e.method} ${e.path}`}
                >
                  <span>
                    {e.method} {e.path}
                  </span>
                </EntityLink>
                {e.annotation ? (
                  <span className="c-faded" style={{ marginLeft: 8 }}>
                    — {e.annotation}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      {pod.public_url ? (
        <Section title="Public URL">
          <a
            className="c-link c-mono"
            href={pod.public_url}
            target="_blank"
            rel="noreferrer"
          >
            {pod.public_url}
          </a>
        </Section>
      ) : null}
    </>
  );
}

function ProclamationFolio({ seq }: { seq: string }) {
  const { data } = useSWR<Proclamation[]>("/state/proclamations", fetcher);
  const proc = data?.find((p) => String(p.seq) === seq);
  if (!proc) return <p className="c-faded">Proclamation not found.</p>;
  return (
    <>
      <Section title="Numeral">
        <span className="c-numeral c-gold">№ {toRoman(proc.seq)}</span>
        <span className="c-faded" style={{ marginLeft: 8, fontSize: 12 }}>
          {formatHHMM(proc.issued_at)}
        </span>
      </Section>
      <Section title="Body">
        {/* Spec/09 §3: the drop cap appears only in Witness. In the
         * folio drawer the proclamation body renders without it so
         * the "one place in the app" rule stays honest. */}
        <p style={{ fontSize: 16, lineHeight: 1.5, margin: 0 }}>
          <Linkified text={proc.text} />
        </p>
      </Section>
      {proc.placeholder_decision_id ? (
        <Section title="Architecture">
          <EntityLink kind="decision" id={proc.placeholder_decision_id}>
            {proc.placeholder_decision_id}
          </EntityLink>
        </Section>
      ) : null}
      {proc.summary ? (
        <Section title="Concluded">
          <Markdown body={proc.summary} />
        </Section>
      ) : null}
    </>
  );
}

function DecisionFolio({ decisionId }: { decisionId: string }) {
  const { data } = useSWR<Decision[]>("/state/decisions", fetcher);
  const d = data?.find((r) => r.decision_id === decisionId);
  if (!d) return <p className="c-faded">Decision not found.</p>;
  return (
    <Plate
      decisionId={d.decision_id}
      title={d.title}
      body={d.body}
      affected={d.affected}
      status={d.status}
      sealedAt={d.sealed_at}
    />
  );
}

function ProposalFolio({ proposalId }: { proposalId: string }) {
  const { data } = useSWR<Proposal[]>("/state/proposals", fetcher);
  const p = data?.find((r) => r.proposal_id === proposalId);
  if (!p) return <p className="c-faded">Proposal not found.</p>;
  return <ProposalCartouche proposal={p} />;
}

function CouncilFolio({ councilId }: { councilId: string }) {
  const { data: councils } = useSWR<Council[]>("/state/councils", fetcher);
  const { data: msgs } = useSWR<CouncilMessage[]>(
    `/state/councils/${councilId}/messages`,
    fetcher,
    { refreshInterval: 4000 },
  );
  const c = councils?.find((r) => r.council_id === councilId);
  if (!c) return <p className="c-faded">Council not found.</p>;
  return (
    <>
      <Section title="Topic">
        <p style={{ margin: 0, fontSize: 15 }}>
          <Linkified text={c.topic} />
        </p>
        {c.needs_augustus ? (
          <div
            className="c-display-sm c-gold"
            style={{ marginTop: 4, fontSize: 11 }}
          >
            ◆ needs Augustus
          </div>
        ) : null}
      </Section>
      <Section title="Participants">
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {c.participants.map((podId) => (
            <EntityLink key={podId} kind="pod" id={podId}>
              <span
                className="c-mono"
                style={{
                  padding: "2px 8px",
                  background: C.parchment,
                  border: `0.5px solid ${C.inkFaded}`,
                  fontSize: 11,
                }}
              >
                {monogram(podId)} {podId.slice(0, 12)}
              </span>
            </EntityLink>
          ))}
        </div>
      </Section>
      <Section title="Thread">
        {msgs?.length ? (
          msgs.map((m) => (
            <Phylactery
              key={m.seq}
              sender={m.from_pod}
              body={m.body}
              sentAt={m.sent_at}
            />
          ))
        ) : (
          <p className="c-faded" style={{ fontStyle: "italic" }}>
            no minutes yet
          </p>
        )}
      </Section>
      {c.summary && c.decision_id ? (
        <Section title="Sealed">
          <EntityLink kind="decision" id={c.decision_id}>
            {c.decision_id}
          </EntityLink>
          <p style={{ marginTop: 6 }}>{c.summary}</p>
        </Section>
      ) : null}
    </>
  );
}

function EndpointFolio({ compositeId }: { compositeId: string }) {
  const [podId, method, path] = compositeId.split("|");
  const { data: endpoints } = useSWR<EndpointRow[]>("/state/endpoints", fetcher);
  const ep = endpoints?.find(
    (e) => e.pod_id === podId && e.method === method && e.path === path,
  );
  if (!ep) return <p className="c-faded">Endpoint not found.</p>;
  return (
    <>
      <Section title="Endpoint">
        <p className="c-mono" style={{ margin: 0, fontSize: 14 }}>
          {ep.method} {ep.path}
        </p>
        <p style={{ margin: 0, fontSize: 12 }}>
          on{" "}
          <EntityLink kind="pod" id={ep.pod_id}>
            {ep.pod_id}
          </EntityLink>
        </p>
      </Section>
      {ep.annotation ? (
        <Section title="Annotation">
          <Markdown body={ep.annotation} />
        </Section>
      ) : (
        <Section title="Annotation">
          <p className="c-faded" style={{ fontStyle: "italic" }}>
            no annotation yet
          </p>
        </Section>
      )}
      <Section title="Observed">
        <p className="c-mono c-faded" style={{ fontSize: 11 }}>
          first seen {formatHHMM(ep.first_seen)} · last seen{" "}
          {formatHHMM(ep.last_seen)}
        </p>
      </Section>
    </>
  );
}

function formatHHMM(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
