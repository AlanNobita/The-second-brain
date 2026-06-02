import * as React from "react";
import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import {
  Layers,
  Search,
  Plus,
  Network,
  Sun,
  Moon,
  MessageSquare,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Session } from "@/lib/types";
import { RippleButton } from "@/components/ui/RippleButton";

interface SidebarProps {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onOpenGraph: () => void;
  onSearch: (q: string) => void;
  graphOpen: boolean;
}

export function Sidebar({
  activeSessionId,
  onSelectSession,
  onNewChat,
  onOpenGraph,
  onSearch,
  graphOpen,
}: SidebarProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
    const dark = stored ? stored === "dark" : prefersDark;
    setIsDark(dark);
    document.documentElement.classList.toggle("dark", dark);
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  const loadSessions = async () => {
    try {
      const data = await api.listSessions();
      setSessions(data);
    } catch (err) {
      console.error("Failed to load sessions", err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [activeSessionId]);

  const handleQueryChange = (q: string) => {
    setQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onSearch(q);
    }, 350);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteSession(id);
      await loadSessions();
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-3 px-5 py-5">
        <div
          className="flex size-9 items-center justify-center rounded-xl"
          style={{
            background: "var(--gradient-primary)",
            boxShadow: "var(--shadow-glow-primary)",
          }}
        >
          <Layers className="size-4 text-white" strokeWidth={1.75} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">Second Brain</div>
          <div className="text-[10px] tracking-[0.18em] text-muted-foreground">
            COGNITIVE OS
          </div>
        </div>
      </div>

      <div className="px-4">
        <motion.div
          animate={{
            boxShadow: focused
              ? "0 0 0 1px oklch(0.62 0.22 290 / 60%), 0 0 16px oklch(0.62 0.22 290 / 25%)"
              : "0 0 0 1px transparent",
          }}
          transition={{ duration: 0.25 }}
          className="flex items-center gap-2 rounded-lg bg-surface/70 px-3 py-2"
        >
          <Search className="size-3.5 text-muted-foreground" strokeWidth={1.5} />
          <input
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="Search memories..."
            className="w-full bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground"
          />
        </motion.div>
      </div>

      <div className="scrollbar-thin mt-6 flex-1 overflow-y-auto px-2">
        <div className="px-3 pb-2 text-[10px] font-semibold tracking-[0.2em] text-muted-foreground">
          RECENT CHATS
        </div>
        {sessions.length === 0 ? (
          <div className="px-3 py-4 text-xs text-muted-foreground">
            No conversations yet.
          </div>
        ) : (
          <ul className="flex flex-col gap-1">
            {sessions.map((s) => {
              const isActive = s.session_id === activeSessionId;
              return (
                <motion.li
                  key={s.session_id}
                  whileHover={{ x: 2 }}
                  onClick={() => onSelectSession(s.session_id)}
                  className={`group flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2.5 transition-colors ${
                    isActive
                      ? "border-accent-teal/40 bg-surface-hover/70"
                      : "border-transparent bg-surface/40 hover:border-accent-teal/30 hover:bg-surface-hover/60"
                  }`}
                >
                  <MessageSquare
                    className={`mt-0.5 size-3.5 shrink-0 transition-colors ${
                      isActive ? "text-accent-teal" : "text-muted-foreground group-hover:text-accent-teal"
                    }`}
                    strokeWidth={1.5}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs font-medium text-foreground">
                      {s.title || "(empty)"}
                    </div>
                    <div className="mt-0.5 text-[10px] text-muted-foreground">
                      {s.message_count} messages
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(s.session_id, e)}
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                    aria-label="Delete session"
                  >
                    <Trash2 className="size-3 text-muted-foreground hover:text-destructive" />
                  </button>
                </motion.li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="space-y-2 border-t border-sidebar-border/60 p-3">
        <RippleButton
          onClick={onNewChat}
          className="flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium text-white transition-transform active:scale-[0.98]"
          style={{
            background: "var(--gradient-primary)",
            boxShadow: "var(--shadow-glow-primary)",
          }}
        >
          <Plus className="size-4" strokeWidth={1.75} />
          New Chat
        </RippleButton>

        <div className="flex items-center justify-between rounded-lg px-2 py-1.5">
          <button
            onClick={onOpenGraph}
            className="group flex items-center gap-2 text-xs"
          >
            <Network
              className={`size-4 transition-colors ${
                graphOpen
                  ? "text-primary"
                  : "text-muted-foreground group-hover:text-foreground"
              }`}
              strokeWidth={1.5}
            />
            <span
              className={
                graphOpen
                  ? "text-primary"
                  : "text-muted-foreground group-hover:text-foreground"
              }
            >
              Graph
            </span>
          </button>
          <button
            onClick={toggleTheme}
            className="text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Toggle theme"
          >
            {isDark ? (
              <Sun className="size-3.5" strokeWidth={1.5} />
            ) : (
              <Moon className="size-3.5" strokeWidth={1.5} />
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}
