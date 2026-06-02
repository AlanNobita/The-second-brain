import { useState, type ReactNode } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Loader2,
  Check,
  AlertCircle,
  Youtube,
  X,
  ExternalLink,
  Download,
  BookOpen,
  Sparkles,
  Network,
  Plus,
  Hash,
  Calendar,
} from "lucide-react";
import { api } from "@/lib/api";
import type { YoutubeResult, Reflection } from "@/lib/types";

export interface KGEntity {
  id?: number;
  name: string;
  type?: string;
  description?: string;
}

export type CommandResult =
  | { kind: "youtube-search"; query: string; results: YoutubeResult[] }
  | { kind: "reflections"; reflections: Reflection[] }
  | { kind: "reflection-today"; reflection: Reflection | null }
  | { kind: "kg-list"; entities: KGEntity[] }
  | { kind: "kg-add"; entity: KGEntity }
  | { kind: "kg-help" };

interface CommandResultsProps {
  result: CommandResult;
  onDismiss: () => void;
  onNodeClick?: (label: string) => void;
}

function thumbnailUrl(videoId: string): string {
  return `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`;
}

function formatYMD(yyyymmdd?: string): string {
  if (!yyyymmdd || yyyymmdd.length !== 8) return yyyymmdd || "";
  const y = yyyymmdd.slice(0, 4);
  const m = yyyymmdd.slice(4, 6);
  const d = yyyymmdd.slice(6, 8);
  const date = new Date(`${y}-${m}-${d}T00:00:00Z`);
  if (isNaN(date.getTime())) return yyyymmdd;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

type IngestStatus = "idle" | "loading" | "success" | "error";

function YouTubeCard({ video, onNodeClick }: { video: YoutubeResult; onNodeClick?: (label: string) => void }) {
  const [status, setStatus] = useState<IngestStatus>("idle");
  const [error, setError] = useState<string>("");

  const handleIngest = async () => {
    setStatus("loading");
    try {
      await api.ytIngest(video.url);
      setStatus("success");
    } catch (e: any) {
      setStatus("error");
      setError(e?.message || "Ingest failed");
    }
  };

  return (
    <div className="flex items-stretch gap-3 rounded-lg border border-border/40 bg-background/30 p-2 transition-colors hover:border-border/70 hover:bg-background/50">
      <a
        href={video.url}
        target="_blank"
        rel="noopener noreferrer"
        className="relative block size-[88px] shrink-0 overflow-hidden rounded-md bg-surface"
      >
        <img
          src={thumbnailUrl(video.video_id)}
          alt={video.title}
          loading="lazy"
          className="size-full object-cover"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).style.display = "none";
          }}
        />
      </a>

      <div className="flex min-w-0 flex-1 flex-col">
        <a
          href={video.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={() => onNodeClick?.(video.title)}
          className="line-clamp-2 text-sm font-medium leading-snug text-foreground transition-colors hover:text-primary"
        >
          {video.title}
        </a>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
          {video.channel && <span className="truncate">{video.channel}</span>}
          {video.published_at && (
            <>
              <span className="opacity-50">·</span>
              <span>{formatYMD(video.published_at)}</span>
            </>
          )}
        </div>

        <div className="mt-auto flex items-center gap-2 pt-1.5">
          <button
            onClick={handleIngest}
            disabled={status === "loading" || status === "success"}
            className={`inline-flex h-6 items-center gap-1.5 rounded-md border px-2 text-[11px] font-medium transition-colors ${
              status === "success"
                ? "border-success/40 bg-success/10 text-success"
                : status === "error"
                ? "border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/15"
                : "border-primary/40 bg-primary/10 text-primary hover:border-primary/60 hover:bg-primary/15"
            } disabled:cursor-not-allowed disabled:opacity-70`}
          >
            {status === "loading" ? (
              <>
                <Loader2 className="size-3 animate-spin" />
                <span>Ingesting…</span>
              </>
            ) : status === "success" ? (
              <>
                <Check className="size-3" />
                <span>Ingested</span>
              </>
            ) : status === "error" ? (
              <>
                <AlertCircle className="size-3" />
                <span>Retry</span>
              </>
            ) : (
              <>
                <Download className="size-3" />
                <span>Ingest</span>
              </>
            )}
          </button>
          <a
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-6 items-center gap-1 rounded-md px-1.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
            title="Open on YouTube"
          >
            <ExternalLink className="size-3" />
          </a>
        </div>
        {status === "error" && error && (
          <div className="mt-1 text-[10px] text-destructive">{error}</div>
        )}
      </div>
    </div>
  );
}

function ReflectionCard({ reflection }: { reflection: Reflection }) {
  return (
    <div className="rounded-lg border border-border/40 bg-background/30 p-3 transition-colors hover:border-border/70 hover:bg-background/50">
      <div className="mb-1.5 flex items-center gap-2 text-[11px] text-muted-foreground">
        <Calendar className="size-3" />
        <span className="font-mono">{reflection.date}</span>
        {reflection.topics && reflection.topics.length > 0 && (
          <span className="ml-auto inline-flex items-center gap-1">
            {reflection.topics.slice(0, 2).map((t, i) => (
              <span
                key={i}
                className="rounded-full border border-border/60 bg-surface/60 px-1.5 py-0.5 text-[10px]"
              >
                {t}
              </span>
            ))}
          </span>
        )}
      </div>
      <p className="line-clamp-4 text-sm leading-relaxed text-foreground/90">
        {reflection.summary}
      </p>
    </div>
  );
}

function KGEntityCard({ entity }: { entity: KGEntity }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border/40 bg-background/30 p-2.5 transition-colors hover:border-border/70 hover:bg-background/50">
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary/10 text-primary">
        <Hash className="size-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <span className="truncate text-sm font-medium text-foreground">
            {entity.name}
          </span>
          {entity.type && (
            <span className="shrink-0 rounded-full border border-border/60 bg-surface/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
              {entity.type}
            </span>
          )}
        </div>
        {entity.description && (
          <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
            {entity.description}
          </p>
        )}
      </div>
    </div>
  );
}

function EmptyState({ icon, message }: { icon: ReactNode; message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center text-xs text-muted-foreground">
      {icon}
      <span>{message}</span>
    </div>
  );
}

function ResultHeader({
  icon,
  title,
  right,
  onDismiss,
}: {
  icon: ReactNode;
  title: ReactNode;
  right?: ReactNode;
  onDismiss: () => void;
}) {
  return (
    <div className="mb-3 flex items-center justify-between gap-2 border-b border-border/40 pb-2">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">{icon}{title}</div>
      <div className="flex items-center gap-2">
        {right}
        <button
          onClick={onDismiss}
          className="rounded p-1 text-muted-foreground transition-colors hover:bg-surface-hover hover:text-foreground"
          aria-label="Dismiss"
        >
          <X className="size-3.5" />
        </button>
      </div>
    </div>
  );
}

export function CommandResults({ result, onDismiss, onNodeClick }: CommandResultsProps) {
  let body: ReactNode;

  switch (result.kind) {
    case "youtube-search": {
      const { query, results } = result;
      body = (
        <>
          <ResultHeader
            icon={<Youtube className="size-3.5 text-red-400" />}
            title={
              <span>
                <span className="font-semibold text-foreground">{results.length}</span>{" "}
                result{results.length === 1 ? "" : "s"} for{" "}
                <span className="font-medium text-foreground">"{query}"</span>
              </span>
            }
            onDismiss={onDismiss}
          />
          <div className="flex flex-col gap-2">
            {results.length === 0 ? (
              <EmptyState
                icon={<Youtube className="size-5 opacity-40" />}
                message="No videos found. Try a different query."
              />
            ) : (
              results.map((v) => (
                <YouTubeCard key={v.video_id} video={v} onNodeClick={onNodeClick} />
              ))
            )}
          </div>
        </>
      );
      break;
    }

    case "reflections": {
      const { reflections } = result;
      body = (
        <>
          <ResultHeader
            icon={<BookOpen className="size-3.5 text-accent-teal" />}
            title={
              <span>
                <span className="font-semibold text-foreground">{reflections.length}</span>{" "}
                recent reflection{reflections.length === 1 ? "" : "s"}
              </span>
            }
            onDismiss={onDismiss}
          />
          <div className="flex flex-col gap-2">
            {reflections.length === 0 ? (
              <EmptyState
                icon={<BookOpen className="size-5 opacity-40" />}
                message="No daily reflections yet."
              />
            ) : (
              reflections.map((r) => (
                <ReflectionCard key={r.date} reflection={r} />
              ))
            )}
          </div>
        </>
      );
      break;
    }

    case "reflection-today": {
      const { reflection } = result;
      body = (
        <>
          <ResultHeader
            icon={<Sparkles className="size-3.5 text-primary" />}
            title={
              <span className="font-semibold text-foreground">Today's reflection</span>
            }
            onDismiss={onDismiss}
          />
          {reflection ? (
            <ReflectionCard reflection={reflection} />
          ) : (
            <EmptyState
              icon={<Sparkles className="size-5 opacity-40" />}
              message="No messages today to reflect on."
            />
          )}
        </>
      );
      break;
    }

    case "kg-list": {
      const { entities } = result;
      body = (
        <>
          <ResultHeader
            icon={<Network className="size-3.5 text-primary" />}
            title={
              <span>
                <span className="font-semibold text-foreground">{entities.length}</span>{" "}
                knowledge graph entit{entities.length === 1 ? "y" : "ies"}
              </span>
            }
            onDismiss={onDismiss}
          />
          <div className="flex flex-col gap-2">
            {entities.length === 0 ? (
              <EmptyState
                icon={<Network className="size-5 opacity-40" />}
                message="No entities yet. Try /kg add <name>[,type,desc]"
              />
            ) : (
              entities.map((e) => <KGEntityCard key={e.name} entity={e} />)
            )}
          </div>
        </>
      );
      break;
    }

    case "kg-add": {
      const { entity } = result;
      body = (
        <>
          <ResultHeader
            icon={<Check className="size-3.5 text-success" />}
            title={
              <span className="font-semibold text-foreground">Entity created</span>
            }
            onDismiss={onDismiss}
          />
          <KGEntityCard entity={entity} />
        </>
      );
      break;
    }

    case "kg-help": {
      body = (
        <>
          <ResultHeader
            icon={<Network className="size-3.5 text-primary" />}
            title={<span className="font-semibold text-foreground">KG commands</span>}
            onDismiss={onDismiss}
          />
          <div className="flex flex-col gap-1.5 text-sm">
            <div className="flex items-center gap-2 rounded-md border border-border/40 bg-background/30 px-2.5 py-1.5">
              <Plus className="size-3 text-muted-foreground" />
              <code className="font-mono text-xs text-foreground">/kg list</code>
              <span className="ml-auto text-[11px] text-muted-foreground">list entities</span>
            </div>
            <div className="flex items-center gap-2 rounded-md border border-border/40 bg-background/30 px-2.5 py-1.5">
              <Plus className="size-3 text-muted-foreground" />
              <code className="font-mono text-xs text-foreground">/kg add &lt;name&gt;[,type,desc]</code>
              <span className="ml-auto text-[11px] text-muted-foreground">create entity</span>
            </div>
            <div className="flex items-center gap-2 rounded-md border border-border/40 bg-background/30 px-2.5 py-1.5">
              <Plus className="size-3 text-muted-foreground" />
              <code className="font-mono text-xs text-foreground">/kg</code>
              <span className="ml-auto text-[11px] text-muted-foreground">open graph view</span>
            </div>
          </div>
        </>
      );
      break;
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.25 }}
      className="flex w-full justify-start"
    >
      <div className="w-full max-w-[78%] rounded-2xl border border-border/60 bg-surface/70 px-4 py-3 backdrop-blur">
        {body}
      </div>
    </motion.div>
  );
}

export function CommandResultsWrapper(props: CommandResultsProps) {
  return (
    <AnimatePresence>
      <CommandResults {...props} />
    </AnimatePresence>
  );
}
