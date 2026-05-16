import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import useSWR from "swr";
import { Box, Card, Flex, Heading, Text, Badge, Separator } from "@radix-ui/themes";
import { fetcher, } from "../api";
export function Witness({ onPodClick }) {
    const { data: procs } = useSWR("/state/proclamations", fetcher);
    const { data: props } = useSWR("/state/proposals", fetcher);
    const { data: counc } = useSWR("/state/councils", fetcher);
    const { data: decs } = useSWR("/state/decisions", fetcher);
    return (_jsxs(Flex, { direction: "column", gap: "4", className: "p-6 max-w-5xl mx-auto", children: [_jsx(Section, { title: "Proclamations", children: (procs ?? []).length === 0 ? (_jsx(Empty, {})) : ((procs ?? []).map((p) => (_jsxs(Card, { className: "mb-2", children: [_jsxs(Flex, { justify: "between", align: "center", children: [_jsxs(Heading, { size: "3", children: ["\u2116 ", p.seq] }), _jsx(Badge, { color: p.status === "open" ? "blue" : "green", children: p.status })] }), _jsx(Text, { size: "3", className: "block mt-1", children: p.text }), _jsx(Text, { size: "1", color: "gray", children: new Date(p.issued_at).toLocaleString() })] }, p.seq)))) }), _jsx(Section, { title: "Senate", children: (props ?? []).length === 0 ? (_jsx(Empty, {})) : ((props ?? []).map((p) => (_jsx(ProposalCard, { p: p, onPodClick: onPodClick }, p.proposal_id)))) }), _jsx(Section, { title: "Councils", children: (counc ?? []).length === 0 ? (_jsx(Empty, {})) : ((counc ?? []).map((c) => _jsx(CouncilCard, { c: c, onPodClick: onPodClick }, c.council_id))) }), _jsx(Section, { title: "Decisions", children: (decs ?? []).length === 0 ? (_jsx(Empty, {})) : ((decs ?? []).map((d) => (_jsxs(Card, { className: "mb-2", children: [_jsxs(Flex, { justify: "between", align: "center", children: [_jsx(Text, { size: "3", weight: "bold", children: d.title }), _jsx(Badge, { color: d.status === "sealed" ? "green" : "gray", children: d.status })] }), d.body && (_jsx(Text, { size: "2", className: "block mt-1 whitespace-pre-wrap", children: d.body })), _jsxs(Text, { size: "1", color: "gray", children: [d.origin.kind, ":", d.origin.id, " \u00B7", " ", d.affected.length > 0 ? `affects ${d.affected.join(", ")}` : "—"] })] }, d.decision_id)))) })] }));
}
function ProposalCard({ p, onPodClick, }) {
    const yesCount = p.ballots.filter((b) => b.choice === "yes").length;
    const noCount = p.ballots.filter((b) => b.choice === "no").length;
    const remaining = Math.max(0, p.eligible_voters.length - p.ballots.length);
    const deadline = new Date(p.deadline);
    return (_jsxs(Card, { className: "mb-2", children: [_jsxs(Flex, { justify: "between", align: "center", children: [_jsxs(Flex, { gap: "2", align: "center", children: [_jsx(Badge, { color: "blue", children: p.kind }), _jsx(Badge, { color: "violet", children: p.strategy }), _jsx(Badge, { color: outcomeColor(p.outcome), children: p.outcome })] }), _jsx(Text, { size: "1", color: "gray", children: p.outcome === "open" ? `closes ${deadline.toLocaleTimeString()}` : "" })] }), _jsx(Text, { size: "3", weight: "bold", className: "block mt-1", children: p.summary }), _jsxs(Text, { size: "1", color: "gray", children: ["proposed by", " ", _jsx("button", { className: "underline", onClick: () => onPodClick(p.proposer), children: p.proposer }), " · ", "eligible: ", p.eligible_voters.length] }), _jsx(Separator, { size: "4", my: "2" }), _jsx(Flex, { gap: "2", wrap: "wrap", align: "center", children: p.eligible_voters.map((v) => {
                    const b = p.ballots.find((b) => b.voter === v);
                    return (_jsxs(Badge, { color: b?.choice === "yes" ? "green" : b?.choice === "no" ? "red" : "gray", children: [v, " ", b ? `· ${b.choice}` : "· pending"] }, v));
                }) }), _jsxs(Text, { size: "1", color: "gray", children: ["tally: ", yesCount, " yes \u00B7 ", noCount, " no \u00B7 ", remaining, " pending"] })] }));
}
function CouncilCard({ c, onPodClick, }) {
    const { data: msgs } = useSWR(`/state/councils/${c.council_id}/messages`, fetcher, { refreshInterval: 4000 });
    return (_jsxs(Card, { className: "mb-2", children: [_jsxs(Flex, { justify: "between", align: "center", children: [_jsxs(Flex, { gap: "2", align: "center", children: [_jsx(Badge, { color: c.status === "open" ? "blue" : "gray", children: c.status }), c.private && _jsx(Badge, { color: "purple", children: "DM" }), c.needs_augustus && _jsx(Badge, { color: "orange", children: "needs Augustus" })] }), _jsx(Text, { size: "1", color: "gray", children: new Date(c.opened_at).toLocaleString() })] }), _jsx(Text, { size: "3", weight: "bold", className: "block mt-1", children: c.topic }), _jsx(Flex, { gap: "2", wrap: "wrap", mt: "1", children: c.participants.map((pp) => (_jsx("button", { className: "text-xs underline text-slate-300", onClick: () => pp !== "__augustus__" && onPodClick(pp), children: pp }, pp))) }), _jsx(Separator, { size: "4", my: "2" }), _jsxs(Flex, { direction: "column", gap: "1", children: [(msgs ?? []).map((m) => (_jsx(Box, { children: _jsxs(Text, { size: "2", children: [_jsxs("span", { className: "font-semibold", children: [m.from_pod, ":"] }), " ", m.body] }) }, m.seq))), (msgs ?? []).length === 0 && (_jsx(Text, { size: "1", color: "gray", children: "(no messages yet)" }))] }), c.summary && (_jsxs(_Fragment, { children: [_jsx(Separator, { size: "4", my: "2" }), _jsxs(Text, { size: "2", color: "gray", children: [_jsx("strong", { children: "Summary:" }), " ", c.summary] })] }))] }));
}
function Section({ title, children }) {
    return (_jsxs(Box, { children: [_jsx(Heading, { size: "4", mb: "2", children: title }), children] }));
}
function Empty() {
    return (_jsx(Text, { size: "2", color: "gray", children: "(none yet)" }));
}
function outcomeColor(o) {
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
