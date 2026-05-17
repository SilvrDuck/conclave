/** Replace conclave-id tokens in arbitrary authored text with
 * clickable ink-links. Patterns match the actual ids minted by:
 *
 *   mcp-pods spawner       — `pod-<hex>` (12 hex chars)
 *   mcp-senate             — `prop-<hex>`
 *   mcp-coms               — `council-<hex>`
 *   mcp-decisions          — `adr-<hex>` (current) / `dec-<hex>` (legacy)
 *
 * Plus three special tokens:
 *
 *   `№ III` / `#3`         — proclamation references
 *   `__augustus__`         — rendered as gold "Augustus" (non-clickable)
 *   `spec/00-vision.md`    — dispatches `conclave:open-spec` event
 */

import { Fragment, type ReactNode } from "react";
import { EntityLink } from "./EntityLink";
import type { EntityKind } from "../folio";

const PATTERNS: Array<{ regex: RegExp; kind: EntityKind }> = [
  { regex: /\bpod-[0-9a-f]{6,32}\b/g, kind: "pod" },
  { regex: /\bprop-[0-9a-f]{6,32}\b/g, kind: "proposal" },
  { regex: /\bcouncil-[0-9a-f]{6,32}\b/g, kind: "council" },
  { regex: /\badr-[0-9a-f]{6,32}\b/g, kind: "decision" },
  { regex: /\bdec-[0-9a-f]{6,32}\b/g, kind: "decision" },
];

const AUGUSTUS_RE = /\b__augustus__\b/g;
const PROCLAMATION_RE = /(?:№\s?|#\s?)(\d+)\b/g;
const SPEC_RE = /\bspec\/(\d{2}-[a-z0-9-]+\.md)\b/g;

type Match = {
  start: number;
  end: number;
  render: (key: string) => ReactNode;
};

function findMatches(text: string): Match[] {
  const out: Match[] = [];

  for (const { regex, kind } of PATTERNS) {
    const re = new RegExp(regex.source, regex.flags);
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const id = m[0];
      out.push({
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

  let am: RegExpExecArray | null;
  const augustusRe = new RegExp(AUGUSTUS_RE.source, AUGUSTUS_RE.flags);
  while ((am = augustusRe.exec(text)) !== null) {
    out.push({
      start: am.index,
      end: am.index + am[0].length,
      render: (key) => (
        <span key={key} className="c-gold" style={{ fontStyle: "italic" }}>
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
    out.push({
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
    out.push({
      start: sm.index,
      end: sm.index + full.length,
      render: (key) => (
        <a
          key={key}
          className="c-link"
          href={`#spec:${fname}`}
          onClick={(e) => {
            e.preventDefault();
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

  out.sort((a, b) => a.start - b.start);
  // Drop overlaps.
  const deduped: Match[] = [];
  let cursor = 0;
  for (const m of out) {
    if (m.start >= cursor) {
      deduped.push(m);
      cursor = m.end;
    }
  }
  return deduped;
}

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
