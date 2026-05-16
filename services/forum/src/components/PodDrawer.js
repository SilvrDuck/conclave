import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import useSWR from "swr";
import { Dialog, Box, Flex, Heading, Text, Badge, Button, TextArea, TextField, Separator, Tabs, } from "@radix-ui/themes";
import { fetcher, postCommand, } from "../api";
/**
 * Side drawer for one pod. Inspects its endpoints, recent calls, gives
 * Augustus a DM box, and a charter editor (pre-loaded from disk).
 */
export function PodDrawer({ podId, onClose, }) {
    const open = podId !== null;
    return (_jsx(Dialog.Root, { open: open, onOpenChange: (o) => !o && onClose(), children: _jsx(Dialog.Content, { maxWidth: "640px", align: "start", style: { position: "fixed", right: 0, top: 0, bottom: 0, height: "100vh" }, children: podId && _jsx(PodInside, { podId: podId }) }) }));
}
function PodInside({ podId }) {
    const { data: pods } = useSWR("/state/pods", fetcher);
    const { data: endpoints } = useSWR(`/state/endpoints?pod_id=${encodeURIComponent(podId)}`, fetcher);
    const { data: calls } = useSWR("/state/calls?since_seconds=300", fetcher);
    const pod = (pods ?? []).find((p) => p.pod_id === podId);
    const inboundCalls = (calls ?? []).filter((c) => c.dst_pod === podId);
    const outboundCalls = (calls ?? []).filter((c) => c.src_pod === podId);
    return (_jsxs(Flex, { direction: "column", className: "h-full", children: [_jsxs(Box, { className: "pb-3", children: [_jsx(Heading, { size: "4", children: pod?.display_role ?? podId }), _jsxs(Flex, { gap: "2", mt: "1", children: [_jsx(Badge, { color: "gray", children: podId }), pod && (_jsxs(_Fragment, { children: [_jsx(Badge, { color: pod.admitted ? "green" : "gray", children: pod.admitted ? "admitted" : "candidate" }), _jsx(Badge, { children: pod.image_strategy }), pod.main_image && _jsx(Badge, { color: "amber", children: pod.main_image })] }))] })] }), _jsx(Separator, { size: "4", my: "2" }), _jsxs(Tabs.Root, { defaultValue: "dm", className: "flex-1 flex flex-col", children: [_jsxs(Tabs.List, { children: [_jsx(Tabs.Trigger, { value: "dm", children: "DM" }), _jsx(Tabs.Trigger, { value: "charter", children: "Charter" }), _jsx(Tabs.Trigger, { value: "endpoints", children: "Endpoints" }), _jsx(Tabs.Trigger, { value: "calls", children: "Calls" })] }), _jsxs(Box, { className: "flex-1 overflow-y-auto pt-3", children: [_jsx(Tabs.Content, { value: "dm", children: _jsx(DMTab, { podId: podId }) }), _jsx(Tabs.Content, { value: "charter", children: _jsx(CharterTab, { podId: podId }) }), _jsx(Tabs.Content, { value: "endpoints", children: _jsx(EndpointsTab, { endpoints: endpoints ?? [] }) }), _jsx(Tabs.Content, { value: "calls", children: _jsx(CallsTab, { inbound: inboundCalls, outbound: outboundCalls }) })] })] })] }));
}
function DMTab({ podId }) {
    const { data: councils } = useSWR("/state/councils", fetcher);
    const myDM = (councils ?? []).find((c) => c.private &&
        c.participants.length === 2 &&
        c.participants.includes("__augustus__") &&
        c.participants.includes(podId));
    const { data: msgs } = useSWR(myDM ? `/state/councils/${myDM.council_id}/messages` : null, fetcher, { refreshInterval: 3000 });
    const [body, setBody] = useState("");
    const [busy, setBusy] = useState(false);
    const send = async () => {
        if (!body.trim())
            return;
        setBusy(true);
        try {
            await postCommand({ kind: "SendDirectMessage", pod_id: podId, body });
            setBody("");
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs(Flex, { direction: "column", gap: "2", children: [_jsxs(Box, { className: "bg-slate-900 rounded p-3 min-h-32 max-h-72 overflow-y-auto", children: [(msgs ?? []).map((m) => (_jsxs(Box, { mb: "2", children: [_jsx(Text, { size: "1", color: "gray", children: m.from_pod }), _jsx(Text, { size: "2", className: "block whitespace-pre-wrap", children: m.body })] }, m.seq))), (msgs ?? []).length === 0 && (_jsx(Text, { size: "2", color: "gray", children: "(no messages yet)" }))] }), _jsx(TextField.Root, { value: body, onChange: (e) => setBody(e.target.value), placeholder: "Tell this pod something\u2026", onKeyDown: (e) => e.key === "Enter" && !e.shiftKey && send() }), _jsx(Button, { onClick: send, disabled: busy || !body.trim(), children: "Send" })] }));
}
function CharterTab({ podId }) {
    // Charter content lives in the pod's git workspace. The observer doesn't
    // currently expose it through an API. v1 pre-loaded from disk; v2 forum
    // shell stubs the editor — full impl pairs with the pod template branch.
    const [body, setBody] = useState("");
    const [busy, setBusy] = useState(false);
    useEffect(() => setBody(""), [podId]);
    const save = async () => {
        if (!body.trim())
            return;
        setBusy(true);
        try {
            await postCommand({ kind: "EditCharter", pod_id: podId, body });
        }
        finally {
            setBusy(false);
        }
    };
    return (_jsxs(Flex, { direction: "column", gap: "2", children: [_jsx(Text, { size: "1", color: "gray", children: "Edit this pod's charter. Empty bodies are ignored; a non-empty save bumps the charter version and wakes the agent on next turn." }), _jsx(TextArea, { rows: 12, value: body, onChange: (e) => setBody(e.target.value), placeholder: "# {pod}'s charter\\n\\n## priorities\\n..." }), _jsx(Button, { onClick: save, disabled: busy || !body.trim(), children: "Save" })] }));
}
function EndpointsTab({ endpoints }) {
    if (endpoints.length === 0)
        return _jsx(Text, { color: "gray", children: "No endpoints observed for this pod." });
    return (_jsx(Flex, { direction: "column", gap: "1", children: endpoints.map((e) => (_jsxs(Text, { size: "2", className: "font-mono", children: [_jsx("span", { className: "text-amber-400 mr-2", children: e.method }), e.path, e.annotation && _jsxs("span", { className: "text-slate-400", children: [" \u2014 ", e.annotation] })] }, `${e.method}-${e.path}`))) }));
}
function CallsTab({ inbound, outbound }) {
    return (_jsxs(Flex, { direction: "column", gap: "3", children: [_jsxs(Box, { children: [_jsx(Heading, { size: "2", mb: "1", children: "Inbound (last 5 min)" }), _jsx(CallList, { rows: inbound, side: "src_pod" })] }), _jsxs(Box, { children: [_jsx(Heading, { size: "2", mb: "1", children: "Outbound (last 5 min)" }), _jsx(CallList, { rows: outbound, side: "dst_pod" })] })] }));
}
function CallList({ rows, side }) {
    if (rows.length === 0)
        return _jsx(Text, { color: "gray", children: "(none)" });
    return (_jsx(Flex, { direction: "column", gap: "1", children: rows.slice(0, 50).map((c, i) => (_jsxs(Text, { size: "2", className: "font-mono", children: [_jsx("span", { className: "text-slate-400 mr-2", children: c[side] }), c.method, " ", c.path, " ", c.status && _jsxs("span", { className: "text-amber-400", children: ["[", c.status, "]"] })] }, i))) }));
}
