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
import { Markdown } from "../components/Markdown";
import { Linkified } from "../components/Linkified";
import { Phylactery } from "../components/Phylactery";
import { EntityLink } from "../components/EntityLink";

/** Witness: epoch cards grouped by proclamation. Each proclamation
 * is a chapter; everything emitted while it was the current top of
 * the operator's pile belongs to its epoch. Older proclamations are
 * older chapters. Items issued before any proclamation land in a
 * "Background activity" bucket. */
export function Witness({ onPodClick: _ }: { onPodClick: (pod_id: string) => void }) {
  const { data: procs } = useSWR<Proclamation[]>("/state/proclamations", fetcher);
  const { data: props } = useSWR<Proposal[]>("/state/proposals", fetcher);
  const { data: counc } = useSWR<Council[]>("/state/councils", fetcher);
  const { data: decs } = useSWR<Decision[]>("/state/decisions", fetcher);

  if (!procs || !props || !counc || !decs) {
    return <Text className="p-6" color="gray">loading…</Text>;
  }

  if (procs.length === 0) {
    return (
      <Flex className="p-6" direction="column" gap="2" align="center">
        <Text size="3" color="gray">No proclamations yet.</Text>
        <Text size="2" color="gray">Issue one above to open the senate.</Text>
      </Flex>
    );
  }

  // Sort proclamations newest first (seq desc). For each, compute
  // [openedAt, nextProclamationOpenedAt) and bucket items.
  const sorted = [...procs].sort((a, b) => b.seq - a.seq);
  const epochs = sorted.map((p, i) => {
    const opened = new Date(p.issued_at);
    const nextOpened = i === 0 ? null : new Date(sorted[i - 1].issued_at);
    return { proclamation: p, opened, nextOpened };
  });

  const itemsForEpoch = <T extends { created_at?: string; opened_at?: string }>(
    items: T[],
    opened: Date,
    nextOpened: Date | null,
  ) =>
    items.filter((it) => {
      const ts = new Date(it.created_at ?? it.opened_at ?? "");
      if (Number.isNaN(ts.getTime())) return false;
      if (ts < opened) return false;
      if (nextOpened && ts >= nextOpened) return false;
      return true;
    });

  return (
    <Flex direction="column" gap="6" className="p-6 max-w-5xl mx-auto">
      {epochs.map((e, idx) => {
        const epochProps = itemsForEpoch(props, e.opened, e.nextOpened);
        const epochCounc = itemsForEpoch(counc, e.opened, e.nextOpened);
        const epochDecs = itemsForEpoch(decs, e.opened, e.nextOpened);
        return (
          <EpochCard
            key={e.proclamation.seq}
            proclamation={e.proclamation}
            isCurrent={idx === 0}
            proposals={epochProps}
            councils={epochCounc}
            decisions={epochDecs}
          />
        );
      })}
    </Flex>
  );
}

function EpochCard({
  proclamation,
  isCurrent,
  proposals,
  councils,
  decisions,
}: {
  proclamation: Proclamation;
  isCurrent: boolean;
  proposals: Proposal[];
  councils: Council[];
  decisions: Decision[];
}) {
  return (
    <Card className="manuscript">
      <Flex justify="between" align="baseline" mb="2">
        <Flex align="baseline" gap="3">
          <span className="manuscript-numeral text-3xl">{toRoman(proclamation.seq)}</span>
          <Badge color={proclamation.status === "open" ? "blue" : "green"}>
            {proclamation.status}
          </Badge>
          {isCurrent ? <Badge color="amber">current</Badge> : null}
        </Flex>
        <Text size="1" style={{ color: "var(--conclave-ink-dim)" }}>
          {new Date(proclamation.issued_at).toLocaleString()}
        </Text>
      </Flex>
      <Markdown body={proclamation.text} manuscript={false} />

      {decisions.length > 0 ? (
        <EpochSection title="Decisions">
          {decisions.map((d) => (
            <DecisionRow key={d.decision_id} d={d} />
          ))}
        </EpochSection>
      ) : null}

      {councils.length > 0 ? (
        <EpochSection title="Councils">
          {councils.map((c) => (
            <CouncilCard key={c.council_id} c={c} />
          ))}
        </EpochSection>
      ) : null}

      {proposals.length > 0 ? (
        <EpochSection title="Senate proposals">
          {proposals.map((p) => (
            <ProposalCard key={p.proposal_id} p={p} />
          ))}
        </EpochSection>
      ) : null}

      {!decisions.length && !councils.length && !proposals.length ? (
        <Text size="2" style={{ color: "var(--conclave-ink-dim)" }}>
          (the swarm hasn't responded yet)
        </Text>
      ) : null}
    </Card>
  );
}

function EpochSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Box mt="3">
      <Heading size="2" className="rubric">{title}</Heading>
      <Box mt="2">{children}</Box>
    </Box>
  );
}

function DecisionRow({ d }: { d: Decision }) {
  return (
    <Box className="mb-2">
      <Flex justify="between" align="baseline">
        <Text size="2" weight="bold">
          <EntityLink kind="decision" id={d.decision_id}>{d.title}</EntityLink>
        </Text>
        <Badge color={d.status === "sealed" ? "green" : "gray"}>{d.status}</Badge>
      </Flex>
      {d.body ? (
        <Box className="mt-1">
          <Markdown body={d.body} manuscript={false} />
        </Box>
      ) : null}
      {d.affected.length > 0 ? (
        <Text size="1" style={{ color: "var(--conclave-ink-dim)" }}>
          affects:{" "}
          {d.affected.map((id, i) => (
            <span key={id}>
              {i > 0 ? ", " : ""}
              <EntityLink kind="pod" id={id}>{id}</EntityLink>
            </span>
          ))}
        </Text>
      ) : null}
    </Box>
  );
}

function ProposalCard({ p }: { p: Proposal }) {
  return (
    <Box className="mb-2 border-l-2 pl-3" style={{ borderColor: "var(--conclave-margin)" }}>
      <Flex gap="2" align="baseline" wrap="wrap">
        <Badge color="blue">{p.kind}</Badge>
        <Badge color="violet">{p.strategy}</Badge>
        <Badge color={outcomeColor(p.outcome)}>{p.outcome}</Badge>
        <Text size="2" weight="bold">
          <EntityLink kind="proposal" id={p.proposal_id}>{p.summary}</EntityLink>
        </Text>
      </Flex>
      <Text size="1" style={{ color: "var(--conclave-ink-dim)" }}>
        proposed by <EntityLink kind="pod" id={p.proposer}>{p.proposer}</EntityLink>
        {" · "}{p.eligible_voters.length} eligible
      </Text>
      <Flex gap="2" wrap="wrap" mt="1">
        {p.eligible_voters.map((v) => {
          const b = p.ballots.find((bb) => bb.voter === v);
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
    </Box>
  );
}

function CouncilCard({ c }: { c: Council }) {
  const { data: msgs } = useSWR<CouncilMessage[]>(
    `/state/councils/${c.council_id}/messages`,
    fetcher,
  );
  return (
    <Box className="mb-3 border-l-2 pl-3" style={{ borderColor: "var(--conclave-margin)" }}>
      <Flex justify="between" align="center">
        <Flex gap="2" align="baseline" wrap="wrap">
          <Badge color={c.status === "open" ? "blue" : "gray"}>{c.status}</Badge>
          {c.private && <Badge color="purple">DM</Badge>}
          {c.needs_augustus && <Badge color="orange">needs Augustus</Badge>}
          <Text size="2" weight="bold">
            <EntityLink kind="council" id={c.council_id}>{c.topic}</EntityLink>
          </Text>
        </Flex>
        <Text size="1" style={{ color: "var(--conclave-ink-dim)" }}>
          {new Date(c.opened_at).toLocaleTimeString()}
        </Text>
      </Flex>
      <Text size="1" mt="1">
        {c.participants.map((pp, i) => (
          <span key={pp}>
            {i > 0 ? ", " : ""}
            {pp === "__augustus__" ? (
              <span style={{ color: "var(--conclave-rubric)" }}>Augustus</span>
            ) : (
              <EntityLink kind="pod" id={pp}>{pp}</EntityLink>
            )}
          </span>
        ))}
      </Text>
      <Flex direction="column" gap="2" mt="2">
        {(msgs ?? []).map((m) => (
          <Phylactery
            key={m.seq}
            sender={m.from_pod}
            body={m.body}
            sentAt={m.sent_at}
          />
        ))}
        {(msgs ?? []).length === 0 && (
          <Text size="1" style={{ color: "var(--conclave-ink-dim)" }}>
            (no messages yet)
          </Text>
        )}
      </Flex>
      {c.summary ? (
        <>
          <Separator size="4" my="2" />
          <Text size="2">
            <strong>Summary:</strong> <Linkified text={c.summary} />
          </Text>
        </>
      ) : null}
    </Box>
  );
}

function toRoman(n: number): string {
  if (n <= 0) return String(n);
  const numerals: [number, string][] = [
    [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"],
    [100, "C"], [90, "XC"], [50, "L"], [40, "XL"],
    [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
  ];
  let out = "";
  let r = n;
  for (const [v, s] of numerals) {
    while (r >= v) {
      out += s;
      r -= v;
    }
  }
  return out;
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
