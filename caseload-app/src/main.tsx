import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { initSync, requestPersistentStorage } from "./datafile/fileSync";
import "./styles.css";

async function start() {
  await initSync();
  void requestPersistentStorage().catch(() => null);
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void start();
