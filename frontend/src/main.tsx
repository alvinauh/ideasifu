import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "@/styles.css";
import App from "@/App";
import { TierProvider } from "@/lib/tier";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <TierProvider>
        <App />
      </TierProvider>
    </BrowserRouter>
  </StrictMode>,
);
