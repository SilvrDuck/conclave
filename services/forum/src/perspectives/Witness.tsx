import useSWR from "swr";
import { Box, Card, Flex, Heading, Text, Badge, Separator } from "@radix-ui/themes";
import {
  Council,
  CouncilMessage,
  Decision,
  Proclamation,
  Proposal,
  fetcher,
} from "../api";

export function Witness({ onPodClick }: { onPodClick: (pod_id: string) => void }) {
  const { data: procs } = useSWR<Proclamation[]>("/state/proclamations", fetcher);
  const { data: props } = useSWR<Proposal[]>("/state/proposals", fetcher);
  const { data: counc } = useSWR<Council[]>("/state/councils", fetcher);
  const { data: decs } = useSWR<Decision[]>("/state/decisions", fetcher);

  return (
    <Flex direction="column" gap="4" className="p-6 max-w-5xl mx-auto">
      <Section title="Proclamations">
        {(procs ?? []).length === 0 ? (
          <Empty />
        ) : (
          (procs ?? []).map((p) => (
            <Card key={p.seq} className="mb-2">
              <Flex justify="between" align="center">
                <Heading size="3">№ {p.seq}</Heading>
                <Badge color={p.status === "open" ? "blue" : "green"}>{p.status}</Badge>
              </Flex>
              <Text size="3" className="block mt-1">
                {p.text}
              </Text>
              <Text size="1" color="gray">
                {new Date(p.issued_at).toLocaleString()}
              </Text>
            </Card>
          ))
        )}
      </Section>

      <Section title="Senate">
        {(props ?? []).length === 0 ? (
          <Empty />
        ) : (
          (props ?? []).map((p) => (
            <ProposalCard key={p.proposal_id} p={p} onPodClick={onPodClick} />
          ))
        )}
      </Section>

      <Section title="Councils">
        {(counc ?? []).length === 0 ? (
          <Empty />
        ) : (
          (counc ?? []).map((c) => <CouncilCard key={c.council_id} c={c} onPodClick={onPodClick} />)
        )}
      </Section>

      <Section title="Decisions">
        {(decs ?? []).length === 0 ? (
          <Empty />
        ) : (
          (decs ?? []).map((d) => (
            <Card key={d.decision_id} className="mb-2">
              <Flex justify="between" align="center">
                <Text size="3" weight="bold">
                  {d.title}
                </Text>
                <Badge color={d.status === "sealed" ? "green" : "gray"}>{d.status}</Badge>
              </Flex>
              {d.body && (
                <Text size="2" className="block mt-1 whitespace-pre-wrap">
                  {d.body}
                </Text>
              )}
              <Text size="1" color="gray">
                {d.origin.kind}:{d.origin.id} ·{" "}
                {d.affected.length > 0 ? `affects ${d.affected.join(", ")}` : "—"}
              </Text>
            </Card>
          ))
        )}
      </Section>
    </Flex>
  );
}

function ProposalCard({
  p,
  onPodClick,
}: {
  p: Proposal;
  onPodClick: (id: string) => void;
}) {
  const yesCount = p.ballots.filter((b) => b.choice === "yes").length;
  const noCount = p.ballots.filter((b) => b.choice === "no").length;
  const remaining = Math.max(0, p.eligible_voters.length - p.ballots.length);
  const deadline = new Date(p.deadline);
  return (
    <Card className="mb-2">
      <Flex justify="between" align="center">
        <Flex gap="2" align="center">
          <Badge color="blue">{p.kind}</Badge>
          <Badge color="violet">{p.strategy}</Badge>
          <Badge color={outcomeColor(p.outcome)}>{p.outcome}</Badge>
        </Flex>
        <Text size="1" color="gray">
          {p.outcome === "open" ? `closes ${deadline.toLocaleTimeString()}` : ""}
        </Text>
      </Flex>
      <Text size="3" weight="bold" className="block mt-1">
        {p.summary}
      </Text>
      <Text size="1" color="gray">
        proposed by{" "}
        <button className="underline" onClick={() => onPodClick(p.proposer)}>
          {p.proposer}
        </button>
        {" · "}
        eligible: {p.eligible_voters.length}
      </Text>
      <Separator size="4" my="2" />
      <Flex gap="2" wrap="wrap" align="center">
        {p.eligible_voters.map((v) => {
          const b = p.ballots.find((b) => b.voter === v);
          return (
            <Badge
              key={v}
              color={b?.choice === "yes" ? "green" : b?.choice === "no" ? "red" : "gray"}
            >
              {v} {b ? `· ${b.choice}` : "· pending"}
            </Badge>
          );
        })}
      </Flex>
      <Text size="1" color="gray">
        tally: {yesCount} yes · {noCount} no · {remaining} pending
      </Text>
    </Card>
  );
}

function CouncilCard({
  c,
  onPodClick,
}: {
  c: Council;
  onPodClick: (id: string) => void;
}) {
  // Live updates come through SSE's MessagePosted handler; no client poll
  // (avoid an N-councils × 4s poll storm).
  const { data: msgs } = useSWR<CouncilMessage[]>(
    `/state/councils/${c.council_id}/messages`,
    fetcher,
  );
  return (
    <Card className="mb-2">
      <Flex justify="between" align="center">
        <Flex gap="2" align="center">
          <Badge color={c.status === "open" ? "blue" : "gray"}>{c.status}</Badge>
          {c.private && <Badge color="purple">DM</Badge>}
          {c.needs_augustus && <Badge color="orange">needs Augustus</Badge>}
        </Flex>
        <Text size="1" color="gray">
          {new Date(c.opened_at).toLocaleString()}
        </Text>
      </Flex>
      <Text size="3" weight="bold" className="block mt-1">
        {c.topic}
      </Text>
      <Flex gap="2" wrap="wrap" mt="1">
        {c.participants.map((pp) => (
          <button
            key={pp}
            className="text-xs underline text-slate-300"
            onClick={() => pp !== "__augustus__" && onPodClick(pp)}
          >
            {pp}
          </button>
        ))}
      </Flex>
      <Separator size="4" my="2" />
      <Flex direction="column" gap="1">
        {(msgs ?? []).map((m) => (
          <Box key={m.seq}>
            <Text size="2">
              <span className="font-semibold">{m.from_pod}:</span> {m.body}
            </Text>
          </Box>
        ))}
        {(msgs ?? []).length === 0 && (
          <Text size="1" color="gray">
            (no messages yet)
          </Text>
        )}
      </Flex>
      {c.summary && (
        <>
          <Separator size="4" my="2" />
          <Text size="2" color="gray">
            <strong>Summary:</strong> {c.summary}
          </Text>
        </>
      )}
    </Card>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box>
      <Heading size="4" mb="2">
        {title}
      </Heading>
      {children}
    </Box>
  );
}

function Empty() {
  return (
    <Text size="2" color="gray">
      (none yet)
    </Text>
  );
}

function outcomeColor(o: Proposal["outcome"]): "green" | "red" | "gray" | "blue" {
  switch (o) {
    case "approved":
      return "green";
    case "rejected":
    case "expired":
      return "red";
    case "open":
      return "blue";
    default:
      return "gray";
  }
}
