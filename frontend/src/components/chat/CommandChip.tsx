import { motion } from "motion/react";

interface CommandChipProps {
  label: string;
  onClick?: () => void;
}

export function CommandChip({ label, onClick }: CommandChipProps) {
  return (
    <motion.button
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.96 }}
      onClick={onClick}
      className="group rounded-full border border-white/5 bg-surface/60 px-3.5 py-1.5 font-mono text-xs text-muted-foreground transition-all hover:border-primary/60 hover:text-foreground"
      style={{ backdropFilter: "blur(6px)" }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow =
          "0 0 16px oklch(0.62 0.22 290 / 30%)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.boxShadow = "none";
      }}
    >
      {label}
    </motion.button>
  );
}
