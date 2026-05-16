import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import useSWR from "swr";
import { Box, Button, Card, Flex, Heading, Text } from "@radix-ui/themes";
import { fetcher } from "../api";
/** "Apps" perspective: every admitted pod that has at least one endpoint
 * gets a one-click open into its `.conclave.local` hostname. */
export function Try() {
    const { data: pods } = useSWR("/state/pods", fetcher);
    const { data: endpoints } = useSWR("/state/endpoints", fetcher);
    const apps = (pods ?? []).filter((p) => p.admitted);
    const epByPod = new Map();
    for (const e of endpoints ?? []) {
        if (!epByPod.has(e.pod_id))
            epByPod.set(e.pod_id, []);
        epByPod.get(e.pod_id).push(e);
    }
    return (_jsxs(Box, { className: "p-6 max-w-5xl mx-auto", children: [_jsx(Heading, { size: "4", mb: "3", children: "Try what they built" }), apps.length === 0 ? (_jsx(Text, { color: "gray", children: "No admitted pods yet." })) : (_jsx(Flex, { direction: "column", gap: "3", children: apps.map((p) => {
                    const eps = epByPod.get(p.pod_id) ?? [];
                    const url = p.public_url ?? `http://${p.display_role}.conclave.local`;
                    return (_jsxs(Card, { children: [_jsxs(Flex, { justify: "between", align: "center", children: [_jsxs(Box, { children: [_jsx(Heading, { size: "3", children: p.display_role }), _jsxs(Text, { size: "2", color: "gray", children: [p.image_strategy, p.main_image ? ` • ${p.main_image}` : ""] })] }), _jsx(Button, { asChild: true, variant: "solid", children: _jsx("a", { href: url, target: "_blank", rel: "noreferrer", children: "Open" }) })] }), eps.length > 0 && (_jsxs(Box, { mt: "2", children: [_jsx(Text, { size: "1", color: "gray", children: "endpoints:" }), _jsx(Flex, { direction: "column", gap: "1", mt: "1", children: eps.slice(0, 12).map((e) => (_jsxs(Text, { size: "2", children: [_jsx("span", { className: "font-mono text-amber-400 mr-2", children: e.method }), _jsx("span", { className: "font-mono", children: e.path }), e.annotation && (_jsxs("span", { className: "text-slate-400", children: [" \u2014 ", e.annotation] }))] }, `${e.method}-${e.path}`))) })] }))] }, p.pod_id));
                }) }))] }));
}
