import * as React from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { motion } from "motion/react";
import { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSend: (message: string) => Promise<void> | void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled = false, placeholder = "Ask Second Brain..." }: ChatInputProps) {
  const [focused, setFocused] = useState(false);
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim() || sending) return;
    const msg = value.trim();
    setValue("");
    setSending(true);
    try {
      await onSend(msg);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="border-t border-border/50 bg-background/60 px-6 pb-3 pt-4 backdrop-blur-md">
      <motion.form
        onSubmit={submit}
        animate={{
          boxShadow: focused
            ? "0 0 0 1px oklch(0.62 0.22 290 / 70%), 0 0 24px oklch(0.62 0.22 290 / 25%)"
            : "0 0 0 1px oklch(1 0 0 / 6%)",
        }}
        transition={{ duration: 0.25 }}
        className="mx-auto flex max-w-3xl items-center gap-2 rounded-2xl bg-surface/70 px-4 py-2.5"
      >
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          disabled={disabled || sending}
          className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:opacity-50"
        />
        <motion.button
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          type="submit"
          disabled={disabled || sending || !value.trim()}
          className="flex size-9 items-center justify-center rounded-xl text-white disabled:opacity-50"
          style={{
            background: "var(--gradient-primary)",
            boxShadow: "var(--shadow-glow-primary)",
          }}
        >
          {sending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <ArrowRight className="size-4" strokeWidth={2} />
          )}
        </motion.button>
      </motion.form>
      <p className="mt-2 text-center text-[10px] text-muted-foreground/80">
        AI responses powered by OpenCode Zen · Type{" "}
        <kbd className="rounded bg-surface px-1 py-0.5 text-foreground/80">/</kbd>{" "}
        for commands
      </p>
    </div>
  );
}
