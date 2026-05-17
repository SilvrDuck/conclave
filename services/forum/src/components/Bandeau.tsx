/** Spec/09 §1 — Bandeau. The 40px top bar. The only persistent
 * chrome in the app.
 *
 * Layout, left-to-right:
 *   1. CONCLAVE wordmark (Cinzel small-caps 14)
 *   2. Current proclamation numeral + truncated text
 *   3. P wax seal (Proclaim)
 *   4. Perspective toggle (Glance / Witness / Try / Direct)
 *   5. Inbox bell (cinnabar dot when non-empty)
 *   6. Status dot
 *   7. Reset link */

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import useSWR from "swr";
import {
  fetcher,
  postCommand,
  type InboxItem,
  type Pod,
  type Proclamation,
} from "../api";
import { C, toRoman } from "../theme";
import { WaxSeal } from "./WaxSeal";
import { EntityLink } from "./EntityLink";

export type Perspective = "glance" | "witness" | "try" | "direct" | "inbox";

interface Props {
  perspective: Perspective;
  onChangePerspective: (p: Perspective) => void;
}

export function Bandeau({ perspective, onChangePerspective }: Props) {
  const { data: procs } = useSWR<Proclamation[]>(
    "/state/proclamations",
    fetcher,
    { refreshInterval: 5000 },
  );
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher, {
    refreshInterval: 5000,
  });
  const { data: inbox } = useSWR<InboxItem[]>(
    "/inbox?for=__augustus__",
    fetcher,
    { refreshInterval: 5000 },
  );

  const latest = procs?.[0];
  const hasConclave = (pods?.length ?? 0) > 0;
  const inboxCount = (inbox ?? []).length;
  const overallStatus = computeStatus(pods ?? []);

  return (
    <header className="c-bandeau">
      <span className="c-display" style={{ fontSize: 14, color: C.ink }}>
        Conclave
      </span>
      {latest ? (
        <EntityLink
          kind="proclamation"
          id={String(latest.seq)}
          label={`№ ${latest.seq}`}
        >
          <span
            style={{ display: "inline-flex", alignItems: "baseline", gap: 6 }}
          >
            <span className="c-numeral c-gold">№ {toRoman(latest.seq)}</span>
            <span
              className="c-faded"
              style={{
                fontStyle: "italic",
                maxWidth: 360,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                fontSize: 13,
              }}
            >
              {latest.text}
            </span>
          </span>
        </EntityLink>
      ) : null}

      {hasConclave ? <ProclamationSealButton /> : null}

      <PerspectiveToggle
        perspective={perspective}
        onChange={onChangePerspective}
      />

      <button
        type="button"
        onClick={() => onChangePerspective("inbox")}
        aria-label={`inbox — ${inboxCount} pending`}
        title={`inbox — ${inboxCount} pending`}
        className="c-display"
        style={{
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          color: C.ink,
          fontSize: 13,
          position: "relative",
          marginLeft: "auto",
        }}
      >
        Inbox
        {inboxCount > 0 ? (
          <span
            aria-hidden
            style={{
              position: "absolute",
              top: -4,
              right: -8,
              width: 8,
              height: 8,
              background: C.cinnabar,
              borderRadius: "50%",
            }}
          />
        ) : null}
      </button>

      <span
        title="overall health"
        aria-label={`overall health: ${overallStatus.label}`}
        style={{
          width: 12,
          height: 12,
          background: overallStatus.color,
          borderRadius: "50%",
          border: `1px solid ${C.ink}`,
          marginLeft: 4,
        }}
      />

      <ResetButton />
    </header>
  );
}

function PerspectiveToggle({
  perspective,
  onChange,
}: {
  perspective: Perspective;
  onChange: (p: Perspective) => void;
}) {
  const items: Array<{ key: Perspective; label: string }> = [
    { key: "glance", label: "Glance" },
    { key: "witness", label: "Witness" },
    { key: "try", label: "Try" },
    { key: "direct", label: "Direct" },
  ];
  return (
    <nav style={{ display: "flex", gap: 0 }}>
      {items.map((i) => {
        const active = perspective === i.key;
        return (
          <button
            key={i.key}
            type="button"
            onClick={() => onChange(i.key)}
            aria-current={active ? "page" : undefined}
            className="c-display"
            style={{
              background: "transparent",
              border: "none",
              padding: "8px 10px",
              borderBottom: `2px solid ${active ? C.gold : "transparent"}`,
              color: active ? C.ink : C.inkFaded,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {i.label}
          </button>
        );
      })}
    </nav>
  );
}

function computeStatus(pods: Pod[]): { color: string; label: string } {
  if (pods.length === 0) return { color: C.wash, label: "empty" };
  if (pods.some((p) => p.agent_state === "stuck" || p.runtime_status === "stopped"))
    return { color: C.cinnabar, label: "blocked" };
  return { color: C.verdigris, label: "breathing" };
}

function ProclamationSealButton() {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <WaxSeal letter="P" label="Proclaim" size={28} />
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(31,26,20,0.45)",
            zIndex: 40,
          }}
        />
        <Dialog.Content
          aria-describedby={undefined}
          style={{
            position: "fixed",
            left: "50%",
            top: "20%",
            transform: "translateX(-50%)",
            width: 640,
            maxWidth: "90vw",
            background: C.vellum,
            border: `1px solid ${C.ink}`,
            padding: 20,
            zIndex: 50,
          }}
        >
          <Dialog.Title asChild>
            <h2
              className="c-display"
              style={{ margin: 0, fontSize: "var(--t-heading)" }}
            >
              Proclaim
            </h2>
          </Dialog.Title>
          <textarea
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Speak, and the conclave listens…"
            rows={5}
            style={{
              width: "100%",
              marginTop: 12,
              background: C.parchment,
              color: C.ink,
              border: `0.5px solid ${C.inkFaded}`,
              padding: 12,
              fontFamily: "var(--f-body)",
              fontSize: 16,
              lineHeight: 1.45,
              resize: "vertical",
            }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 12,
              marginTop: 12,
              alignItems: "center",
            }}
          >
            <button
              type="button"
              className="c-link"
              onClick={() => setOpen(false)}
              style={{ background: "transparent", border: "none" }}
            >
              cancel
            </button>
            <WaxSeal
              letter="P"
              label="Send proclamation"
              disabled={pending || !text.trim()}
              onClick={async () => {
                setPending(true);
                try {
                  await postCommand({
                    kind: "IssueProclamation",
                    text: text.trim(),
                  });
                  setText("");
                  setOpen(false);
                } finally {
                  setPending(false);
                }
              }}
            />
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ResetButton() {
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  return (
    <Dialog.Root open={confirming} onOpenChange={setConfirming}>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className="c-link"
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            fontSize: 13,
          }}
        >
          reset
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(31,26,20,0.45)",
            zIndex: 40,
          }}
        />
        <Dialog.Content
          aria-describedby={undefined}
          style={{
            position: "fixed",
            left: "50%",
            top: "30%",
            transform: "translateX(-50%)",
            width: 480,
            background: C.vellum,
            border: `1px solid ${C.cinnabar}`,
            padding: 20,
            zIndex: 50,
          }}
        >
          <Dialog.Title asChild>
            <h2
              className="c-display"
              style={{ margin: 0, fontSize: "var(--t-heading)", color: C.cinnabar }}
            >
              Wipe the conclave?
            </h2>
          </Dialog.Title>
          <p style={{ fontFamily: "var(--f-body)" }}>
            Every pod, proposal, council and decision is removed. The
            architectural record is cleared. The Docker stack itself
            stays up.
          </p>
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 12,
              alignItems: "center",
            }}
          >
            <button
              type="button"
              className="c-link"
              onClick={() => setConfirming(false)}
              style={{ background: "transparent", border: "none" }}
            >
              cancel
            </button>
            <button
              type="button"
              disabled={pending}
              onClick={async () => {
                setPending(true);
                try {
                  await postCommand({ kind: "ResetState" });
                  setConfirming(false);
                } finally {
                  setPending(false);
                }
              }}
              style={{
                background: C.cinnabar,
                color: C.parchment,
                border: "none",
                padding: "6px 14px",
                fontFamily: "var(--f-display)",
                fontSize: 12,
                letterSpacing: "0.1em",
                cursor: "pointer",
              }}
            >
              {pending ? "WIPING…" : "WIPE"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

