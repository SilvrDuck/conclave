import { useState } from "react";
import { Box, Flex, Heading, Tabs, Text } from "@radix-ui/themes";
import { Glance } from "./perspectives/Glance";
import { Witness } from "./perspectives/Witness";
import { Try } from "./perspectives/Try";
import { Direct } from "./perspectives/Direct";
import { ProclamationField } from "./components/ProclamationField";
import { useDomainStream } from "./sse";
import { PodDrawer } from "./components/PodDrawer";

export default function App() {
  useDomainStream();
  const [openPod, setOpenPod] = useState<string | null>(null);

  return (
    <Flex direction="column" className="h-screen">
      <header className="border-b border-slate-700 px-6 py-3 flex items-center justify-between">
        <Heading size="5">conclave / forum</Heading>
        <Text size="2" color="gray">
          watching the senate think
        </Text>
      </header>

      <Box className="px-6 py-3 border-b border-slate-800">
        <ProclamationField />
      </Box>

      <Tabs.Root defaultValue="glance" className="flex-1 flex flex-col">
        <Tabs.List className="px-6">
          <Tabs.Trigger value="glance">Glance</Tabs.Trigger>
          <Tabs.Trigger value="witness">Witness</Tabs.Trigger>
          <Tabs.Trigger value="try">Try</Tabs.Trigger>
          <Tabs.Trigger value="direct">Direct</Tabs.Trigger>
        </Tabs.List>

        <Box className="flex-1 overflow-hidden">
          <Tabs.Content value="glance" className="h-full">
            <Glance onPodClick={setOpenPod} />
          </Tabs.Content>
          <Tabs.Content value="witness" className="h-full overflow-y-auto">
            <Witness onPodClick={setOpenPod} />
          </Tabs.Content>
          <Tabs.Content value="try" className="h-full overflow-y-auto">
            <Try />
          </Tabs.Content>
          <Tabs.Content value="direct" className="h-full overflow-y-auto">
            <Direct onPodClick={setOpenPod} />
          </Tabs.Content>
        </Box>
      </Tabs.Root>

      <PodDrawer podId={openPod} onClose={() => setOpenPod(null)} />
    </Flex>
  );
}
