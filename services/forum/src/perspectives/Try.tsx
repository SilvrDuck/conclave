import useSWR from "swr";
import { Box, Button, Card, Flex, Heading, Text } from "@radix-ui/themes";
import { EndpointRow, Pod, fetcher } from "../api";

/** "Apps" perspective: every admitted pod that has at least one endpoint
 * gets a one-click open into its `.conclave.local` hostname. */
export function Try() {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher);
  const { data: endpoints } = useSWR<EndpointRow[]>("/state/endpoints", fetcher);

  const apps = (pods ?? []).filter((p) => p.admitted);
  const epByPod = new Map<string, EndpointRow[]>();
  for (const e of endpoints ?? []) {
    if (!epByPod.has(e.pod_id)) epByPod.set(e.pod_id, []);
    epByPod.get(e.pod_id)!.push(e);
  }

  return (
    <Box className="p-6 max-w-5xl mx-auto">
      <Heading size="4" mb="3">
        Try what they built
      </Heading>
      {apps.length === 0 ? (
        <Text color="gray">No admitted pods yet.</Text>
      ) : (
        <Flex direction="column" gap="3">
          {apps.map((p) => {
            const eps = epByPod.get(p.pod_id) ?? [];
            const url = p.public_url ?? `http://${p.display_role}.conclave.local`;
            return (
              <Card key={p.pod_id}>
                <Flex justify="between" align="center">
                  <Box>
                    <Heading size="3">{p.display_role}</Heading>
                    <Text size="2" color="gray">
                      {p.image_strategy}
                      {p.main_image ? ` • ${p.main_image}` : ""}
                    </Text>
                  </Box>
                  <Button asChild variant="solid">
                    <a href={url} target="_blank" rel="noreferrer">
                      Open
                    </a>
                  </Button>
                </Flex>
                {eps.length > 0 && (
                  <Box mt="2">
                    <Text size="1" color="gray">
                      endpoints:
                    </Text>
                    <Flex direction="column" gap="1" mt="1">
                      {eps.slice(0, 12).map((e) => (
                        <Text size="2" key={`${e.method}-${e.path}`}>
                          <span className="font-mono text-amber-400 mr-2">{e.method}</span>
                          <span className="font-mono">{e.path}</span>
                          {e.annotation && (
                            <span className="text-slate-400"> — {e.annotation}</span>
                          )}
                        </Text>
                      ))}
                    </Flex>
                  </Box>
                )}
              </Card>
            );
          })}
        </Flex>
      )}
    </Box>
  );
}
