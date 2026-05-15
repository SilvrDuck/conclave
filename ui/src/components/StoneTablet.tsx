import type { ReactNode } from "react";

type Props = {
  title: string;
  meta?: string;
  children: ReactNode;
};

export function StoneTablet({ title, meta, children }: Props) {
  return (
    <article
      style={{
        background: "var(--marble)",
        border: "2px solid var(--stone)",
        borderRadius: "4px",
        padding: "1rem 1.25rem",
        marginBottom: "1rem",
        boxShadow: "inset 0 0 0 1px var(--gold)",
      }}
    >
      <header
        style={{
          borderBottom: "1px dashed var(--stone)",
          marginBottom: "0.5rem",
        }}
      >
        <h3 style={{ margin: "0 0 0.25rem 0", color: "var(--ink)" }}>
          {title}
        </h3>
        {meta ? (
          <small style={{ color: "var(--stone)", fontStyle: "italic" }}>
            {meta}
          </small>
        ) : null}
      </header>
      <div>{children}</div>
    </article>
  );
}
