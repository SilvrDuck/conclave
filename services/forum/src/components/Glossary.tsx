import * as Tooltip from "@radix-ui/react-tooltip";
import { type ReactNode } from "react";

/** Conclave-specific jargon. Inline (i) chips render an explanatory
 * tooltip on hover/focus so the Forum doesn't need a separate
 * glossary page for first-time readers. (kanban #47) */
const TERMS: Record<string, string> = {
  proclamation:
    "A mandate from Augustus. Sets the swarm's horizon. Spec/02 Phase 0.",
  council:
    "A short-lived chatroom for cross-cutting debate. Opened by any pod. Closes with a summary that may seal a decision.",
  proposal:
    "A senate motion: admission, completion, contract change, exile, or image swap. Closes via the strategy you picked.",
  ballot:
    "One vote cast by an eligible voter. yes / no / abstain, with an optional comment.",
  decision:
    "A sealed ADR. Immutable once sealed. Origin: a proposal, a council, or a proclamation.",
  charter:
    "A pod's role definition. Augustus and the agent can both edit it. The platform's iusiurandum (cross-pod rules) is prepended automatically.",
  admission:
    "The vote that welcomes a new pod into the swarm. N=1 admissions auto-pass via the proposer's self-vote.",
  exile:
    "The vote that removes a pod. Requires supermajority by default. Containers go away; identity is retained for audit.",
  consensus_omnium:
    "A vote passes only if every eligible voter says yes. Highest bar; used for admissions and identity changes.",
  supermajority:
    "Passes at ≥ ⌈2/3⌉ yes votes among the eligible. Used for exiles and irreversible changes.",
  majority:
    "Passes at the first half-plus-one. The default for low-risk choices.",
  sortition:
    "A subset of eligible voters is drawn at random; the draw is shown in the UI. Used when the full senate would be overkill.",
  pod: "One agent + one service it manages, end-to-end. Code-pod (agent writes the code) or adopted-pod (agent manages an OSS image).",
  iusiurandum:
    "The platform-priorities preamble appended to every pod's system prompt. Spec/03 row 132.",
};

type Props = {
  term: keyof typeof TERMS | string;
  /** The visible label. Defaults to the term itself. */
  children?: ReactNode;
};

export function Glossary({ term, children }: Props) {
  const definition = TERMS[term];
  if (!definition) {
    // No-op for unknown terms so callers don't crash.
    return <>{children ?? term}</>;
  }
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <span className="inline-flex items-baseline gap-0.5 cursor-help">
            {children ?? term}
            <span
              aria-hidden
              className="text-xs"
              style={{ color: "var(--conclave-gold)" }}
            >
              ⓘ
            </span>
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            sideOffset={4}
            className="z-50 max-w-xs rounded-md bg-slate-800 px-3 py-2 text-xs text-slate-100 shadow-lg border border-slate-700"
          >
            {definition}
            <Tooltip.Arrow className="fill-slate-800" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
