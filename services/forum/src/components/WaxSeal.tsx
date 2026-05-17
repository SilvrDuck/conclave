/** Spec/09 §6.10 — Wax seal. Primary action button.
 *
 * Cinnabar 32-px disc with a single Cinzel letter embossed
 * (`P` Proclaim, `S` Seal edit, `O` Open app, `A`/`N` ballots,
 * `—` abstain).
 *
 * Used sparingly: at most one wax seal per surface. Secondary
 * actions use compass-blue ink-links instead. */

import type { ButtonHTMLAttributes } from "react";
import { C } from "../theme";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  letter: string;
  label: string;
  variant?: "cinnabar" | "gold" | "wash";
  size?: number;
}

const VARIANT_BG: Record<NonNullable<Props["variant"]>, string> = {
  cinnabar: C.cinnabar,
  gold: C.gold,
  wash: C.wash,
};

export function WaxSeal({
  letter,
  label,
  variant = "cinnabar",
  size = 32,
  disabled,
  className,
  ...rest
}: Props) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: VARIANT_BG[variant],
        color: variant === "wash" ? C.ink : C.parchment,
        border: `1px solid ${C.ink}`,
        fontFamily: "var(--f-display)",
        fontWeight: 600,
        fontSize: Math.round(size * 0.42),
        letterSpacing: 0,
        textTransform: "uppercase",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.45 : 1,
        boxShadow: "inset 0 -2px 0 rgba(0,0,0,0.18)",
        padding: 0,
        lineHeight: 1,
      }}
      {...rest}
    >
      {letter}
    </button>
  );
}
