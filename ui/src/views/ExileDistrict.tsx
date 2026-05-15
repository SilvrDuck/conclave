import useSWR from "swr";
import { listMembers } from "../api/observer";
import type { Member } from "../api/observer";
import { StoneTablet } from "../components/StoneTablet";

export function ExileDistrict() {
  const { data, error } = useSWR<Member[]>("members", listMembers);
  const exiled = data?.filter((m) => m.status === "exiled") ?? [];

  function proposeRevival(name: string) {
    console.log("revival-intent", { pod: name });
    alert(
      `Would call senate.propose_revival(${name}) — backend not wired yet.`,
    );
  }

  return (
    <section>
      <h2>Exile District</h2>
      <p>
        Former pods. Their code lives in <code>exile/</code> and they may be
        revived by senate vote.
      </p>

      {error ? (
        <p style={{ color: "#a23" }}>
          Could not reach observer: {(error as Error).message}
        </p>
      ) : null}

      {exiled.length === 0 && data ? <p>No exiled pods.</p> : null}

      {exiled.map((m) => (
        <StoneTablet
          key={m.name}
          title={m.name}
          meta={`exiled ${m.exiled_at ?? "unknown"} · charter: ${m.charter_path}`}
        >
          <button type="button" onClick={() => proposeRevival(m.name)}>
            Propose revival
          </button>
        </StoneTablet>
      ))}
    </section>
  );
}
