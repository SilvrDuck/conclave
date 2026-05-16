import { useState } from "react";
import useSWR, { mutate } from "swr";
import { Box, Button, Card, Flex, Heading, Text, Badge } from "@radix-ui/themes";
import { InboxBallot, InboxItem, Pod, fetcher, postCommand } from "../api";

const AUGUSTUS = "__augustus__";

/** Direct perspective: inbox of things that need Augustus + a pod list
 * for picking one to interact with. The DM / charter editor / token-stream
 * UI lives in the per-pod drawer (PodDrawer) opened on click. */
export function Direct({ onPodClick }: { onPodClick: (pod_id: string) => void }) {
  const { data: inbox } = useSWR<InboxItem[]>("/inbox", fetcher, { refreshInterval: 5000 });
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher);

  return (
    <Flex direction="column" gap="4" className="p-6 max-w-5xl mx-auto">
      <Box>
        <Heading size="4" mb="2">
          Inbox
        </Heading>
        {(inbox ?? []).length === 0 ? (
          <Text size="2" color="gray">
            (nothing needs you)
          </Text>
        ) : (
          <Flex direction="column" gap="2">
            {(inbox ?? []).map((item) => (
              <InboxRow key={inboxKey(item)} item={item} onPodClick={onPodClick} />
            ))}
          </Flex>
        )}
      </Box>

      <Box>
        <Heading size="4" mb="2">
          Pods
        </Heading>
        <Flex direction="column" gap="2">
          {(pods ?? []).map((p) => (
            <Card
              key={p.pod_id}
              className="cursor-pointer hover:bg-slate-800"
              onClick={() => onPodClick(p.pod_id)}
            >
              <Flex justify="between" align="center">
                <Box>
                  <Text size="3" weight="bold">
                    {p.display_role}
                  </Text>
                  <Text size="1" color="gray">
                    {p.pod_id} · {p.image_strategy}
                  </Text>
                </Box>
                <Flex gap="2">
                  <Badge color={p.admitted ? "green" : "gray"}>
                    {p.admitted ? "admitted" : "candidate"}
                  </Badge>
                  <Badge color={p.runtime_status === "running" ? "green" : "red"}>
                    {p.runtime_status}
                  </Badge>
                  <Badge color={p.agent_state === "stuck" ? "red" : "blue"}>
                    {p.agent_state}
                  </Badge>
                </Flex>
              </Flex>
            </Card>
          ))}
        </Flex>
      </Box>
    </Flex>
  );
}

function inboxKey(item: InboxItem): string {
  switch (item.kind) {
    case "ballot":
      return `ballot:${item.proposal_id}`;
    case "stuck":
      return `stuck:${item.pod_id}`;
    case "council":
      return `council:${item.council_id}`;
  }
}

function InboxRow({
  item,
  onPodClick,
}: {
  item: InboxItem;
  onPodClick: (id: string) => void;
}) {
  switch (item.kind) {
    case "ballot":
      return <BallotRow item={item} />;
    case "stuck":
      return (
        <Card
          onClick={() => onPodClick(item.pod_id)}
          className="cursor-pointer hover:bg-slate-800"
        >
          <Badge color="red">stuck</Badge>
          <Text size="3" weight="bold" className="block mt-1">
            {item.display_role}
          </Text>
        </Card>
      );
    case "council":
      return (
        <Card>
          <Badge color="orange">council</Badge>
          <Text size="3" weight="bold" className="block mt-1">
            {item.topic}
          </Text>
          <Text size="1" color="gray">
            {item.participants.join(" ↔ ")}
          </Text>
        </Card>
      );
  }
}

function BallotRow({ item }: { item: InboxBallot }) {
  const [busy, setBusy] = useState<null | "yes" | "no" | "abstain">(null);
  const [err, setErr] = useState<string | null>(null);
  const cast = async (choice: "yes" | "no" | "abstain") => {
    setBusy(choice);
    setErr(null);
    try {
      await postCommand({
        kind: "CastBallot",
        proposal_id: item.proposal_id,
        voter: AUGUSTUS,
        choice,
      });
      await mutate("/inbox");
      await mutate("/state/proposals");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(null);
    }
  };
  return (
    <Card>
      <Flex justify="between" align="center">
        <Badge color="violet">ballot · {item.strategy}</Badge>
        <Text size="1" color="gray">
          closes {new Date(item.deadline).toLocaleTimeString()}
        </Text>
      </Flex>
      <Text size="3" weight="bold" className="block mt-1">
        {item.summary}
      </Text>
      <Flex gap="2" mt="2">
        <Button
          color="green"
          variant="solid"
          disabled={busy !== null}
          loading={busy === "yes"}
          onClick={() => cast("yes")}
        >
          Yes
        </Button>
        <Button
          color="red"
          variant="solid"
          disabled={busy !== null}
          loading={busy === "no"}
          onClick={() => cast("no")}
        >
          No
        </Button>
        <Button
          variant="soft"
          disabled={busy !== null}
          loading={busy === "abstain"}
          onClick={() => cast("abstain")}
        >
          Abstain
        </Button>
        {err && (
          <Text size="2" color="red">
            {err}
          </Text>
        )}
      </Flex>
    </Card>
  );
}
