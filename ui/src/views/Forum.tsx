import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { getAgenda, listMembers, sendMandate } from "../api/observer";
import type { AgendaSnapshot, Member } from "../api/observer";
import { drawDomus, spritePosition } from "../components/Sprite";

const CANVAS_W = 800;
const CANVAS_H = 500;
const REFRESH_MS = 5000;

function hasActiveAgenda(snap: AgendaSnapshot | undefined): boolean {
  if (!snap) return false;
  return snap.doing.length > 0;
}

export function Forum() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { data: members, error } = useSWR<Member[]>("members", listMembers, {
    refreshInterval: REFRESH_MS,
  });
  const [agendas, setAgendas] = useState<Record<string, AgendaSnapshot>>({});

  useEffect(() => {
    if (!members) return;
    let cancelled = false;
    const admitted = members.filter((m) => m.status === "admitted");
    Promise.all(
      admitted.map(async (m) => {
        try {
          const snap = await getAgenda(m.name);
          return [m.name, snap] as const;
        } catch {
          return null;
        }
      }),
    ).then((pairs) => {
      if (cancelled) return;
      const next: Record<string, AgendaSnapshot> = {};
      for (const p of pairs) {
        if (p) next[p[0]] = p[1];
      }
      setAgendas(next);
    });
    return () => {
      cancelled = true;
    };
  }, [members]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.fillStyle = "#c8a86a";
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    ctx.strokeStyle = "#8a7444";
    for (let y = 40; y < CANVAS_H; y += 80) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(CANVAS_W, y);
      ctx.stroke();
    }

    ctx.fillStyle = "#2a221a";
    ctx.font = '14px "JetBrains Mono", monospace';
    ctx.textAlign = "left";
    ctx.fillText("FORUM ROMANUM", 12, 22);

    if (!members) return;

    for (const m of members) {
      if (m.status === "exiled") continue;
      const { x, y } = spritePosition(m.name, CANVAS_W, CANVAS_H);
      const glow = m.status === "admitted" && hasActiveAgenda(agendas[m.name]);
      const tint = m.status === "proposed" ? "#bfb7a0" : undefined;
      drawDomus(ctx, x, y, { glow, tint, label: m.name });
    }
  }, [members, agendas]);

  return (
    <section>
      <h2>Forum</h2>
      <p>
        Each domus is a pod. Yellow halos mark members currently working on
        something (agenda item in <code>doing</code>). Updated every{" "}
        {REFRESH_MS / 1000}s.
      </p>
      <MandateInput />
      {error ? (
        <p style={{ color: "#a23" }}>
          Could not reach observer: {(error as Error).message}
        </p>
      ) : null}
      <canvas
        ref={canvasRef}
        className="forum-canvas"
        width={CANVAS_W}
        height={CANVAS_H}
      />
      <p style={{ marginTop: "1rem", color: "var(--stone)" }}>
        Members: {members ? members.length : "..."}
      </p>
    </section>
  );
}

function MandateInput() {
  const [goal, setGoal] = useState("");
  const [pod, setPod] = useState("founder");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!goal.trim()) return;
    setBusy(true);
    setStatus(null);
    try {
      await sendMandate(pod, goal);
      setStatus(`Published to pod/${pod}/inbox.`);
      setGoal("");
    } catch (err) {
      setStatus(`Failed: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      style={{
        display: "flex",
        gap: "0.5rem",
        margin: "0.75rem 0 1rem",
        padding: "0.75rem",
        background: "var(--marble)",
        border: "1px solid var(--stone)",
        borderRadius: "4px",
      }}
    >
      <input
        type="text"
        value={pod}
        onChange={(e) => setPod(e.target.value)}
        style={{ width: "10ch", fontFamily: '"JetBrains Mono", monospace' }}
        aria-label="Target pod"
      />
      <input
        type="text"
        placeholder="Mandate (e.g., 'propose a peer named alice to own the auth service')"
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        style={{ flex: 1 }}
        aria-label="Mandate"
      />
      <button type="submit" disabled={busy || !goal.trim()}>
        {busy ? "Sending…" : "Send mandate"}
      </button>
      {status ? (
        <span
          style={{
            alignSelf: "center",
            color: status.startsWith("Failed") ? "#a23" : "var(--stone)",
            fontSize: "0.85em",
          }}
        >
          {status}
        </span>
      ) : null}
    </form>
  );
}
