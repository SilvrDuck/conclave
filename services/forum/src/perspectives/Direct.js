import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import useSWR from "swr";
import { Box, Card, Flex, Heading, Text, Badge } from "@radix-ui/themes";
import { fetcher } from "../api";
/** Direct perspective: inbox of things that need Augustus + a pod list
 * for picking one to interact with. The DM / charter editor / token-stream
 * UI lives in the per-pod drawer (PodDrawer) opened on click. */
export function Direct({ onPodClick }) {
    const { data: inbox } = useSWR("/inbox", fetcher, { refreshInterval: 5000 });
    const { data: pods } = useSWR("/state/pods", fetcher);
    return (_jsxs(Flex, { direction: "column", gap: "4", className: "p-6 max-w-5xl mx-auto", children: [_jsxs(Box, { children: [_jsx(Heading, { size: "4", mb: "2", children: "Inbox" }), (inbox ?? []).length === 0 ? (_jsx(Text, { size: "2", color: "gray", children: "(nothing needs you)" })) : (_jsx(Flex, { direction: "column", gap: "2", children: (inbox ?? []).map((item, i) => (_jsx(InboxRow, { item: item, onPodClick: onPodClick }, i))) }))] }), _jsxs(Box, { children: [_jsx(Heading, { size: "4", mb: "2", children: "Pods" }), _jsx(Flex, { direction: "column", gap: "2", children: (pods ?? []).map((p) => (_jsx(Card, { className: "cursor-pointer hover:bg-slate-800", onClick: () => onPodClick(p.pod_id), children: _jsxs(Flex, { justify: "between", align: "center", children: [_jsxs(Box, { children: [_jsx(Text, { size: "3", weight: "bold", children: p.display_role }), _jsxs(Text, { size: "1", color: "gray", children: [p.pod_id, " \u00B7 ", p.image_strategy] })] }), _jsxs(Flex, { gap: "2", children: [_jsx(Badge, { color: p.admitted ? "green" : "gray", children: p.admitted ? "admitted" : "candidate" }), _jsx(Badge, { color: p.runtime_status === "running" ? "green" : "red", children: p.runtime_status }), _jsx(Badge, { color: p.agent_state === "stuck" ? "red" : "blue", children: p.agent_state })] })] }) }, p.pod_id))) })] })] }));
}
function InboxRow({ item, onPodClick, }) {
    switch (item.kind) {
        case "ballot":
            return (_jsxs(Card, { children: [_jsxs(Badge, { color: "violet", children: ["ballot \u00B7 ", item.strategy] }), _jsx(Text, { size: "3", weight: "bold", className: "block mt-1", children: item.summary }), _jsxs(Text, { size: "1", color: "gray", children: ["closes ", new Date(item.deadline).toLocaleTimeString()] })] }));
        case "stuck":
            return (_jsxs(Card, { onClick: () => onPodClick(item.pod_id), className: "cursor-pointer hover:bg-slate-800", children: [_jsx(Badge, { color: "red", children: "stuck" }), _jsx(Text, { size: "3", weight: "bold", className: "block mt-1", children: item.display_role })] }));
        case "council":
            return (_jsxs(Card, { children: [_jsx(Badge, { color: "orange", children: "council" }), _jsx(Text, { size: "3", weight: "bold", className: "block mt-1", children: item.topic }), _jsx(Text, { size: "1", color: "gray", children: item.participants.join(" ↔ ") })] }));
    }
}
