import type { ViewKey } from "../App";

const ITEMS: { key: ViewKey; label: string }[] = [
  { key: "forum", label: "Forum" },
  { key: "tabularium", label: "Tabularium" },
  { key: "council", label: "Council" },
  { key: "charter", label: "Charter Editor" },
  { key: "exile", label: "Exile District" },
  { key: "wizard", label: "Wizard" },
];

type Props = {
  current: ViewKey;
  onSelect: (key: ViewKey) => void;
};

export function Nav({ current, onSelect }: Props) {
  return (
    <nav
      style={{
        background: "var(--stone)",
        color: "var(--marble)",
        padding: "1rem",
        borderRight: "2px solid var(--ink)",
      }}
    >
      <h1
        style={{
          color: "var(--gold)",
          fontSize: "1.4rem",
          marginBottom: "1.5rem",
        }}
      >
        Conclave
      </h1>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {ITEMS.map((item) => (
          <li key={item.key} style={{ marginBottom: "0.5rem" }}>
            <button
              type="button"
              onClick={() => onSelect(item.key)}
              style={{
                width: "100%",
                textAlign: "left",
                background:
                  current === item.key ? "var(--ochre)" : "transparent",
                color: "var(--marble)",
                border: "1px solid var(--marble)",
                padding: "0.5rem 0.75rem",
              }}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
