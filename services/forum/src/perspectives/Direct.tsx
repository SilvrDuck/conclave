/** Spec/09 §5 — Direct perspective. Three sections, all driven by
 * a single selected pod:
 *
 *   1. Charter Editor (top, via the CharterEditor component)
 *   2. DM thread (bottom)
 *   3. Persistent right drawer: live agent transcript
 *
 * Selecting a pod from the chooser also opens its folio in the
 * right drawer so the live transcript stays visible. */

import { useEffect, useState } from "react";
import useSWR from "swr";
import { fetcher, postCommand, type Pod } from "../api";
import { Phylactery } from "../components/Phylactery";
import { CharterEditor } from "../components/CharterEditor";
import { WaxSeal } from "../components/WaxSeal";
import { useFolio } from "../folio";
import { C } from "../theme";

export function Direct() {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher, {
    refreshInterval: 5000,
  });
  const [selectedPodId, setSelectedPodId] = useState<string | null>(
    (pods ?? [])[0]?.pod_id ?? null,
  );
  // Seed selection once pods arrive.
  useEffect(() => {
    if (selectedPodId === null && (pods ?? []).length > 0) {
      setSelectedPodId(pods![0].pod_id);
    }
  }, [pods, selectedPodId]);

  const folio = useFolio();
  // Per spec/09 §5 — the persistent right drawer mirrors the
  // selected pod so the live transcript stays visible while editing
  // the charter or sending a DM. Only push when the drawer's empty
  // or its top entry already points at this pod; otherwise we'd
  // hijack the user's own click-through navigation (a folio close
  // would re-open immediately; an EntityLink to a council would be
  // overwritten on the next render).
  useEffect(() => {
    if (!selectedPodId) return;
    const top = folio.stack[folio.stack.length - 1];
    const drawerEmpty = folio.stack.length === 0;
    const onThisPod = top?.kind === "pod" && top.id === selectedPodId;
    if (drawerEmpty || onThisPod) {
      folio.open({ kind: "pod", id: selectedPodId });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPodId]);

  if ((pods ?? []).length === 0) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <p className="c-faded" style={{ fontStyle: "italic" }}>
          no pods yet — issue a proclamation first.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <CharterEditor
        selectedPodId={selectedPodId}
        onSelect={setSelectedPodId}
      />
      <div
        style={{
          borderTop: `0.5px solid ${C.inkFaded}`,
          padding: 16,
        }}
      >
        <h2 className="c-display" style={{ margin: 0, fontSize: 13 }}>
          Direct messages
        </h2>
        {selectedPodId ? (
          <DMThread podId={selectedPodId} />
        ) : (
          <p
            className="c-faded"
            style={{ fontStyle: "italic", marginTop: 12 }}
          >
            select a pod above to send a message.
          </p>
        )}
      </div>
    </div>
  );
}

function DMThread({ podId }: { podId: string }) {
  // The DM history per pod isn't exposed directly today; surface a
  // send-only affordance with a clear ack so Augustus knows the nudge
  // landed. The full transcript shows up in the folio drawer's live
  // transcript band.
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [lastSent, setLastSent] = useState<string | null>(null);
  return (
    <div style={{ marginTop: 12 }}>
      {lastSent ? (
        <Phylactery
          sender="__augustus__"
          body={lastSent}
          sentAt={new Date().toISOString()}
        />
      ) : null}
      <textarea
        rows={3}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="A missive…"
        style={{
          width: "100%",
          marginTop: 8,
          padding: 10,
          background: C.parchment,
          color: C.ink,
          border: `0.5px solid ${C.inkFaded}`,
          fontFamily: "var(--f-body)",
          fontSize: 14,
          resize: "vertical",
        }}
      />
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginTop: 6,
        }}
      >
        <WaxSeal
          letter="M"
          label="Send missive"
          disabled={pending || !draft.trim()}
          onClick={async () => {
            const body = draft.trim();
            setPending(true);
            try {
              await postCommand({
                kind: "SendDirectMessage",
                pod_id: podId,
                body,
              });
              setLastSent(body);
              setDraft("");
            } finally {
              setPending(false);
            }
          }}
        />
      </div>
    </div>
  );
}
