/** Spec/09 §6.11 — Charter Editor. Pod chooser strip (a horizontal
 * row of Pod Cartouches), serif diff view of the current charter
 * versus a working draft, and a single S wax seal at the foot to
 * commit via POST /commands {kind: EditCharter}. */

import { useEffect, useState } from "react";
import useSWR from "swr";
import { fetcher, postCommand, type Pod } from "../api";
import { PodCartouche } from "./PodCartouche";
import { WaxSeal } from "./WaxSeal";
import { C } from "../theme";

interface Props {
  selectedPodId: string | null;
  onSelect: (podId: string) => void;
}

export function CharterEditor({ selectedPodId, onSelect }: Props) {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher, {
    refreshInterval: 5000,
  });
  const { data: charter } = useSWR<{ body: string } | { detail: string }>(
    selectedPodId ? `/state/pods/${selectedPodId}/charter` : null,
    fetcher,
  );
  const original = charter && "body" in charter ? charter.body : "";
  const [draft, setDraft] = useState<string>(original);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    setDraft(original);
  }, [original]);

  const dirty = draft !== original;

  return (
    <section
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        padding: 16,
      }}
    >
      <header>
        <h2 className="c-display" style={{ margin: 0, fontSize: 13 }}>
          Charter
        </h2>
      </header>

      {/* Pod chooser strip */}
      <div
        style={{
          display: "flex",
          gap: 8,
          overflowX: "auto",
          paddingBottom: 4,
        }}
      >
        {(pods ?? []).map((p) => (
          <button
            type="button"
            key={p.pod_id}
            onClick={() => onSelect(p.pod_id)}
            style={{
              background: selectedPodId === p.pod_id ? C.gold : "transparent",
              padding: 2,
              border: "none",
              cursor: "pointer",
            }}
            aria-current={selectedPodId === p.pod_id ? "true" : "false"}
          >
            <PodCartouche pod={p} compact />
          </button>
        ))}
      </div>

      {selectedPodId ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {/* Original (faded) */}
          <div>
            <div className="c-display-sm c-faded" style={{ marginBottom: 4 }}>
              Original
            </div>
            <pre
              style={{
                margin: 0,
                background: C.parchment,
                color: C.inkFaded,
                padding: 12,
                fontFamily: "var(--f-body)",
                fontSize: "var(--t-charter)",
                lineHeight: 1.5,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                border: `0.5px solid ${C.inkFaded}`,
                minHeight: 300,
              }}
            >
              {original || "_no charter yet_"}
            </pre>
          </div>
          {/* Draft */}
          <div>
            <div className="c-display-sm" style={{ marginBottom: 4 }}>
              Edit
            </div>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              style={{
                width: "100%",
                minHeight: 300,
                background: C.vellum,
                color: C.ink,
                padding: 12,
                fontFamily: "var(--f-body)",
                fontSize: "var(--t-charter)",
                lineHeight: 1.5,
                border: `0.5px solid ${dirty ? C.ink : C.inkFaded}`,
                resize: "vertical",
              }}
            />
          </div>
        </div>
      ) : (
        <p
          className="c-faded"
          style={{ fontStyle: "italic", marginTop: 24 }}
        >
          select a pod above to edit its charter.
        </p>
      )}

      {selectedPodId && dirty ? (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <WaxSeal
            letter="S"
            label="Seal edit"
            disabled={pending}
            onClick={async () => {
              setPending(true);
              try {
                await postCommand({
                  kind: "EditCharter",
                  pod_id: selectedPodId,
                  body: draft,
                });
              } finally {
                setPending(false);
              }
            }}
          />
        </div>
      ) : null}
    </section>
  );
}
