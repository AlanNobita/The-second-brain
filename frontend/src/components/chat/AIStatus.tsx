import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function AIStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await api.health();
        if (!cancelled) setOnline(res.status === "ok");
      } catch {
        if (!cancelled) setOnline(false);
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span
        className="pulse-dot block size-2 rounded-full"
        style={{ background: online === false ? "var(--destructive)" : "var(--success)" }}
      />
      <span className="tracking-wide">
        {online === false ? "Offline" : "AI Active"}
      </span>
    </div>
  );
}
