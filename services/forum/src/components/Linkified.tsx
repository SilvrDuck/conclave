import { Fragment, type ReactNode } from "react";
import { EntityLink } from "./EntityLink";
import { type EntityRef } from "./PeekContext";

/** Patterns matching the actual id shapes minted by the platform.
 * Spec/01 interconnection invariant: every domain entity reference
 * in authored text should resolve to a clickable peek. Keep these
 * in sync with: mcp-pods spawner (pod-…), mcp-senate (prop-…),
 * mcp-coms (council-…), mcp-decisions (adr-…). */
const PATTERNS: Array<{ regex: RegExp; kind: EntityRef["kind"] }> = [
  // pod ids: `pod-<hex>` (spawner mints 12-hex; older flows 6-32).
  { regex: /\bpod-[0-9a-f]{6,32}\b/g, kind: "pod" },
  // proposal ids: `prop-<hex>` from senate.proposals.
  { regex: /\bprop-[0-9a-f]{6,32}\b/g, kind: "proposal" },
  // council ids: `council-<hex>` from council.councils.
  { regex: /\bcouncil-[0-9a-f]{6,32}\b/g, kind: "council" },
  // decision ids: `adr-<hex>` (current mint) or `dec-<hex>` (legacy).
  { regex: /\badr-[0-9a-f]{6,32}\b/g, kind: "decision" },
  { regex: /\bdec-[0-9a-f]{6,32}\b/g, kind: "decision" },
];

const AUGUSTUS_RE = /\b__augustus__\b/g;
// Proclamation seq references: `№ 1`, `№1`, `# 1`, `#1`. Anchored on
// the conclave-specific glyphs and forms so we don't false-positive
// on generic "#1" mentions in arbitrary text.
const PROCLAMATION_RE = /(?:№\s?|#\s?)(\d+)\b/g;
// Spec file refs: `spec/00-vision.md` etc — used in council
// summaries and decision bodies that quote the spec.
const SPEC_RE = /\bspec\/(\d{2}-[a-z0-9-]+\.md)\b/g;

type Match = {
  start: number;
  end: number;
  /** Renderer for this match. */
  render: (key: string) => ReactNode;
};

function findMatches(text: string): Match[] {
  const matches: Match[] = [];

  for (const { regex, kind } of PATTERNS) {
    const re = new RegExp(regex.source, regex.flags);
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const id = m[0];
      matches.push({
        start: m.index,
        end: m.index + id.length,
        render: (key) => (
          <EntityLink key={key} kind={kind} id={id}>
            {id}
          </EntityLink>
        ),
      });
    }
  }

  // __augustus__ — render the literal but it's not a clickable peek
  // (no pod entity). Style it so it's visibly distinct.
  let am: RegExpExecArray | null;
  const augustusRe = new RegExp(AUGUSTUS_RE.source, AUGUSTUS_RE.flags);
  while ((am = augustusRe.exec(text)) !== null) {
    const text0 = am[0];
    matches.push({
      start: am.index,
      end: am.index + text0.length,
      render: (key) => (
        <span key={key} style={{ color: "var(--conclave-rubric)" }}>
          Augustus
        </span>
      ),
    });
  }

  let pm: RegExpExecArray | null;
  const procRe = new RegExp(PROCLAMATION_RE.source, PROCLAMATION_RE.flags);
  while ((pm = procRe.exec(text)) !== null) {
    const full = pm[0];
    const seq = pm[1];
    matches.push({
      start: pm.index,
      end: pm.index + full.length,
      render: (key) => (
        <EntityLink key={key} kind="proclamation" id={seq}>
          {full}
        </EntityLink>
      ),
    });
  }

  let sm: RegExpExecArray | null;
  const specRe = new RegExp(SPEC_RE.source, SPEC_RE.flags);
  while ((sm = specRe.exec(text)) !== null) {
    const full = sm[0];
    const fname = sm[1];
    matches.push({
      start: sm.index,
      end: sm.index + full.length,
      render: (key) => (
        <a
          key={key}
          className="entity-link"
          href={`#spec:${fname}`}
          onClick={(e) => {
            e.preventDefault();
            // Spec viewer is opened by the AboutDialog/SpecDialog
            // surface — emit a window event the surface listens to.
            window.dispatchEvent(
              new CustomEvent("conclave:open-spec", { detail: fname }),
            );
          }}
        >
          {full}
        </a>
      ),
    });
  }

  matches.sort((a, b) => a.start - b.start);
  // Drop overlaps (e.g. if two regex flavours match the same span).
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

/** Replace conclave-id tokens, Augustus references, proclamation
 * numerals, and spec links in `text` with their clickable / styled
 * equivalents. */
export function Linkified({ text }: { text: string }) {
  const matches = findMatches(text);
  if (matches.length === 0) return <>{text}</>;
  const parts: ReactNode[] = [];
  let cursor = 0;
  matches.forEach((m, i) => {
    if (m.start > cursor) parts.push(text.slice(cursor, m.start));
    parts.push(m.render(`m${i}`));
    cursor = m.end;
  });
  if (cursor < text.length) parts.push(text.slice(cursor));
  return (
    <>
      {parts.map((p, i) => (
        <Fragment key={i}>{p}</Fragment>
      ))}
    </>
  );
}
