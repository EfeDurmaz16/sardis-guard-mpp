import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { OverviewView } from "./components/views/OverviewView";
import { FeedView } from "./components/views/FeedView";
import { PolicyView } from "./components/views/PolicyView";
import { MandatesView } from "./components/views/MandatesView";
import { ScreeningView } from "./components/views/ScreeningView";
import { AuditView } from "./components/views/AuditView";
import { useEventStream } from "./hooks/useEventStream";
import { useApi } from "./hooks/useApi";
import type { ViewId } from "./types";

function App() {
  const [activeView, setActiveView] = useState<ViewId>("overview");
  const { events, riskData, stats, connected } = useEventStream();
  const {
    health,
    summary,
    serviceInfo,
    mandates,
    killSwitches,
    screenEntity,
    screenAddress,
    freezeMandate,
    resumeMandate,
  } = useApi();

  // Merge SSE stats with API stats
  const mergedStats = {
    ...stats,
    agentsTracked: summary?.active_agents ?? health?.agents_tracked ?? stats.agentsTracked,
    activeMandates: summary?.mandates_active ?? health?.mandates_active ?? stats.activeMandates,
    frozenMandates: summary?.mandates_frozen ?? stats.frozenMandates,
    totalVolume: summary?.total_volume ?? stats.totalVolume,
    uniqueMerchants: summary?.unique_merchants ?? stats.uniqueMerchants,
  };

  return (
    <div className="h-screen flex bg-sardis-bg overflow-hidden">
      <Sidebar
        activeView={activeView}
        onNavigate={setActiveView}
        connected={connected}
      />

      <main className="flex-1 min-w-0 overflow-hidden">
        {activeView === "overview" && (
          <OverviewView
            summary={summary}
            stats={mergedStats}
            serviceInfo={serviceInfo}
            killSwitches={killSwitches}
            events={events}
            riskData={riskData}
            connected={connected}
          />
        )}
        {activeView === "feed" && (
          <FeedView events={events} connected={connected} />
        )}
        {activeView === "policy" && (
          <PolicyView />
        )}
        {activeView === "mandates" && (
          <MandatesView
            mandates={mandates}
            onFreeze={freezeMandate}
            onResume={resumeMandate}
          />
        )}
        {activeView === "screening" && (
          <ScreeningView
            onScreenEntity={screenEntity}
            onScreenAddress={screenAddress}
          />
        )}
        {activeView === "audit" && (
          <AuditView events={events} />
        )}
      </main>
    </div>
  );
}

export default App;
