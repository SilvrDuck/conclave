import { useState } from "react";
import useSWR from "swr";
import { listMembers } from "../api/observer";
import type { Member } from "../api/observer";

export function CharterEditor() {
  const { data: members } = useSWR<Member[]>("members", listMembers);
  const [explicit, setExplicit] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [status, setStatus] = useState<string | null>(null);

  const selected = explicit ?? members?.[0]?.name ?? "";
  const setSelected = (name: string) => setExplicit(name);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const intent = {
      action: "charter_edit",
      pod: selected,
      charter: draft,
    };
    console.log("charter-edit intent", intent);
    setStatus(
      `Would PR pods/${selected}/charter.md (charter backend not wired yet)`,
    );
  }

  return (
    <section>
      <h2>Charter Editor</h2>
      <p>
        Edit any agent's system prompt. The change effective on the agent's next
        wake.
      </p>

      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
          maxWidth: "720px",
        }}
      >
        <label>
          Pod{" "}
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {members?.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name} ({m.status})
              </option>
            ))}
          </select>
        </label>

        <label htmlFor="charter-body">Charter</label>
        <textarea
          id="charter-body"
          rows={16}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="# Charter of alice&#10;&#10;You are the maintainer of the auth service..."
        />

        <button type="submit" disabled={!selected || draft.length === 0}>
          Submit charter edit
        </button>
      </form>

      {status ? (
        <p style={{ marginTop: "1rem", color: "var(--stone)" }}>{status}</p>
      ) : null}
    </section>
  );
}
