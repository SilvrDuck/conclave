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

/**
 * Side drawer for one pod. Inspects its endpoints, recent calls, gives
 * Augustus a DM box, and a charter editor (pre-loaded from disk).
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
        maxWidth="640px"
        align="start"
        style={{ position: "fixed", right: 0, top: 0, bottom: 0, height: "100vh" }}
      >
        <VisuallyHidden>
          <Dialog.Title>Pod details: {podId ?? ""}</Dialog.Title>
          <Dialog.Description>
            Inspect a pod's endpoints, calls, charter, and DM with it.
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
  const pod = (pods ?? []).find((p) => p.pod_id === podId);
  const inboundCalls = (calls ?? []).filter((c) => c.dst_pod === podId);
  const outboundCalls = (calls ?? []).filter((c) => c.src_pod === podId);

  return (
    <Flex direction="column" className="h-full">
      <Box className="pb-3">
        <Heading size="4">{pod?.display_role ?? podId}</Heading>
        <Flex gap="2" mt="1">
          <Badge color="gray">{podId}</Badge>
          {pod && (
            <>
              <Badge color={pod.admitted ? "green" : "gray"}>
                {pod.admitted ? "admitted" : "candidate"}
              </Badge>
              <Badge>{pod.image_strategy}</Badge>
              {pod.main_image && <Badge color="amber">{pod.main_image}</Badge>}
            </>
          )}
        </Flex>
      </Box>
      <Separator size="4" my="2" />

      <Tabs.Root defaultValue="dm" className="flex-1 flex flex-col">
        <Tabs.List>
          <Tabs.Trigger value="dm">DM</Tabs.Trigger>
          <Tabs.Trigger value="charter">Charter</Tabs.Trigger>
          <Tabs.Trigger value="endpoints">Endpoints</Tabs.Trigger>
          <Tabs.Trigger value="calls">Calls</Tabs.Trigger>
        </Tabs.List>

        <Box className="flex-1 overflow-y-auto pt-3">
          <Tabs.Content value="dm">
            <DMTab podId={podId} />
          </Tabs.Content>
          <Tabs.Content value="charter">
            <CharterTab podId={podId} />
          </Tabs.Content>
          <Tabs.Content value="endpoints">
            <EndpointsTab endpoints={endpoints ?? []} />
          </Tabs.Content>
          <Tabs.Content value="calls">
            <CallsTab
              inbound={inboundCalls}
              outbound={outboundCalls}
            />
          </Tabs.Content>
        </Box>
      </Tabs.Root>
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
              {m.from_pod}
            </Text>
            <Text size="2" className="block whitespace-pre-wrap">
              {m.body}
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

function CharterTab({ podId }: { podId: string }) {
  // Charter content lives in the pod's git workspace. The observer doesn't
  // currently expose it through an API. v1 pre-loaded from disk; v2 forum
  // shell stubs the editor — full impl pairs with the pod template branch.
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => setBody(""), [podId]);
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
        Edit this pod's charter. Empty bodies are ignored; a non-empty save bumps the
        charter version and wakes the agent on next turn.
      </Text>
      <TextArea
        rows={12}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="# {pod}'s charter\n\n## priorities\n..."
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
          <span className="text-slate-400 mr-2">{c[side]}</span>
          {c.method} {c.path}{" "}
          {c.status && <span className="text-amber-400">[{c.status}]</span>}
        </Text>
      ))}
    </Flex>
  );
}
