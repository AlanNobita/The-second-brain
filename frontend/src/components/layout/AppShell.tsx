import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { PulseDivider } from "./PulseDivider";

interface AppShellProps {
  children: ReactNode;
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onOpenGraph: () => void;
  onSearch: (q: string) => void;
  graphOpen: boolean;
}

export function AppShell({
  children,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onOpenGraph,
  onSearch,
  graphOpen,
}: AppShellProps) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar
        activeSessionId={activeSessionId}
        onSelectSession={onSelectSession}
        onNewChat={onNewChat}
        onOpenGraph={onOpenGraph}
        onSearch={onSearch}
        graphOpen={graphOpen}
      />
      <PulseDivider />
      <main className="relative flex h-full min-w-0 flex-1 flex-col">
        {children}
      </main>
    </div>
  );
}
