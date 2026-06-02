import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

type Data = {
  label: string;
  color: string;
  delay: number;
};

export const GraphNode = memo(({ data, selected }: NodeProps<Data>) => {
  return (
    <div className="flex flex-col items-center gap-2">
      <Handle type="target" position={Position.Top} className="!opacity-0" />
      <div
        className="float-sway relative size-12 rounded-full transition-transform"
        style={{
          animationDelay: `${data.delay}s`,
          background: `radial-gradient(circle at 35% 30%, oklch(0.95 0 0 / 60%) 0%, ${data.color} 35%, oklch(0.2 0.04 265) 100%)`,
          boxShadow: selected
            ? `0 0 0 2px ${data.color}, 0 0 30px ${data.color}, 0 0 60px ${data.color}`
            : `0 0 18px ${data.color}`,
          transform: selected ? "scale(1.1)" : undefined,
        }}
      >
        <div
          aria-hidden
          className="absolute inset-[-12px] rounded-full"
          style={{
            background: `radial-gradient(circle, ${data.color} 0%, transparent 70%)`,
            opacity: selected ? 0.35 : 0.18,
            filter: "blur(6px)",
          }}
        />
      </div>
      <div className="text-xs font-medium tracking-wide text-foreground/90">
        {data.label}
      </div>
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
    </div>
  );
});
GraphNode.displayName = "GraphNode";
