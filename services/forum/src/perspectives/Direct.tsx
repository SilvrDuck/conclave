import useSWR from "swr";
import { Box, Card, Flex, Heading, Text, Badge } from "@radix-ui/themes";
import { InboxItem, Pod, fetcher } from "../api";

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
            {(inbox ?? []).map((item, i) => (
              <InboxRow key={i} item={item} onPodClick={onPodClick} />
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

function InboxRow({
  item,
  onPodClick,
}: {
  item: InboxItem;
  onPodClick: (id: string) => void;
}) {
  switch (item.kind) {
    case "ballot":
      return (
        <Card>
          <Badge color="violet">ballot · {item.strategy}</Badge>
          <Text size="3" weight="bold" className="block mt-1">
            {item.summary}
          </Text>
          <Text size="1" color="gray">
            closes {new Date(item.deadline).toLocaleTimeString()}
          </Text>
        </Card>
      );
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
