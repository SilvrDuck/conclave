import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  body: string;
  /** Apply the illuminated-manuscript styling. Charter / decision /
   * proclamation bodies are authored content and should render in
   * the manuscript palette; in-Forum chrome (badges, panels) should
   * stay in the platform's default styling. */
  manuscript?: boolean;
};

/** Markdown renderer used for authored content (proclamations,
 * charters, sealed decisions, council summaries, spec pages). */
export function Markdown({ body, manuscript = true }: Props) {
  return (
    <div className={manuscript ? "manuscript p-4 rounded" : ""}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
    </div>
  );
}
