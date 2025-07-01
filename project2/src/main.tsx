import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";

import App from "./App";
import { config } from "./config";
import { SequenceConnect } from "@0xsequence/connect";
import { BrowserRouter } from "react-router-dom"; // <-- ✅ Import it

function Dapp() {
  return (
    <SequenceConnect config={config}>
      <BrowserRouter> {/* <-- ✅ Wrap your app in a router */}
        <App />
      </BrowserRouter>
    </SequenceConnect>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Dapp />
  </React.StrictMode>
);
