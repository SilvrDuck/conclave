/** Spec/09 §6.2 — Pod Cartouche.
 *
 * The pod node on the Glance graph AND the inline pod-reference chip.
 * Oval parchment frame, display-role in Cinzel small-caps, 12px state
 * pip, optional 24×6 endpoint-traffic sparkline (graph form only).
 *
 * Pip colour:
 *   verdigris — running + idle/thinking
 *   cinnabar  — agent_state stuck (with 1.5Hz pulse)
 *   wash      — not_yet_spawned
 *   faded ink — stopped (container exited)
 * Outline:
 *   dashed    — placeholder pod
 *   solid     — admitted pod
 *   crossed   — exiled
 * The simulator pod has gold hairlines above and below. */

import type { Pod } from "../api";
import { C, monogram, podHue } from "../theme";

interface Props {
  pod: Pod;
  /** Sparkline values (RPM-ish), 0..1 normalised. Optional. */
  sparkline?: number[];
  /** Show the gold hairline above/below (used for the simulator pod). */
  simulator?: boolean;
  /** Compact mode for inline references — no sparkline, no pip-label. */
  compact?: boolean;
}

function pipColor(pod: Pod): string {
  if (pod.agent_state === "stuck") return C.cinnabar;
  if (pod.runtime_status === "not_yet_spawned") return C.wash;
  if (pod.runtime_status === "stopped") return C.inkFaded;
  return C.verdigris;
}

export function PodCartouche({ pod, sparkline, simulator, compact }: Props) {
  const pip = pipColor(pod);
  const pulsing = pod.agent_state === "stuck";
  const isPlaceholder = !pod.admitted;
  const borderStyle = isPlaceholder ? "dashed" : "solid";
  const role = pod.display_role || pod.pod_id;

  return (
    <div
      style={{
        position: "relative",
        background: C.vellum,
        border: `1px ${borderStyle} ${C.ink}`,
        borderRadius: 80,
        padding: compact ? "4px 12px" : "10px 18px",
        minWidth: compact ? 100 : 140,
        boxShadow: simulator
          ? `0 -2px 0 ${C.gold}, 0 2px 0 ${C.gold}`
          : "none",
        textAlign: "center",
        fontFamily: "var(--f-body)",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: -4,
          right: 8,
          width: 10,
          height: 10,
          borderRadius: "50%",
          background: pip,
          border: `1px solid ${C.ink}`,
        }}
        className={pulsing ? "c-pip-stuck" : undefined}
        aria-label={`pod ${pod.pod_id} state ${pod.agent_state}`}
      />
      <div
        aria-hidden
        style={{
          width: 18,
          height: 18,
          background: podHue(pod.pod_id),
          color: C.parchment,
          borderRadius: "50%",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "var(--f-display)",
          fontSize: 9,
          marginRight: 8,
          verticalAlign: "middle",
        }}
      >
        {monogram(role)}
      </div>
      <span
        className="c-display"
        style={{ fontSize: compact ? 10 : 12, verticalAlign: "middle" }}
      >
        {role}
      </span>
      {!compact && sparkline && sparkline.length > 1 ? (
        <Sparkline values={sparkline} />
      ) : null}
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const w = 80;
  const h = 12;
  const max = Math.max(...values, 1);
  const step = w / (values.length - 1);
  const path = values
    .map((v, i) => `${i === 0 ? "M" : "L"} ${i * step} ${h - (v / max) * h}`)
    .join(" ");
  return (
    <svg
      width={w}
      height={h}
      style={{ display: "block", margin: "6px auto 0" }}
      aria-hidden
    >
      <path d={path} fill="none" stroke={C.inkFaded} strokeWidth={1} />
    </svg>
  );
}
