import {
  ShieldCheck,
  Pulse,
  ListChecks,
  TreeStructure,
  MagnifyingGlass,
  ClockCounterClockwise,
} from "@phosphor-icons/react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ViewId } from "../types";

const NAV_ITEMS: { id: ViewId; label: string; icon: React.ElementType }[] = [
  { id: "overview", label: "Overview", icon: ShieldCheck },
  { id: "feed", label: "Live Feed", icon: Pulse },
  { id: "policy", label: "Policy Simulator", icon: ListChecks },
  { id: "mandates", label: "Mandates", icon: TreeStructure },
  { id: "screening", label: "Screening", icon: MagnifyingGlass },
  { id: "audit", label: "Audit Trail", icon: ClockCounterClockwise },
];

interface SidebarProps {
  activeView: ViewId;
  onNavigate: (view: ViewId) => void;
  connected: boolean;
}

export function Sidebar({ activeView, onNavigate, connected }: SidebarProps) {
  return (
    <aside className="w-14 flex flex-col items-center border-r border-border bg-sardis-surface shrink-0">
      {/* Logo mark */}
      <div className="h-14 flex items-center justify-center border-b border-border w-full">
        <div className="w-7 h-7 rounded-md bg-sardis-amber/15 flex items-center justify-center">
          <ShieldCheck weight="bold" className="w-4 h-4 text-sardis-amber" />
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 flex flex-col items-center gap-1 pt-3 px-2">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const isActive = activeView === id;
          return (
            <Tooltip key={id} delayDuration={0}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => onNavigate(id)}
                  className={`w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-150 ${
                    isActive
                      ? "bg-sardis-amber/12 text-sardis-amber"
                      : "text-sardis-text-muted hover:text-sardis-text-secondary hover:bg-sardis-surface-2"
                  }`}
                >
                  <Icon weight={isActive ? "bold" : "regular"} className="w-[18px] h-[18px]" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>
                <p className="text-xs">{label}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </nav>

      {/* Connection indicator */}
      <div className="pb-4">
        <Tooltip delayDuration={0}>
          <TooltipTrigger asChild>
            <div className="flex items-center justify-center">
              <span
                className={`w-2 h-2 rounded-full ${
                  connected ? "bg-sardis-green pulse-dot" : "bg-sardis-red"
                }`}
              />
            </div>
          </TooltipTrigger>
          <TooltipContent side="right" sideOffset={8}>
            <p className="text-xs">{connected ? "Stream connected" : "Disconnected"}</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </aside>
  );
}
