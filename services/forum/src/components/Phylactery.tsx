import { EntityLink } from "./EntityLink";
import { Linkified } from "./Linkified";

type Props = {
  sender: string;
  body: string;
  sentAt?: string;
  /** Optional auxiliary metadata to render below the body (e.g.
   * a sealed-decision link when this council message closed one). */
  footer?: React.ReactNode;
};

/** Roman speech-bubble (phylactery) used for council messages.
 * Sender renders as an EntityLink → click opens the pod's drawer.
 * The body is run through Linkified so pod-id-shaped tokens become
 * clickable references too (spec/01 universal click-through). */
export function Phylactery({ sender, body, sentAt, footer }: Props) {
  return (
    <div className="phylactery">
      <div className="flex items-baseline gap-2 mb-1">
        <span className="sender">
          <EntityLink kind="pod" id={sender}>
            {sender}
          </EntityLink>
        </span>
        {sentAt ? (
          <span className="text-xs italic" style={{ color: "var(--conclave-ink-dim)" }}>
            {new Date(sentAt).toLocaleTimeString()}
          </span>
        ) : null}
      </div>
      <div>
        <Linkified text={body} />
      </div>
      {footer ? <div className="mt-2">{footer}</div> : null}
    </div>
  );
}
