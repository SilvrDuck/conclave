import { Fragment, type ReactNode } from "react";
import { EntityLink } from "./EntityLink";
import { type EntityRef } from "./PeekContext";

/** Patterns that identify the domain entities in plain text. The
 * regex is anchored on conclave's id shapes so we don't accidentally
 * linkify arbitrary kebab-case strings. Spec/01 interconnection
 * invariant: every mention should be clickable. */
const PATTERNS: Array<{ regex: RegExp; kind: EntityRef["kind"] }> = [
  // pod ids: `pod-<hex8>` or `pod-<hex12>` minted by mcp-pods.
  { regex: /\bpod-[0-9a-f]{6,32}\b/g, kind: "pod" },
  // decision ids: `dec-<hex>` from decisions.decisions.
  { regex: /\bdec-[0-9a-f]{6,32}\b/g, kind: "decision" },
  // proposal ids: `prop-<hex>` from senate.proposals.
  { regex: /\bprop-[0-9a-f]{6,32}\b/g, kind: "proposal" },
  // council ids: `cou-<hex>` from council.councils.
  { regex: /\bcou-[0-9a-f]{6,32}\b/g, kind: "council" },
];

type Match = {
  start: number;
  end: number;
  kind: EntityRef["kind"];
  text: string;
};

function findMatches(text: string): Match[] {
  const matches: Match[] = [];
  for (const { regex, kind } of PATTERNS) {
    // RegExp.exec with /g is stateful — clone per call.
    const re = new RegExp(regex.source, regex.flags);
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      matches.push({ start: m.index, end: m.index + m[0].length, kind, text: m[0] });
    }
  }
  matches.sort((a, b) => a.start - b.start);
  // Drop overlaps (unlikely but defensive).
  const out: Match[] = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start >= cursor) {
      out.push(m);
      cursor = m.end;
    }
  }
  return out;
}

/** Replace conclave-id tokens in `text` with clickable EntityLinks. */
export function Linkified({ text }: { text: string }) {
  const matches = findMatches(text);
  if (matches.length === 0) return <>{text}</>;
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start > cursor) parts.push(text.slice(cursor, m.start));
    parts.push(
      <EntityLink key={`${m.start}-${m.kind}`} kind={m.kind} id={m.text}>
        {m.text}
      </EntityLink>,
    );
    cursor = m.end;
  }
  if (cursor < text.length) parts.push(text.slice(cursor));
  return (
    <>
      {parts.map((p, i) => (
        <Fragment key={i}>{p}</Fragment>
      ))}
    </>
  );
}
