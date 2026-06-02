import { useEffect, useState, useCallback } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowLeft, Search } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { ChatSplash } from "@/components/chat/ChatSplash";
import { ChatView } from "@/components/chat/ChatView";
import { KnowledgeGraph } from "@/components/graph/KnowledgeGraph";
import type { CommandResult } from "@/components/chat/CommandResults";
import { api } from "@/lib/api";
import type { Message, Source, Suggestion } from "@/lib/types";

type View = "chat" | "graph" | "search";

interface SearchResult {
  id?: number;
  session_id: string;
  role: string;
  content: string;
  _source?: string;
  _score?: number;
}

export default function App() {
  const [view, setView] = useState<View>("chat");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingSources, setPendingSources] = useState<Source[] | undefined>();
  const [pendingSuggestion, setPendingSuggestion] = useState<Suggestion | undefined>();
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [commandResult, setCommandResult] = useState<CommandResult | null>(null);

  const loadHistory = useCallback(async (id: string) => {
    try {
      setLoading(true);
      const data = await api.getHistory(id);
      setMessages(data.messages);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleNewChat = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setPendingSources(undefined);
    setPendingSuggestion(undefined);
    setCommandResult(null);
    setError(null);
    setView("chat");
  }, []);

  const handleSelectSession = useCallback(
    async (id: string) => {
      setSessionId(id);
      setCommandResult(null);
      setView("chat");
      await loadHistory(id);
    },
    [loadHistory]
  );

  const handleSend = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text) return;
      setError(null);

      // Slash commands
      if (text.startsWith("/ytsearch ")) {
        const q = text.slice("/ytsearch ".length).trim();
        if (!q) return;
        try {
          setLoading(true);
          const results = await api.ytSearch(q);
          setCommandResult({ kind: "youtube-search", query: q, results });
        } catch (e: any) {
          setError(e.message);
        } finally {
          setLoading(false);
        }
        return;
      }

      if (text === "/reflections") {
        try {
          setLoading(true);
          const refs = await api.listReflections();
          setCommandResult({ kind: "reflections", reflections: refs });
        } catch (e: any) {
          setError(e.message);
        } finally {
          setLoading(false);
        }
        return;
      }

      if (text === "/reflection-today") {
        try {
          setLoading(true);
          let ref = await api.getTodayReflection();
          if (!ref) ref = await api.generateReflection();
          setCommandResult({ kind: "reflection-today", reflection: ref });
        } catch (e: any) {
          setError(e.message);
        } finally {
          setLoading(false);
        }
        return;
      }

      if (text.startsWith("/kg")) {
        const sub = text.slice(3).trim();
        if (sub.startsWith("add ")) {
          const parts = sub.slice(4).split(",").map((s) => s.trim());
          if (parts[0]) {
            try {
              setLoading(true);
              const created = await api.createEntity(
                parts[0],
                parts[1] || "concept",
                parts[2] || ""
              );
              const entity = {
                name: created?.name ?? parts[0],
                type: created?.type ?? (parts[1] || "concept"),
                description: created?.description ?? (parts[2] || ""),
              };
              setCommandResult({ kind: "kg-add", entity });
            } catch (e: any) {
              setError(e.message);
            } finally {
              setLoading(false);
            }
          }
        } else if (sub === "list") {
          try {
            setLoading(true);
            const entities = await api.listEntities();
            setCommandResult({
              kind: "kg-list",
              entities: entities.map((e: any) => ({
                id: e.id,
                name: e.name,
                type: e.type,
                description: e.description,
              })),
            });
          } catch (e: any) {
            setError(e.message);
          } finally {
            setLoading(false);
          }
        } else if (sub === "") {
          setView("graph");
          return;
        } else {
          setCommandResult({ kind: "kg-help" });
        }
        return;
      }

      // Regular chat message
      const userMsg: Message = {
        id: Date.now(),
        session_id: sessionId || "pending",
        role: "user",
        content: text,
      };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming(true);
      try {
        const res = await api.sendMessage(text, sessionId || undefined);
        if (!sessionId) setSessionId(res.session_id);
        setMessages((prev) => [
          ...prev,
          { id: Date.now() + 1, session_id: res.session_id, role: "assistant", content: res.reply },
        ]);
        setPendingSources(res.sources);
        setPendingSuggestion(res.suggestion);
      } catch (e: any) {
        setError(e.message || "Failed to send message");
      } finally {
        setStreaming(false);
      }
    },
    [sessionId]
  );

  const handleSuggestionClick = useCallback(
    async (s: Suggestion) => {
      await handleSelectSession(s.session_id);
    },
    [handleSelectSession]
  );

  const handleNodeClick = useCallback((label: string) => {
    console.log("Open graph focused on", label);
    setView("graph");
  }, []);

  const handleSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSearchResults([]);
      setView("chat");
      return;
    }
    try {
      setSearching(true);
      const results = await api.search(q);
      setSearchResults(results);
      setView("search");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSearching(false);
    }
  }, []);

  return (
    <AppShell
      activeSessionId={sessionId}
      onSelectSession={handleSelectSession}
      onNewChat={handleNewChat}
      onOpenGraph={() => setView(view === "graph" ? "chat" : "graph")}
      onSearch={handleSearch}
      graphOpen={view === "graph"}
    >
      <AnimatePresence mode="wait">
        {view === "graph" ? (
          <motion.div
            key="graph"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="h-full"
          >
            <KnowledgeGraph />
          </motion.div>
        ) : view === "search" ? (
          <motion.div
            key="search"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="flex h-full flex-col"
          >
            <header className="flex items-center gap-3 border-b border-border/40 px-6 py-4">
              <button
                onClick={() => setView("chat")}
                className="text-muted-foreground transition-colors hover:text-foreground"
              >
                <ArrowLeft className="size-4" />
              </button>
              <div>
                <div className="text-sm font-semibold">Search results</div>
                <div className="text-xs text-muted-foreground">
                  {searching ? "Searching…" : `${searchResults.length} match(es)`}
                </div>
              </div>
            </header>
            <div className="scrollbar-thin flex-1 overflow-y-auto px-6 py-6">
              <div className="mx-auto flex max-w-3xl flex-col gap-3">
                {searchResults.length === 0 && !searching && (
                  <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                    No matches
                  </div>
                )}
                {searchResults.map((r, i) => (
                  <button
                    key={i}
                    onClick={() => r.session_id && handleSelectSession(r.session_id)}
                    className="rounded-xl border border-border/50 bg-surface/40 p-4 text-left transition-colors hover:border-primary/40 hover:bg-surface/60"
                  >
                    <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                      <Search className="size-2.5" />
                      {r._source || "match"}
                    </div>
                    <div className="line-clamp-3 text-sm leading-relaxed">
                      {r.content}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>
        ) : sessionId === null && messages.length === 0 ? (
          <ChatSplash key="splash" onSend={handleSend} />
        ) : (
          <ChatView
            key={sessionId || "new"}
            sessionId={sessionId || "new"}
            messages={messages}
            loading={loading}
            streaming={streaming}
            error={error}
            onSend={handleSend}
            onSuggestionClick={handleSuggestionClick}
            onNodeClick={handleNodeClick}
            pendingSources={pendingSources}
            pendingSuggestion={pendingSuggestion}
            commandResult={commandResult}
            onDismissCommand={() => setCommandResult(null)}
          />
        )}
      </AnimatePresence>
    </AppShell>
  );
}
