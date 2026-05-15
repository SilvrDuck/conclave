import { useState } from "react";
import { Nav } from "./components/Nav";
import { CharterEditor } from "./views/CharterEditor";
import { Council } from "./views/Council";
import { ExileDistrict } from "./views/ExileDistrict";
import { Forum } from "./views/Forum";
import { Tabularium } from "./views/Tabularium";
import { Wizard } from "./views/Wizard";

export type ViewKey =
  | "forum"
  | "tabularium"
  | "council"
  | "charter"
  | "exile"
  | "wizard";

const VIEWS: Record<ViewKey, () => React.JSX.Element> = {
  forum: Forum,
  tabularium: Tabularium,
  council: Council,
  charter: CharterEditor,
  exile: ExileDistrict,
  wizard: Wizard,
};

function App() {
  const [view, setView] = useState<ViewKey>("forum");
  const Current = VIEWS[view];
  return (
    <div className="app">
      <Nav current={view} onSelect={setView} />
      <main className="main">
        <Current />
      </main>
    </div>
  );
}

export default App;
