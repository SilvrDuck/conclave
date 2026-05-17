import { useState, useEffect } from "react";
import useSWR from "swr";
import {
  Dialog,
  Box,
  Flex,
  Heading,
  Text,
  Badge,
  Button,
  TextArea,
  TextField,
  Separator,
  Tabs,
  VisuallyHidden,
} from "@radix-ui/themes";
import {
  Call,
  CouncilMessage,
  EndpointRow,
  Pod,
  fetcher,
  postCommand,
} from "../api";
import { Markdown } from "./Markdown";
import { Linkified } from "./Linkified";
import { EntityLink } from "./EntityLink";

type CharterDoc = { pod_id: string; body: string; size: number; mtime: string };
type FilesDoc = {
  pod_id: string;
  root: string;
  truncated: boolean;
  entries: { path: string; kind: "file" | "dir"; size: number | null }[];
};
type Turn = {
  turn_id: string;
  started_at: string | null;
  ended_at: string | null;
  tokens_in: number;
  tokens_out: number;
  status: "ended" | "in_flight";
};

/**
 * Side drawer for one pod. Renders charter, live turn transcript,
 * endpoints, calls, DM, and a workspace file tree. Pre-loads charter
 * via /state/pods/{id}/charter so the editor isn't a blank box.
 */
export function PodDrawer({
  podId,
  onClose,
}: {
  podId: string | null;
  onClose: () => void;
}) {
  const open = podId !== null;
  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Content
        maxWidth="720px"
        align="start"
        style={{ position: "fixed", right: 0, top: 0, bottom: 0, height: "100vh" }}
      >
        <VisuallyHidden>
          <Dialog.Title>Pod details: {podId ?? ""}</Dialog.Title>
          <Dialog.Description>
            Inspect a pod's charter, transcript, endpoints, calls, files, and DM with it.
          </Dialog.Description>
        </VisuallyHidden>
        {podId && <PodInside podId={podId} />}
      </Dialog.Content>
    </Dialog.Root>
  );
}

function PodInside({ podId }: { podId: string }) {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher);
  const { data: endpoints } = useSWR<EndpointRow[]>(
    `/state/endpoints?pod_id=${encodeURIComponent(podId)}`,
    fetcher,
  );
  const { data: calls } = useSWR<Call[]>("/state/calls?since_seconds=300", fetcher);
  const { data: charter } = useSWR<CharterDoc | { detail: string }>(
    `/state/pods/${encodeURIComponent(podId)}/charter`,
    fetcher,
  );
  const pod = (pods ?? []).find((p) => p.pod_id === podId);
  const inboundCalls = (calls ?? []).filter((c) => c.dst_pod === podId);
  const outboundCalls = (calls ?? []).filter((c) => c.src_pod === podId);
  const charterBody = charter && "body" in charter ? charter.body : "";

  const [restartBusy, setRestartBusy] = useState(false);
  const restart = async () => {
    if (restartBusy) return;
    if (!window.confirm(`Restart pod ${podId}? The container will be recreated; the agent resumes on the next inbox event.`))
      return;
    setRestartBusy(true);
    try {
      await postCommand({ kind: "RestartPod", pod_id: podId });
    } finally {
      setRestartBusy(false);
    }
  };

  return (
    <Flex direction="column" className="h-full">
      <Box className="pb-3">
        <Flex justify="between" align="start" gap="3">
          <Box>
            <Heading size="4">{pod?.display_role ?? podId}</Heading>
            <Flex gap="2" mt="1" wrap="wrap">
              <Badge color="gray">{podId}</Badge>
              {pod && (
                <>
                  <Badge color={pod.admitted ? "green" : "gray"}>
                    {pod.admitted ? "admitted" : "candidate"}
                  </Badge>
                  <Badge>{pod.image_strategy}</Badge>
                  <Badge color={pod.agent_state === "thinking" ? "amber" : "gray"}>
                    {pod.agent_state}
                  </Badge>
                  {pod.main_image && <Badge color="amber">{pod.main_image}</Badge>}
                </>
              )}
            </Flex>
          </Box>
          {/* ATAM Op4 — Restart pod. Confirms before firing so an
            accidental click can't kill a thinking agent. */}
          <Button
            size="1"
            variant="soft"
            color="orange"
            onClick={restart}
            disabled={restartBusy || !pod}
          >
            {restartBusy ? "restarting…" : "Restart"}
          </Button>
        </Flex>
      </Box>

      {/* Charter rendered above the tabs per UX direction — the rules
        the pod operates under are first-class context, not a tab. */}
      {charterBody ? (
        <Box className="pb-3">
          <Markdown body={charterBody} />
        </Box>
      ) : null}

      <Separator size="4" my="2" />

      <Tabs.Root defaultValue="thinking" className="flex-1 flex flex-col">
        <Tabs.List>
          <Tabs.Trigger value="thinking">Thinking</Tabs.Trigger>
          <Tabs.Trigger value="dm">DM</Tabs.Trigger>
          <Tabs.Trigger value="charter">Charter</Tabs.Trigger>
          <Tabs.Trigger value="endpoints">Endpoints</Tabs.Trigger>
          <Tabs.Trigger value="files">Files</Tabs.Trigger>
          <Tabs.Trigger value="calls">Calls</Tabs.Trigger>
        </Tabs.List>

        <Box className="flex-1 overflow-y-auto pt-3">
          <Tabs.Content value="thinking">
            <ThinkingTab podId={podId} />
          </Tabs.Content>
          <Tabs.Content value="dm">
            <DMTab podId={podId} />
          </Tabs.Content>
          <Tabs.Content value="charter">
            <CharterTab podId={podId} initialBody={charterBody} />
          </Tabs.Content>
          <Tabs.Content value="endpoints">
            <EndpointsTab endpoints={endpoints ?? []} />
          </Tabs.Content>
          <Tabs.Content value="files">
            <FilesTab podId={podId} />
          </Tabs.Content>
          <Tabs.Content value="calls">
            <CallsTab inbound={inboundCalls} outbound={outboundCalls} />
          </Tabs.Content>
        </Box>
      </Tabs.Root>
    </Flex>
  );
}

function ThinkingTab({ podId }: { podId: string }) {
  const { data: turns } = useSWR<Turn[]>(
    `/state/pods/${encodeURIComponent(podId)}/turns?limit=30`,
    fetcher,
    { refreshInterval: 2000 },
  );
  if (!turns) return <Text color="gray">loading…</Text>;
  if (turns.length === 0)
    return (
      <Text color="gray">
        No agent turns yet. New turns appear here as the pod thinks.
      </Text>
    );
  return (
    <Flex direction="column" gap="2">
      <Text size="1" color="gray">
        Live turn list. Full streaming transcript is the J4 follow-up (#90).
      </Text>
      {turns.map((t) => (
        <Box key={t.turn_id} className="border border-slate-700 rounded p-2">
          <Flex justify="between" align="center">
            <Text size="2" weight="bold" className="font-mono">
              {t.turn_id}
            </Text>
            <Badge color={t.status === "in_flight" ? "amber" : "gray"}>
              {t.status === "in_flight" ? "thinking" : "ended"}
            </Badge>
          </Flex>
          <Text size="1" color="gray" as="div">
            started {t.started_at?.replace("T", " ").slice(0, 19) ?? "—"}
            {t.ended_at ? ` · ended ${t.ended_at.replace("T", " ").slice(0, 19)}` : ""}
          </Text>
          <Text size="1" color="gray">
            tokens in/out: {t.tokens_in.toLocaleString()} / {t.tokens_out.toLocaleString()}
          </Text>
        </Box>
      ))}
    </Flex>
  );
}

function DMTab({ podId }: { podId: string }) {
  const { data: councils } = useSWR<{
    council_id: string;
    private: boolean;
    participants: string[];
  }[]>("/state/councils", fetcher);
  const myDM = (councils ?? []).find(
    (c) =>
      c.private &&
      c.participants.length === 2 &&
      c.participants.includes("__augustus__") &&
      c.participants.includes(podId),
  );
  const { data: msgs } = useSWR<CouncilMessage[]>(
    myDM ? `/state/councils/${myDM.council_id}/messages` : null,
    fetcher,
    { refreshInterval: 3000 },
  );
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const send = async () => {
    if (!body.trim()) return;
    setBusy(true);
    try {
      await postCommand({ kind: "SendDirectMessage", pod_id: podId, body });
      setBody("");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Flex direction="column" gap="2">
      <Box className="bg-slate-900 rounded p-3 min-h-32 max-h-72 overflow-y-auto">
        {(msgs ?? []).map((m) => (
          <Box key={m.seq} mb="2">
            <Text size="1" color="gray">
              <EntityLink kind="pod" id={m.from_pod}>{m.from_pod}</EntityLink>
            </Text>
            <Text size="2" className="block whitespace-pre-wrap">
              <Linkified text={m.body} />
            </Text>
          </Box>
        ))}
        {(msgs ?? []).length === 0 && (
          <Text size="2" color="gray">
            (no messages yet)
          </Text>
        )}
      </Box>
      <TextField.Root
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Tell this pod something…"
        onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
      />
      <Button onClick={send} disabled={busy || !body.trim()}>
        Send
      </Button>
    </Flex>
  );
}

function CharterTab({
  podId,
  initialBody,
}: {
  podId: string;
  initialBody: string;
}) {
  const [body, setBody] = useState(initialBody);
  const [busy, setBusy] = useState(false);
  useEffect(() => setBody(initialBody), [podId, initialBody]);
  const save = async () => {
    if (!body.trim()) return;
    setBusy(true);
    try {
      await postCommand({ kind: "EditCharter", pod_id: podId, body });
    } finally {
      setBusy(false);
    }
  };
  return (
    <Flex direction="column" gap="2">
      <Text size="1" color="gray">
        Edit this pod's charter. Saves are versioned; the agent picks up changes on the next turn.
      </Text>
      <TextArea
        rows={14}
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
      <Button onClick={save} disabled={busy || !body.trim()}>
        Save
      </Button>
    </Flex>
  );
}

function EndpointsTab({ endpoints }: { endpoints: EndpointRow[] }) {
  if (endpoints.length === 0)
    return <Text color="gray">No endpoints observed for this pod.</Text>;
  return (
    <Flex direction="column" gap="1">
      {endpoints.map((e) => (
        <Text size="2" key={`${e.method}-${e.path}`} className="font-mono">
          <span className="text-amber-400 mr-2">{e.method}</span>
          {e.path}
          {e.annotation && <span className="text-slate-400"> — {e.annotation}</span>}
        </Text>
      ))}
    </Flex>
  );
}

function FilesTab({ podId }: { podId: string }) {
  const { data } = useSWR<FilesDoc | { detail: string }>(
    `/state/pods/${encodeURIComponent(podId)}/files`,
    fetcher,
  );
  if (!data) return <Text color="gray">loading…</Text>;
  if ("detail" in data)
    return <Text color="gray">{data.detail}</Text>;
  if (data.entries.length === 0)
    return <Text color="gray">workspace empty</Text>;
  return (
    <Flex direction="column" gap="0">
      <Text size="1" color="gray">
        {data.root} {data.truncated ? "(truncated)" : ""}
      </Text>
      {data.entries.map((e) => (
        <Text
          size="2"
          key={e.path}
          className="font-mono"
          color={e.kind === "dir" ? "amber" : undefined}
        >
          {e.kind === "dir" ? "📂 " : "📄 "}
          {e.path}
          {e.size !== null ? (
            <span className="text-slate-500"> · {e.size}b</span>
          ) : null}
        </Text>
      ))}
    </Flex>
  );
}

function CallsTab({ inbound, outbound }: { inbound: Call[]; outbound: Call[] }) {
  return (
    <Flex direction="column" gap="3">
      <Box>
        <Heading size="2" mb="1">
          Inbound (last 5 min)
        </Heading>
        <CallList rows={inbound} side="src_pod" />
      </Box>
      <Box>
        <Heading size="2" mb="1">
          Outbound (last 5 min)
        </Heading>
        <CallList rows={outbound} side="dst_pod" />
      </Box>
    </Flex>
  );
}

function CallList({ rows, side }: { rows: Call[]; side: "src_pod" | "dst_pod" }) {
  if (rows.length === 0) return <Text color="gray">(none)</Text>;
  return (
    <Flex direction="column" gap="1">
      {rows.slice(0, 50).map((c, i) => (
        <Text size="2" key={i} className="font-mono">
          <EntityLink kind="pod" id={c[side]}>{c[side]}</EntityLink>
          <span className="mx-2">{c.method} {c.path}</span>
          {c.status && <span className="text-amber-400">[{c.status}]</span>}
        </Text>
      ))}
    </Flex>
  );
}
