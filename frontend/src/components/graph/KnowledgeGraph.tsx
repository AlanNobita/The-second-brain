import { useEffect, useMemo, useState, useCallback } from "react";
import { AnimatePresence } from "motion/react";
import ReactFlow, {
  Background,
  Controls,
  type Edge,
  type Node,
  useEdgesState,
  useNodesState,
  type NodeMouseHandler,
} from "reactflow";
import "reactflow/dist/style.css";
import { motion } from "motion/react";
import { Search, Loader2, AlertCircle, Plus, X, Link2 } from "lucide-react";
import { GraphNode } from "./GraphNode";
import { ParticleField } from "./ParticleField";
import { NodeDetailsPanel, type NodeConcept } from "./NodeDetailsPanel";
import { api } from "@/lib/api";
import type { GraphData } from "@/lib/types";

const nodeTypes = { concept: GraphNode };

const NODE_COLORS = [
  "oklch(0.82 0.17 90)",
  "oklch(0.72 0.18 155)",
  "oklch(0.75 0.15 220)",
  "oklch(0.68 0.22 320)",
  "oklch(0.78 0.15 30)",
  "oklch(0.70 0.18 200)",
  "oklch(0.65 0.20 350)",
  "oklch(0.78 0.16 60)",
];

function layoutCircle(count: number, radius = 240) {
  return Array.from({ length: count }, (_, i) => {
    const a = (i / count) * Math.PI * 2 - Math.PI / 2;
    return { x: Math.cos(a) * radius, y: Math.sin(a) * radius };
  });
}

interface KnowledgeGraphProps {
  focusLabel?: string | null;
  onFocusConsumed?: () => void;
}

export function KnowledgeGraph({ focusLabel = null, onFocusConsumed }: KnowledgeGraphProps = {}) {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<NodeConcept | null>(null);
  const [search, setSearch] = useState("");
  const [focused, setFocused] = useState(false);
  const [entityName, setEntityName] = useState("");
  const [entityType, setEntityType] = useState("concept");
  const [entityDesc, setEntityDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [showRelationForm, setShowRelationForm] = useState(false);
  const [relSource, setRelSource] = useState("");
  const [relTarget, setRelTarget] = useState("");
  const [relType, setRelType] = useState("related to");
  const [creatingRelation, setCreatingRelation] = useState(false);
  const [deletingRelId, setDeletingRelId] = useState<number | null>(null);

  const load = useCallback(async (q?: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getGraph(q);
      setGraph(data);
    } catch (e: any) {
      setError(e.message || "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const initialNodes: Node[] = useMemo(() => {
    if (!graph) return [];
    const positions = layoutCircle(graph.nodes.length, 240);
    return graph.nodes.map((n, i) => ({
      id: String(n.id),
      type: "concept",
      position: positions[i] || { x: 0, y: 0 },
      data: {
        label: n.label,
        color: NODE_COLORS[i % NODE_COLORS.length],
        delay: (i % 6) * 0.4,
      },
    }));
  }, [graph]);

  const initialEdges: Edge[] = useMemo(() => {
    if (!graph) return [];
    return graph.edges.map((e, i) => ({
      id: `e${i}`,
      source: String(e.from),
      target: String(e.to),
      type: "smoothstep",
      label: e.label,
    }));
  }, [graph]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
  }, [initialNodes, setNodes]);

  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);

  useEffect(() => {
    if (!focusLabel) return;
    setSearch(focusLabel);
    load(focusLabel);
    onFocusConsumed?.();
  }, [focusLabel, load, onFocusConsumed]);

  useEffect(() => {
    return () => {
      setSearch("");
      setFocused(false);
    };
  }, []);

  useEffect(() => {
    if (!graph) return;
    setEdges((eds) =>
      eds.map((e) => {
        const isConnected =
          selected &&
          (String(e.source) === String(selected.id) ||
            String(e.target) === String(selected.id));
        return { ...e, className: isConnected ? "connected" : "" };
      })
    );
  }, [selected, setEdges, graph]);

  const onNodeClick: NodeMouseHandler = (_e, node) => {
    if (!graph) return;
    const n = graph.nodes.find((x) => String(x.id) === String(node.id));
    if (!n) return;
    setSelected({
      id: n.id,
      label: n.label,
      type: n.title,
      description: n.description,
      color: node.data.color,
      connections: graph.edges.filter(
        (e) => String(e.from) === String(n.id) || String(e.to) === String(n.id)
      ).length,
    });
  };

  const handleSearch = (q: string) => {
    setSearch(q);
    if (q.trim()) {
      load(q.trim());
    } else {
      load();
    }
  };

  const handleCreate = async () => {
    if (!entityName.trim() || creating) return;
    try {
      setCreating(true);
      await api.createEntity(entityName.trim(), entityType, entityDesc.trim());
      setEntityName("");
      setEntityDesc("");
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to create entity");
    } finally {
      setCreating(false);
    }
  };

  const handleCreateRelation = async () => {
    if (
      !relSource.trim() ||
      !relTarget.trim() ||
      relSource.trim() === relTarget.trim() ||
      creatingRelation
    ) {
      return;
    }
    try {
      setCreatingRelation(true);
      setError(null);
      await api.createRelation(
        relSource.trim(),
        relTarget.trim(),
        relType.trim() || "related to"
      );
      setRelSource("");
      setRelTarget("");
      setRelType("related to");
      setShowRelationForm(false);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to create relation");
    } finally {
      setCreatingRelation(false);
    }
  };

  const handleDeleteRelation = async (rel_id: number) => {
    if (deletingRelId != null) return;
    try {
      setDeletingRelId(rel_id);
      setError(null);
      await api.deleteRelation(rel_id);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to delete relation");
    } finally {
      setDeletingRelId(null);
    }
  };

  const selectedEdges = useMemo(() => {
    if (!selected || !graph) return [];
    return graph.edges
      .filter(
        (e) =>
          e.rel_id != null &&
          (String(e.from) === String(selected.id) ||
            String(e.to) === String(selected.id))
      )
      .map((e) => {
        const isOutgoing = String(e.from) === String(selected.id);
        const otherId = isOutgoing ? e.to : e.from;
        const otherNode = graph.nodes.find(
          (n) => String(n.id) === String(otherId)
        );
        return {
          rel_id: e.rel_id as number,
          label: e.label || "related to",
          otherLabel: otherNode?.label || String(otherId),
          direction: isOutgoing ? ("out" as const) : ("in" as const),
        };
      });
  }, [selected, graph]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="relative flex h-full flex-col"
    >
      <header className="flex items-center justify-between border-b border-border/40 px-6 py-4">
        <div>
          <div className="text-sm font-semibold">Knowledge Graph</div>
          <div className="mt-1 text-xs text-muted-foreground">
            {graph ? `${graph.nodes.length} concepts · ${graph.edges.length} relationships` : "Loading…"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {graph && graph.nodes.length > 0 && (
            <button
              onClick={() => setShowRelationForm((s) => !s)}
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-surface/70 hover:text-foreground"
              aria-label="Toggle add relation form"
            >
              {showRelationForm ? (
                <X className="size-3.5" strokeWidth={1.5} />
              ) : (
                <Link2 className="size-3.5" strokeWidth={1.5} />
              )}
              {showRelationForm ? "Close" : "Connect"}
            </button>
          )}
          <motion.div
            animate={{
              boxShadow: focused
                ? "0 0 0 1px oklch(0.62 0.22 290 / 60%), 0 0 16px oklch(0.62 0.22 290 / 25%)"
                : "0 0 0 1px transparent",
            }}
            transition={{ duration: 0.25 }}
            className="flex items-center gap-2 rounded-lg bg-surface/70 px-3 py-1.5"
          >
            <Search className="size-3.5 text-muted-foreground" strokeWidth={1.5} />
            <input
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="Search concepts..."
              className="w-48 bg-transparent text-xs text-foreground outline-none placeholder:text-muted-foreground"
            />
          </motion.div>
        </div>
      </header>

      <AnimatePresence>
        {showRelationForm && graph && graph.nodes.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-b border-border/40"
          >
            <div className="flex flex-wrap items-end gap-2 px-6 py-3">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  Source
                </label>
                <select
                  value={relSource}
                  onChange={(e) => setRelSource(e.target.value)}
                  className="min-w-[10rem] rounded-md border border-border/60 bg-surface/40 px-2.5 py-1.5 text-xs outline-none focus:border-primary/60"
                >
                  <option value="">Select concept…</option>
                  {graph.nodes.map((n) => (
                    <option key={String(n.id)} value={n.label}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  Relationship
                </label>
                <input
                  value={relType}
                  onChange={(e) => setRelType(e.target.value)}
                  placeholder="related to"
                  className="w-40 rounded-md border border-border/60 bg-surface/40 px-2.5 py-1.5 text-xs outline-none focus:border-primary/60"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  Target
                </label>
                <select
                  value={relTarget}
                  onChange={(e) => setRelTarget(e.target.value)}
                  className="min-w-[10rem] rounded-md border border-border/60 bg-surface/40 px-2.5 py-1.5 text-xs outline-none focus:border-primary/60"
                >
                  <option value="">Select concept…</option>
                  {graph.nodes.map((n) => (
                    <option key={String(n.id)} value={n.label}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleCreateRelation}
                disabled={
                  creatingRelation ||
                  !relSource.trim() ||
                  !relTarget.trim() ||
                  relSource.trim() === relTarget.trim()
                }
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                style={{
                  background: "var(--gradient-primary)",
                  boxShadow: "var(--shadow-glow-primary)",
                }}
              >
                {creatingRelation ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <Plus className="size-3" />
                )}
                Create
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative flex-1 overflow-hidden">
        <ParticleField />

        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/40 backdrop-blur-sm">
            <Loader2 className="size-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <div className="absolute left-1/2 top-4 z-10 flex -translate-x-1/2 items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            <AlertCircle className="size-3" />
            <span>{error}</span>
          </div>
        )}

        {graph && !loading && graph.nodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-center">
            <div className="text-sm text-muted-foreground">
              Your knowledge graph is empty.
            </div>
            <div className="flex w-80 flex-col gap-2 rounded-xl border border-border/50 bg-surface/40 p-3">
              <input
                value={entityName}
                onChange={(e) => setEntityName(e.target.value)}
                placeholder="Concept name"
                className="rounded-md border border-border/60 bg-background/40 px-2.5 py-1.5 text-xs outline-none focus:border-primary/60"
              />
              <input
                value={entityType}
                onChange={(e) => setEntityType(e.target.value)}
                placeholder="Type (e.g. framework, ai, tool)"
                className="rounded-md border border-border/60 bg-background/40 px-2.5 py-1.5 text-xs outline-none focus:border-primary/60"
              />
              <input
                value={entityDesc}
                onChange={(e) => setEntityDesc(e.target.value)}
                placeholder="Short description (optional)"
                className="rounded-md border border-border/60 bg-background/40 px-2.5 py-1.5 text-xs outline-none focus:border-primary/60"
              />
              <button
                onClick={handleCreate}
                disabled={creating || !entityName.trim()}
                className="flex items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium text-white disabled:opacity-50"
                style={{
                  background: "var(--gradient-primary)",
                  boxShadow: "var(--shadow-glow-primary)",
                }}
              >
                <Plus className="size-3" />
                Add concept
              </button>
            </div>
          </div>
        )}

        {graph && graph.nodes.length > 0 && (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.3}
            maxZoom={1.6}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="oklch(0.55 0.08 240 / 15%)" gap={32} size={1} />
            <Controls position="bottom-right" showInteractive={false} />
          </ReactFlow>
        )}

        <NodeDetailsPanel
          concept={selected}
          edges={selectedEdges}
          onDeleteRelation={handleDeleteRelation}
          deletingRelId={deletingRelId}
          onClose={() => setSelected(null)}
        />
      </div>
    </motion.div>
  );
}
