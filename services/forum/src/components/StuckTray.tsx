/** Spec/09 §6.12 — Stuck Tray. Bottom-left fold-out on Glance.
 * The only component allowed to use cinnabar as a fill. Verb-buttons
 * in Cinzel small-caps. Each row is one stuck thing with one tap. */

import { useState } from "react";
import { postCommand, type Pod } from "../api";
import { EntityLink } from "../components/EntityLink";
import { C, monogram } from "../theme";

interface Props {
  pods: Pod[];
  /** Render full-page (true) — used by /inbox — or as a collapsed
   * fold-out (false) — used by Glance. */
  fullPage?: boolean;
}

export function StuckTray({ pods, fullPage }: Props) {
  const [open, setOpen] = useState(fullPage ?? false);
  const stuck = pods.filter(
    (p) => p.agent_state === "stuck" || p.runtime_status === "stopped",
  );
  if (stuck.length === 0 && !fullPage) return null;

  const body = (
    <div
      style={{
        background: fullPage ? "transparent" : C.cinnabar,
        color: fullPage ? C.ink : C.parchment,
        padding: fullPage ? "0" : "8px 12px",
        fontFamily: "var(--f-body)",
        fontSize: "var(--t-body)",
      }}
    >
      {!fullPage ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 6,
          }}
        >
          <span className="c-display-sm">{stuck.length} STUCK</span>
        </div>
      ) : null}
      {stuck.length === 0 ? (
        <div className="c-faded" style={{ fontStyle: "italic" }}>
          nothing is stuck
        </div>
      ) : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {stuck.map((p) => (
            <li
              key={p.pod_id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                margin: "4px 0",
              }}
            >
              <EntityLink kind="pod" id={p.pod_id} label={p.display_role}>
                <span
                  style={{
                    background: fullPage ? C.cinnabar : C.parchment,
                    color: fullPage ? C.parchment : C.cinnabar,
                    padding: "2px 8px",
                    borderRadius: 2,
                    fontFamily: "var(--f-display)",
                    fontSize: 11,
                  }}
                >
                  {monogram(p.display_role || p.pod_id)} {p.display_role || p.pod_id}
                </span>
              </EntityLink>
              <span style={{ fontSize: 13 }}>
                {p.agent_state === "stuck" ? "agent stuck" : "container stopped"}
              </span>
              <RestartButton podId={p.pod_id} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  if (fullPage) return body;

  return (
    <div
      style={{
        position: "fixed",
        left: 16,
        bottom: 16,
        background: C.cinnabar,
        color: C.parchment,
        padding: open ? "8px 12px" : "6px 10px",
        borderRadius: 2,
        boxShadow: `0 2px 6px rgba(0,0,0,0.3)`,
        maxWidth: 360,
        cursor: open ? "default" : "pointer",
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      role="region"
      aria-label="stuck things"
    >
      {open ? body : <span className="c-display-sm">{stuck.length} STUCK</span>}
    </div>
  );
}

function RestartButton({ podId }: { podId: string }) {
  const [pending, setPending] = useState(false);
  return (
    <button
      type="button"
      disabled={pending}
      onClick={async () => {
        setPending(true);
        try {
          await postCommand({ kind: "RestartPod", pod_id: podId });
        } finally {
          setPending(false);
        }
      }}
      style={{
        background: "transparent",
        color: "inherit",
        border: `1px solid currentColor`,
        padding: "2px 8px",
        cursor: "pointer",
        fontFamily: "var(--f-display)",
        fontSize: 10,
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        marginLeft: "auto",
      }}
    >
      {pending ? "…" : "RESTART"}
    </button>
  );
}
