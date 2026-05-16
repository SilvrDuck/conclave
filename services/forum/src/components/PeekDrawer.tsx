import * as Dialog from "@radix-ui/react-dialog";
import { Cross1Icon, ChevronLeftIcon } from "@radix-ui/react-icons";
import { Box, Flex, IconButton, Text } from "@radix-ui/themes";
import useSWR from "swr";
import { usePeek, type EntityRef } from "./PeekContext";
import { Markdown } from "./Markdown";
import { EntityLink } from "./EntityLink";
import { Linkified } from "./Linkified";
import { Phylactery } from "./Phylactery";

const OBSERVER_URL =
  (import.meta.env?.VITE_OBSERVER_URL as string | undefined) ??
  "http://localhost:8000";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

/** Top of the peek stack opens a Radix Dialog as a side drawer. The
 * stack lets users traverse chains; the back arrow pops back. */
export function PeekDrawer() {
  const { stack, pop, clear } = usePeek();
  const top = stack[stack.length - 1] ?? null;
  const open = top !== null;
  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o) clear();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content
          className="fixed right-0 top-0 h-full w-[480px] bg-slate-900 border-l border-slate-700 z-50 overflow-y-auto"
          aria-describedby={undefined}
        >
          <Flex justify="between" align="center" className="px-4 py-3 border-b border-slate-700">
            <Flex align="center" gap="2">
              {stack.length > 1 ? (
                <IconButton variant="ghost" onClick={pop} aria-label="back">
                  <ChevronLeftIcon />
                </IconButton>
              ) : null}
              <Dialog.Title asChild>
                <Text size="3" weight="bold">
                  {top ? renderTitle(top) : "—"}
                </Text>
              </Dialog.Title>
            </Flex>
            <Dialog.Close asChild>
              <IconButton variant="ghost" aria-label="close">
                <Cross1Icon />
              </IconButton>
            </Dialog.Close>
          </Flex>
          <Box className="p-4">{top ? <PeekBody ref={top} /> : null}</Box>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function renderTitle(ref: EntityRef): string {
  const label = ref.label ?? ref.id;
  switch (ref.kind) {
    case "pod":
      return `Pod ${label}`;
    case "proclamation":
      return `Proclamation ${label}`;
    case "decision":
      return `Decision ${label}`;
    case "proposal":
      return `Proposal ${label}`;
    case "council":
      return `Council ${label}`;
    case "endpoint":
      return `Endpoint ${label}`;
  }
}

function PeekBody({ ref }: { ref: EntityRef }) {
  switch (ref.kind) {
    case "pod":
      return <PodPeek podId={ref.id} />;
    case "proclamation":
      return <ProclamationPeek seq={ref.id} />;
    case "decision":
      return <DecisionPeek decisionId={ref.id} />;
    case "proposal":
      return <ProposalPeek proposalId={ref.id} />;
    case "council":
      return <CouncilPeek councilId={ref.id} />;
    case "endpoint":
      return <Text>Endpoint {ref.id}</Text>;
  }
}

function PodPeek({ podId }: { podId: string }) {
  const { data: pods } = useSWR<any[]>(`${OBSERVER_URL}/state/pods`, fetcher);
  const { data: charter } = useSWR<any>(
    `${OBSERVER_URL}/state/pods/${podId}/charter`,
    fetcher,
  );
  const pod = pods?.find((p) => p.pod_id === podId);
  if (!pod) return <Text color="gray">Pod not found.</Text>;
  return (
    <Flex direction="column" gap="3">
      <Box>
        <Text size="2" color="gray">role</Text>
        <Text size="4" weight="bold" as="div">{pod.display_role}</Text>
      </Box>
      <Box>
        <Text size="2" color="gray">runtime</Text>
        <Text as="div">{pod.runtime_status} · {pod.agent_state}</Text>
      </Box>
      {charter && !charter.detail ? (
        <Box>
          <Text size="2" color="gray" as="div">charter</Text>
          <Markdown body={charter.body} />
        </Box>
      ) : null}
    </Flex>
  );
}

function ProclamationPeek({ seq }: { seq: string }) {
  const { data } = useSWR<any[]>(`${OBSERVER_URL}/state/proclamations`, fetcher);
  const proc = data?.find((p) => String(p.seq) === seq);
  if (!proc) return <Text color="gray">Proclamation not found.</Text>;
  return (
    <Flex direction="column" gap="2">
      <Markdown body={proc.text} />
      {proc.placeholder_decision_id ? (
        <Text size="2" color="gray">
          decision:{" "}
          <EntityLink kind="decision" id={proc.placeholder_decision_id}>
            {proc.placeholder_decision_id}
          </EntityLink>
        </Text>
      ) : null}
    </Flex>
  );
}

function DecisionPeek({ decisionId }: { decisionId: string }) {
  const { data } = useSWR<any[]>(`${OBSERVER_URL}/state/decisions`, fetcher);
  const d = data?.find((r) => r.decision_id === decisionId);
  if (!d) return <Text color="gray">Decision not found.</Text>;
  return (
    <Flex direction="column" gap="2">
      <Markdown body={`# ${d.title}\n\n${d.body || "_pending_"}`} />
      {d.affected?.length ? (
        <Text size="2" color="gray">
          affected:{" "}
          {d.affected.map((id: string, i: number) => (
            <span key={id}>
              {i > 0 ? ", " : ""}
              <EntityLink kind="pod" id={id}>{id}</EntityLink>
            </span>
          ))}
        </Text>
      ) : null}
    </Flex>
  );
}

function ProposalPeek({ proposalId }: { proposalId: string }) {
  const { data } = useSWR<any[]>(`${OBSERVER_URL}/state/proposals`, fetcher);
  const p = data?.find((r) => r.proposal_id === proposalId);
  if (!p) return <Text color="gray">Proposal not found.</Text>;
  return (
    <Flex direction="column" gap="2">
      <Text>kind: {p.kind} · strategy: {p.strategy}</Text>
      <Text><Linkified text={p.summary || ""} /></Text>
      <Text size="2" color="gray">
        proposed by{" "}
        <EntityLink kind="pod" id={p.proposer}>{p.proposer}</EntityLink>
      </Text>
      <Text size="2" color="gray">outcome: {p.outcome || "open"}</Text>
    </Flex>
  );
}

function CouncilPeek({ councilId }: { councilId: string }) {
  const { data: councils } = useSWR<any[]>(`${OBSERVER_URL}/state/councils`, fetcher);
  const { data: msgs } = useSWR<any[]>(
    `${OBSERVER_URL}/state/councils/${councilId}/messages`,
    fetcher,
  );
  const c = councils?.find((r) => r.council_id === councilId);
  if (!c) return <Text color="gray">Council not found.</Text>;
  return (
    <Flex direction="column" gap="2">
      <Text weight="bold">{c.topic}</Text>
      <Text size="2" color="gray">
        participants:{" "}
        {c.participants.map((id: string, i: number) => (
          <span key={id}>
            {i > 0 ? ", " : ""}
            <EntityLink kind="pod" id={id}>{id}</EntityLink>
          </span>
        ))}
      </Text>
      <Flex direction="column" gap="2" className="mt-2">
        {msgs?.map((m: any) => (
          <Phylactery
            key={m.seq}
            sender={m.from_pod}
            body={m.body}
            sentAt={m.sent_at}
          />
        ))}
      </Flex>
    </Flex>
  );
}
