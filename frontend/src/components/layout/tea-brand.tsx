import { Leaf } from "lucide-react";
import { cn } from "@/lib/utils";

export function TeaBrand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-amber text-amber-foreground shadow-soft">
        <Leaf className="size-5" strokeWidth={2} />
      </div>
      <div
        className={cn("min-w-0 group-data-[collapsible=icon]:hidden", compact && "hidden sm:block")}
      >
        <p className="font-display text-lg font-semibold leading-tight">Tea Scholar</p>
        <p className="truncate text-[11px] tracking-wide text-current/60">
          Trợ lý tri thức cây chè
        </p>
      </div>
    </div>
  );
}
