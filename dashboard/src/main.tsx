import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";
import { config } from "./wagmi-config";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./index.css";
import App from "./App";

const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider delayDuration={0}>
          <App />
        </TooltipProvider>
      </QueryClientProvider>
    </WagmiProvider>
  </StrictMode>
);
