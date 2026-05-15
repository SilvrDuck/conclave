import useSWR from "swr";
import { listChatrooms } from "../api/observer";
import type { Chatroom } from "../api/observer";
import { StoneTablet } from "../components/StoneTablet";

const REFRESH_MS = 5000;

export function Council() {
  const { data, error, isLoading } = useSWR<Chatroom[]>(
    "chatrooms",
    listChatrooms,
    {
      refreshInterval: REFRESH_MS,
    },
  );

  return (
    <section>
      <h2>Council</h2>
      <p>
        Live chatrooms and councils. Full transcripts live in the bus; this view
        lists recent rooms.
      </p>

      {error ? (
        <p style={{ color: "#a23" }}>
          Could not reach observer: {(error as Error).message}
        </p>
      ) : null}

      {isLoading ? <p>Loading chatrooms...</p> : null}

      {data && data.length === 0 ? <p>No chatrooms open.</p> : null}

      {data?.map((room) => (
        <StoneTablet
          key={room.id}
          title={room.topic || room.id}
          meta={`opened by ${room.opened_by} · ${room.participants.join(", ")} · last active ${room.last_active}`}
        >
          {room.summary ? (
            <p>{room.summary}</p>
          ) : (
            <p>
              <em>Transcript not yet rendered.</em>
            </p>
          )}
          {room.closed_at ? (
            <small>closed {room.closed_at}</small>
          ) : (
            <small>open</small>
          )}
        </StoneTablet>
      ))}
    </section>
  );
}
