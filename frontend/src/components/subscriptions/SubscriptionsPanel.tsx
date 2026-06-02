import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { motion } from "motion/react";
import {
  Loader2,
  Check,
  AlertCircle,
  Rss,
  Plus,
  Trash2,
  Download,
  RefreshCw,
  Clock,
  Youtube,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Subscription } from "@/lib/types";

type Status = "idle" | "loading" | "success" | "error";

function formatRelative(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const now = Date.now();
  const diffMs = now - d.getTime();
  const diffSec = Math.round(diffMs / 1000);
  if (diffSec < 60) return "just now";
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function SubscribeForm({ onSubscribed }: { onSubscribed: () => void | Promise<void> }) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [created, setCreated] = useState<string>("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed || status === "loading") return;
    setStatus("loading");
    setError("");
    try {
      const res = await api.ytSubscribe(trimmed);
      setStatus("success");
      setCreated(res.channel_name || trimmed);
      setUrl("");
      await onSubscribed();
      setTimeout(() => setStatus("idle"), 2500);
    } catch (e: any) {
      setStatus("error");
      setError(e?.message || "Subscribe failed");
    }
  };

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-2 rounded-lg border border-border/40 bg-background/30 p-3"
    >
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <Plus className="size-3" />
        <span>Subscribe to channel</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/@channel"
          disabled={status === "loading"}
          className="flex-1 rounded-md border border-border/60 bg-background/40 px-2.5 py-1.5 text-xs outline-none transition-colors focus:border-primary/60 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={status === "loading" || !url.trim()}
          className="inline-flex h-7 items-center gap-1.5 rounded-md px-3 text-xs font-medium text-white transition-transform active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            background: "var(--gradient-primary)",
            boxShadow: "var(--shadow-glow-primary)",
          }}
        >
          {status === "loading" ? (
            <>
              <Loader2 className="size-3 animate-spin" />
              <span>Subscribing…</span>
            </>
          ) : (
            <>
              <Plus className="size-3" />
              <span>Subscribe</span>
            </>
          )}
        </button>
      </div>
      {status === "success" && (
        <div className="flex items-center gap-1.5 text-[11px] text-success">
          <Check className="size-3" />
          <span>Subscribed to {created}</span>
        </div>
      )}
      {status === "error" && (
        <div className="flex items-center gap-1.5 text-[11px] text-destructive">
          <AlertCircle className="size-3" />
          <span>{error}</span>
        </div>
      )}
    </form>
  );
}

function ChannelIngestForm() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [count, setCount] = useState<number>(0);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed || status === "loading") return;
    setStatus("loading");
    setError("");
    try {
      const res = await api.ytChannel(trimmed);
      setCount(res.ingested_count);
      setStatus("success");
      setUrl("");
    } catch (e: any) {
      setStatus("error");
      setError(e?.message || "Channel ingest failed");
    }
  };

  return (
    <form
      onSubmit={submit}
      className="flex flex-col gap-2 rounded-lg border border-border/40 bg-background/30 p-3"
    >
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <Download className="size-3" />
        <span>One-off channel ingest</span>
      </div>
      <div className="flex items-center gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/@channel"
          disabled={status === "loading"}
          className="flex-1 rounded-md border border-border/60 bg-background/40 px-2.5 py-1.5 text-xs outline-none transition-colors focus:border-accent-teal/60 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={status === "loading" || !url.trim()}
          className="inline-flex h-7 items-center gap-1.5 rounded-md border border-accent-teal/40 bg-accent-teal/10 px-3 text-xs font-medium text-accent-teal transition-colors hover:border-accent-teal/60 hover:bg-accent-teal/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === "loading" ? (
            <>
              <Loader2 className="size-3 animate-spin" />
              <span>Ingesting…</span>
            </>
          ) : (
            <>
              <Download className="size-3" />
              <span>Ingest</span>
            </>
          )}
        </button>
      </div>
      {status === "success" && (
        <div className="flex items-center gap-1.5 text-[11px] text-success">
          <Check className="size-3" />
          <span>Ingested {count} video{count === 1 ? "" : "s"}</span>
        </div>
      )}
      {status === "error" && (
        <div className="flex items-center gap-1.5 text-[11px] text-destructive">
          <AlertCircle className="size-3" />
          <span>{error}</span>
        </div>
      )}
    </form>
  );
}

function SubscriptionRow({
  sub,
  onUnsubscribed,
}: {
  sub: Subscription;
  onUnsubscribed: () => void | Promise<void>;
}) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");

  const handleUnsubscribe = async () => {
    if (status === "loading") return;
    setStatus("loading");
    setError("");
    try {
      await api.ytUnsubscribe(sub.id);
      setStatus("success");
      await onUnsubscribed();
    } catch (e: any) {
      setStatus("error");
      setError(e?.message || "Unsubscribe failed");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.2 }}
      className="flex items-start gap-3 rounded-lg border border-border/40 bg-background/30 p-2.5 transition-colors hover:border-border/70 hover:bg-background/50"
    >
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border border-red-400/30 bg-red-400/10 text-red-400">
        <Youtube className="size-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <a
          href={sub.channel_url}
          target="_blank"
          rel="noopener noreferrer"
          className="block truncate text-sm font-medium text-foreground transition-colors hover:text-primary"
        >
          {sub.channel_name}
        </a>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Clock className="size-2.5" />
            <span>checked {formatRelative(sub.last_checked)}</span>
          </span>
          {sub.fail_count > 0 && (
            <>
              <span className="opacity-50">·</span>
              <span className="text-destructive/80">
                {sub.fail_count} fail{sub.fail_count === 1 ? "" : "s"}
              </span>
            </>
          )}
        </div>
        {status === "error" && error && (
          <div className="mt-1 text-[10px] text-destructive">{error}</div>
        )}
      </div>
      <button
        onClick={handleUnsubscribe}
        disabled={status === "loading" || status === "success"}
        className="inline-flex h-7 items-center gap-1 rounded-md border border-border/40 px-2 text-[11px] font-medium text-muted-foreground transition-colors hover:border-destructive/40 hover:bg-destructive/10 hover:text-destructive disabled:cursor-not-allowed disabled:opacity-50"
        aria-label="Unsubscribe"
      >
        {status === "loading" ? (
          <Loader2 className="size-3 animate-spin" />
        ) : (
          <Trash2 className="size-3" />
        )}
      </button>
    </motion.div>
  );
}

export function SubscriptionsPanel() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setStatus("loading");
    setError("");
    try {
      const data = await api.ytSubscriptions();
      setSubs(data);
      setStatus("success");
    } catch (e: any) {
      setStatus("error");
      setError(e?.message || "Failed to load subscriptions");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Rss className="size-3.5 text-accent-teal" />
          <span>
            {status === "loading" && subs.length === 0 ? (
              "Loading…"
            ) : (
              <>
                <span className="font-semibold text-foreground">{subs.length}</span>{" "}
                active subscription{subs.length === 1 ? "" : "s"}
              </>
            )}
          </span>
        </div>
        <button
          onClick={load}
          disabled={status === "loading"}
          className="inline-flex h-6 items-center gap-1 rounded-md border border-border/40 px-1.5 text-[11px] text-muted-foreground transition-colors hover:border-border/70 hover:text-foreground disabled:opacity-50"
          aria-label="Refresh subscriptions"
        >
          <RefreshCw className={`size-3 ${status === "loading" ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {status === "error" && error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          <AlertCircle className="size-3" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        {subs.length === 0 && status !== "loading" ? (
          <div className="flex flex-col items-center gap-2 py-6 text-center text-xs text-muted-foreground">
            <Rss className="size-5 opacity-40" />
            <span>No subscriptions yet. Add one below.</span>
          </div>
        ) : (
          subs.map((s) => (
            <SubscriptionRow key={s.id} sub={s} onUnsubscribed={load} />
          ))
        )}
      </div>

      <SubscribeForm onSubscribed={load} />
      <ChannelIngestForm />
    </div>
  );
}
