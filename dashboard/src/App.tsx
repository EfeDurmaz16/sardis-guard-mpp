import { Header } from "./components/Header";
import { RiskGaugePanel } from "./components/RiskGaugePanel";
import { LiveEventFeed } from "./components/LiveEventFeed";
import { RiskTimeline } from "./components/RiskTimeline";
import { MandateTree } from "./components/MandateTree";
import { AlertBanner } from "./components/AlertBanner";
import { useEventStream } from "./hooks/useEventStream";

function App() {
  const { events, riskData, stats, connected, alerts, dismissAlert } =
    useEventStream();

  return (
    <div className="h-screen flex flex-col bg-sardis-bg overflow-hidden">
      {/* Header */}
      <Header stats={stats} connected={connected} />

      {/* Main content */}
      <div className="flex-1 flex flex-col p-4 gap-4 min-h-0 overflow-hidden">
        {/* Alert Banner */}
        <AlertBanner alerts={alerts} onDismiss={dismissAlert} />

        {/* Top row: Risk Gauge Cards */}
        <RiskGaugePanel stats={stats} />

        {/* Main grid: Feed + Charts + Mandates */}
        <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
          {/* Left column: Live Event Feed */}
          <div className="col-span-4 min-h-0">
            <LiveEventFeed events={events} />
          </div>

          {/* Right column: Risk Timeline + Mandate Tree */}
          <div className="col-span-8 flex flex-col gap-4 min-h-0">
            {/* Risk Timeline */}
            <div className="flex-1 min-h-0">
              <RiskTimeline data={riskData} />
            </div>

            {/* Mandate Tree */}
            <div className="flex-1 min-h-0">
              <MandateTree />
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-sardis-border bg-sardis-surface px-6 py-2 flex items-center justify-between text-[10px] text-sardis-text-dim font-mono">
        <span>
          Sardis Guard v0.1.0 &middot; MPP Policy Firewall &middot; The
          Synthesis Hackathon 2026
        </span>
        <span>
          API: http://localhost:8402 &middot; Stream: SSE &middot; Paradigm
          Demo
        </span>
      </footer>
    </div>
  );
}

export default App;
