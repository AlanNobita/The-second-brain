import { motion } from "motion/react";
import { Layers } from "lucide-react";
import { CommandChip } from "./CommandChip";
import { AIStatus } from "./AIStatus";
import { ChatInput } from "./ChatInput";

const COMMAND_CHIPS = ["/ytsearch", "/kg", "/reflections", "/reflection-today", "/subscriptions"];

interface ChatSplashProps {
  onSend: (msg: string) => Promise<void> | void;
}

export function ChatSplash({ onSend }: ChatSplashProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.35 }}
      className="flex h-full flex-col"
    >
      <header className="flex items-center justify-between border-b border-border/40 px-6 py-4">
        <div>
          <div className="text-sm font-semibold">Ask Second Brain...</div>
          <div className="mt-1">
            <AIStatus />
          </div>
        </div>
      </header>

      <div className="relative flex flex-1 flex-col items-center justify-center px-6">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 180, damping: 18 }}
          className="relative flex size-20 items-center justify-center rounded-3xl"
          style={{
            background: "oklch(0.22 0.05 280 / 60%)",
            boxShadow:
              "0 0 60px oklch(0.62 0.22 290 / 35%), inset 0 0 24px oklch(0.62 0.22 290 / 20%)",
          }}
        >
          <div
            aria-hidden
            className="absolute inset-0 -z-10 rounded-full blur-3xl"
            style={{ background: "oklch(0.62 0.22 290 / 30%)" }}
          />
          <Layers className="size-9 text-primary-glow" strokeWidth={1.5} />
        </motion.div>

        <motion.h1
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-7 text-2xl font-semibold tracking-tight"
        >
          Your Second Brain
        </motion.h1>
        <motion.p
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.28 }}
          className="mt-3 max-w-md text-center text-sm leading-relaxed text-muted-foreground"
        >
          I am your learning companion, memory repository, and cognitive
          assistant. Start a conversation or search past thoughts.
        </motion.p>

        <motion.div
          initial={{ y: 10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.38 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-2"
        >
          {COMMAND_CHIPS.map((c) => (
            <CommandChip
              key={c}
              label={c}
              onClick={() => onSend(c)}
            />
          ))}
        </motion.div>
      </div>

      <ChatInput onSend={onSend} />
    </motion.div>
  );
}
