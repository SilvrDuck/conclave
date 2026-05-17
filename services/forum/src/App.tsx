/** Spec/09 — Forum shell. Bandeau + four perspectives + folio
 * provider + folio drawer. No router: perspective state is local;
 * the folio drawer carries cross-cutting entity navigation. */

import { useState } from "react";
import { Bandeau, type Perspective } from "./components/Bandeau";
import { FolioDrawer } from "./components/FolioDrawer";
import { FolioProvider } from "./folio";
import { Glance } from "./perspectives/Glance";
import { Witness } from "./perspectives/Witness";
import { Try } from "./perspectives/Try";
import { Direct } from "./perspectives/Direct";
import { Inbox } from "./perspectives/Inbox";
import { useDomainStream } from "./sse";

export default function App() {
  const [perspective, setPerspective] = useState<Perspective>("glance");

  // Server-Sent Events from observer — invalidates SWR keys when
  // relevant events land so the perspective re-fetches without
  // every component polling.
  useDomainStream();

  return (
    <FolioProvider>
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <Bandeau
          perspective={perspective}
          onChangePerspective={setPerspective}
        />
        <main
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
          }}
        >
          {perspective === "glance" ? <Glance /> : null}
          {perspective === "witness" ? <Witness /> : null}
          {perspective === "try" ? <Try /> : null}
          {perspective === "direct" ? <Direct /> : null}
          {perspective === "inbox" ? <Inbox /> : null}
        </main>
        <FolioDrawer />
      </div>
    </FolioProvider>
  );
}
