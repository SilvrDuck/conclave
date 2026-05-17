import * as Dialog from "@radix-ui/react-dialog";
import { Cross1Icon } from "@radix-ui/react-icons";
import { Box, Flex, IconButton, Text } from "@radix-ui/themes";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { fetcher } from "../api";
import { Markdown } from "./Markdown";

const ABOUT_BODY = `# About this conclave

You are looking at the **Forum** — the architect's window into a
swarm of autonomous AI agents that coordinate via a senate, council,
and decisions ledger.

## The four perspectives

- **Glance** — live architecture graph. Pods are services; edges
  are real OpenTelemetry HTTP calls.
- **Witness** — proclamations, decisions, council threads. The
  archive of what the senate decided and why.
- **Try** — open the deployed apps. Each pod with a public
  endpoint shows up here.
- **Direct** — talk to a specific pod (DM, charter, ballots).

## How it works

The architect issues a **proclamation** (a feature mandate). The
platform spawns the first pod; the agent reads the proclamation and
*proposes its own admission* through the senate. From there, the
swarm grows organically — every cross-cutting decision goes through
a vote or a council.

The full spec lives under \`spec/\` — open it from the header bar.
`;

type SpecPage = {
  filename: string;
  body: string;
};

const SPEC_PAGES = [
  "00-vision.md",
  "01-jtbd.md",
  "02-event-storming.md",
  "03-prototype-audit.md",
  "04-wardley.md",
  "05-ddd-contexts.md",
  "06-atam.md",
  "07-c4.md",
  "08-v2-acceptance.md",
];

export function AboutDialog() {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button className="text-sm text-amber-400 hover:text-amber-300 underline-offset-2 hover:underline">
          About
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[640px] max-h-[80vh] bg-slate-900 border border-slate-700 rounded-md z-50 overflow-y-auto"
          aria-describedby={undefined}
        >
          <Flex justify="between" align="center" className="px-4 py-3 border-b border-slate-700">
            <Dialog.Title asChild>
              <Text size="3" weight="bold">About this conclave</Text>
            </Dialog.Title>
            <Dialog.Close asChild>
              <IconButton variant="ghost" aria-label="close">
                <Cross1Icon />
              </IconButton>
            </Dialog.Close>
          </Flex>
          <Box className="p-4">
            <Markdown body={ABOUT_BODY} />
          </Box>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function SpecDialog() {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string>("00-vision.md");
  // Listen for the cross-component event Linkified fires when a
  // user clicks `spec/00-vision.md` in authored text. Centralising
  // the spec viewer here means Linkified doesn't need to thread
  // open-state through the component tree.
  useEffect(() => {
    const onOpenSpec = (e: Event) => {
      const fname = (e as CustomEvent).detail;
      if (typeof fname === "string") {
        setSelected(fname);
        setOpen(true);
      }
    };
    window.addEventListener("conclave:open-spec", onOpenSpec);
    return () => window.removeEventListener("conclave:open-spec", onOpenSpec);
  }, []);
  const { data } = useSWR<SpecPage | { detail: string }>(
    open ? `/state/spec/${selected}` : null,
    fetcher,
  );
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <button className="text-sm text-amber-400 hover:text-amber-300 underline-offset-2 hover:underline">
          Spec
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[80vw] h-[80vh] bg-slate-900 border border-slate-700 rounded-md z-50 overflow-hidden flex flex-col"
          aria-describedby={undefined}
        >
          <Flex justify="between" align="center" className="px-4 py-3 border-b border-slate-700">
            <Dialog.Title asChild>
              <Text size="3" weight="bold">Spec</Text>
            </Dialog.Title>
            <Dialog.Close asChild>
              <IconButton variant="ghost" aria-label="close">
                <Cross1Icon />
              </IconButton>
            </Dialog.Close>
          </Flex>
          <Flex className="flex-1 overflow-hidden">
            <Box className="w-56 border-r border-slate-700 overflow-y-auto py-2">
              {SPEC_PAGES.map((p) => (
                <button
                  key={p}
                  onClick={() => setSelected(p)}
                  className={`block w-full text-left px-3 py-1.5 text-sm ${
                    selected === p ? "bg-slate-800 text-amber-300" : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {p.replace(/\.md$/, "")}
                </button>
              ))}
            </Box>
            <Box className="flex-1 overflow-y-auto p-4">
              {data && "body" in data ? (
                <Markdown body={data.body} />
              ) : (
                <Text color="gray">{data ? "not found" : "loading…"}</Text>
              )}
            </Box>
          </Flex>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
