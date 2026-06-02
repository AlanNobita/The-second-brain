import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { Loader2, AlertCircle } from "lucide-react";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { AIStatus } from "./AIStatus";
import { CommandResultsWrapper, type CommandResult } from "./CommandResults";
import type { Message, Source, Suggestion } from "@/lib/types";

interface ChatViewProps {
  sessionId: string;
  messages: Message[];
  loading: boolean;
  streaming: boolean;
  error: string | null;
  onSend: (msg: string) => Promise<void> | void;
  onSuggestionClick: (s: Suggestion) => void;
  onNodeClick?: (label: string) => void;
  pendingSources?: Source[];
  pendingSuggestion?: Suggestion;
  commandResult?: CommandResult | null;
  onDismissCommand?: () => void;
}

export function ChatView({
  sessionId,
  messages,
  loading,
  streaming,
  error,
  onSend,
  onSuggestionClick,
  onNodeClick,
  pendingSources,
  pendingSuggestion,
  commandResult,
  onDismissCommand,
}: ChatViewProps) {
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesRef.current?.scrollTo({
      top: messagesRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streaming, commandResult]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="flex h-full flex-col"
      key={sessionId}
    >
      <header className="flex items-center justify-between border-b border-border/40 px-6 py-4">
        <div>
          <div className="text-sm font-semibold">
            {messages[0]?.content.slice(0, 60) || "New conversation"}
          </div>
          <div className="mt-1">
            <AIStatus />
          </div>
        </div>
        <div className="text-[10px] font-mono text-muted-foreground">
          {sessionId.slice(0, 8)}…
        </div>
      </header>

      <div
        ref={messagesRef}
        className="scrollbar-thin flex-1 overflow-y-auto px-6 py-6"
      >
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        ) : messages.length === 0 && !commandResult ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Send a message to start the conversation.
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-4">
            {messages.map((m, idx) => {
              const isLast = idx === messages.length - 1;
              const sources = isLast && pendingSources ? pendingSources : undefined;
              const suggestion =
                isLast && pendingSuggestion ? pendingSuggestion : undefined;
              return (
                <MessageBubble
                  key={m.id ?? idx}
                  role={m.role}
                  content={m.content}
                  sources={sources}
                  suggestion={suggestion}
                  onSuggestionClick={onSuggestionClick}
                  onNodeClick={onNodeClick}
                />
              );
            })}
            {commandResult && onDismissCommand && (
              <CommandResultsWrapper
                result={commandResult}
                onDismiss={onDismissCommand}
                onNodeClick={onNodeClick}
              />
            )}
            {streaming && (
              <div className="flex items-center gap-2 self-start text-xs text-muted-foreground">
                <Loader2 className="size-3 animate-spin" />
                <span>Thinking…</span>
              </div>
            )}
            {error && (
              <div className="flex items-center gap-2 self-start rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                <AlertCircle className="size-3" />
                <span>{error}</span>
              </div>
            )}
          </div>
        )}
      </div>

      <ChatInput onSend={onSend} disabled={loading} />
    </motion.div>
  );
}
