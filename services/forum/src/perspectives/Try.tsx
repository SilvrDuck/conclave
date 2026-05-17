/** Spec/09 §4 — Try perspective. A grid of Plaques, one per pod
 * with a public HTTP service. Three columns on wide screens, one
 * on narrow. No screenshots, no thumbnails — the plaque IS the
 * affordance. Clicking the plaque body opens the pod folio (for
 * endpoint navigation); the O wax seal opens the deployed app. */

import useSWR from "swr";
import { fetcher, type Pod, type EndpointRow } from "../api";
import { WaxSeal } from "../components/WaxSeal";
import { useFolio } from "../folio";
import { C } from "../theme";

export function Try() {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher, {
    refreshInterval: 5000,
  });
  const { data: endpoints } = useSWR<EndpointRow[]>("/state/endpoints", fetcher, {
    refreshInterval: 5000,
  });

  const launchable = (pods ?? []).filter(
    (p) => p.public_url && p.admitted,
  );

  if (launchable.length === 0) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        <p
          className="c-faded"
          style={{ fontStyle: "italic", textAlign: "center" }}
        >
          no apps have been deployed yet. wait for the swarm to ship.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: 24,
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
        gap: 16,
      }}
    >
      {launchable.map((pod) => (
        <Plaque
          key={pod.pod_id}
          pod={pod}
          endpoints={(endpoints ?? []).filter((e) => e.pod_id === pod.pod_id)}
        />
      ))}
    </div>
  );
}

function Plaque({
  pod,
  endpoints,
}: {
  pod: Pod;
  endpoints: EndpointRow[];
}) {
  const folio = useFolio();
  return (
    <article
      style={{
        background: C.vellum,
        border: `0.5px solid ${C.inkFaded}`,
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        minHeight: 160,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <button
          type="button"
          onClick={() => folio.open({ kind: "pod", id: pod.pod_id })}
          className="c-display"
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            cursor: "pointer",
            fontSize: 13,
            color: C.ink,
          }}
        >
          {pod.display_role}
        </button>
        <span className="c-mono c-faded" style={{ fontSize: 11 }}>
          {pod.image_strategy === "adopted" ? "adopted" : "code"}
        </span>
      </div>
      <a
        className="c-link c-mono"
        href={pod.public_url ?? "#"}
        target="_blank"
        rel="noreferrer"
        style={{ fontSize: 12 }}
      >
        {pod.public_url ? new URL(pod.public_url).host : "—"}
      </a>
      <EndpointSparkline endpoints={endpoints} />
      <div style={{ marginTop: "auto", display: "flex", justifyContent: "flex-end" }}>
        {pod.public_url ? (
          <WaxSeal
            letter="O"
            label="Open app"
            size={28}
            onClick={() => window.open(pod.public_url!, "_blank")}
          />
        ) : null}
      </div>
    </article>
  );
}

function EndpointSparkline({ endpoints }: { endpoints: EndpointRow[] }) {
  // Endpoint freshness as a discrete sparkline: most-recently-seen
  // first, faded the older they get. A real RPM sparkline needs a
  // time-series read; this is the right §9-compliant placeholder.
  const sorted = [...endpoints].sort(
    (a, b) => new Date(b.last_seen).getTime() - new Date(a.last_seen).getTime(),
  );
  if (sorted.length === 0) {
    return (
      <p className="c-faded" style={{ fontSize: 12, fontStyle: "italic", margin: 0 }}>
        no endpoints observed yet.
      </p>
    );
  }
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0, fontSize: 12 }}>
      {sorted.slice(0, 5).map((e) => (
        <li key={`${e.method}|${e.path}`} className="c-mono">
          <span>
            {e.method} {e.path}
          </span>
          {e.annotation ? (
            <span className="c-faded" style={{ marginLeft: 6 }}>
              — {e.annotation}
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
