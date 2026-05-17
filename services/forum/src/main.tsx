import React from "react";
import ReactDOM from "react-dom/client";
import { Theme } from "@radix-ui/themes";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {/* Radix Theme provides primitives (dialogs, tooltips, etc.);
        spec/09 palette tokens override its default colours via the
        .radix-themes class in index.css. Appearance is light because
        the parchment surface is light. */}
    <Theme appearance="light" radius="small" grayColor="sand" scaling="95%">
      <App />
    </Theme>
  </React.StrictMode>,
);
