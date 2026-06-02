import { AnimatePresence, motion } from "motion/react";
import { X, Network, Trash2, ArrowRight, ArrowLeft } from "lucide-react";

export interface NodeConcept {
  id: string | number;
  label: string;
  type?: string;
  description?: string;
  tags?: string[];
  connections?: number;
  color?: string;
}

export interface SelectedEdge {
  rel_id: number;
  label: string;
  otherLabel: string;
  direction: "out" | "in";
}

export function NodeDetailsPanel({
  concept,
  edges = [],
  onDeleteRelation,
  deletingRelId = null,
  onClose,
}: {
  concept: NodeConcept | null;
  edges?: SelectedEdge[];
  onDeleteRelation?: (rel_id: number) => Promise<void> | void;
  deletingRelId?: number | null;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {concept && (
        <motion.aside
          initial={{ x: 360, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 360, opacity: 0 }}
          transition={{ type: "spring", stiffness: 220, damping: 26 }}
          className="absolute right-0 top-0 z-20 flex h-full w-80 flex-col border-l border-white/10 p-5"
          style={{
            background: "oklch(0.20 0.028 265 / 55%)",
            backdropFilter: "blur(18px)",
          }}
        >
          <div className="flex items-center justify-between">
            <div className="text-[10px] font-semibold tracking-[0.2em] text-muted-foreground">
              NODE DETAILS
            </div>
            <button
              onClick={onClose}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Close"
            >
              <X className="size-3.5" strokeWidth={1.5} />
            </button>
          </div>
          <div className="mt-6 flex items-center gap-3">
            <div
              className="size-10 rounded-full"
              style={{
                background: `radial-gradient(circle at 35% 30%, oklch(0.95 0 0 / 60%) 0%, ${concept.color || "var(--node-ai)"} 40%, oklch(0.18 0.04 265) 100%)`,
                boxShadow: `0 0 24px ${concept.color || "var(--node-ai)"}`,
              }}
            />
            <div>
              <div className="text-lg font-semibold">{concept.label}</div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                {concept.type || "concept"}
              </div>
            </div>
          </div>
          {concept.description && (
            <p className="mt-5 text-sm leading-relaxed text-muted-foreground">
              {concept.description}
            </p>
          )}
          {concept.tags && concept.tags.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-1.5">
              {concept.tags.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-surface/70 px-2.5 py-0.5 text-[10px] text-foreground/80"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
          <div className="mt-6 flex items-center gap-2 rounded-xl border border-border/50 p-3 text-xs text-muted-foreground">
            <Network className="size-3" />
            <span>
              <span className="text-foreground">
                {concept.connections ?? 0}
              </span>{" "}
              connections
            </span>
          </div>

          {edges.length > 0 && (
            <div className="mt-6 flex min-h-0 flex-1 flex-col">
              <div className="text-[10px] font-semibold tracking-[0.2em] text-muted-foreground">
                RELATIONSHIPS
              </div>
              <ul className="mt-2 flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pr-1">
                {edges.map((edge) => {
                  const isDeleting = deletingRelId === edge.rel_id;
                  return (
                    <li
                      key={edge.rel_id}
                      className="group flex items-center gap-2 rounded-lg border border-border/40 bg-surface/40 px-2.5 py-1.5"
                    >
                      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-surface/70 text-muted-foreground">
                        {edge.direction === "out" ? (
                          <ArrowRight className="size-3" strokeWidth={1.5} />
                        ) : (
                          <ArrowLeft className="size-3" strokeWidth={1.5} />
                        )}
                      </span>
                      <div className="min-w-0 flex-1 text-xs">
                        <div className="truncate text-foreground/90">
                          {edge.otherLabel}
                        </div>
                        <div className="truncate text-[10px] text-muted-foreground">
                          {edge.label}
                        </div>
                      </div>
                      {onDeleteRelation && (
                        <button
                          onClick={() => onDeleteRelation(edge.rel_id)}
                          disabled={isDeleting || deletingRelId != null}
                          className="flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/15 hover:text-destructive disabled:opacity-50"
                          aria-label={`Delete relation with ${edge.otherLabel}`}
                          title="Delete relation"
                        >
                          <Trash2 className="size-3" strokeWidth={1.5} />
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
