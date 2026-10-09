import { SearchX } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  subtitle,
  eyebrow,
  action,
}: {
  title: string;
  subtitle: string;
  eyebrow?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
      <div>
        {eyebrow && (
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-primary">
            {eyebrow}
          </p>
        )}
        <h1 className="text-3xl font-semibold text-foreground sm:text-4xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
          {subtitle}
        </p>
      </div>
      {action}
    </div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  className?: string;
}) {
  return (
    <div className={cn("mb-8 max-w-2xl", className)}>
      {eyebrow && (
        <p className="text-xs font-semibold uppercase tracking-widest text-primary">{eyebrow}</p>
      )}
      <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">{title}</h2>
      {description && (
        <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">{description}</p>
      )}
    </div>
  );
}

export function IconBadge({ icon: Icon, className }: { icon: LucideIcon; className?: string }) {
  return (
    <div
      className={cn(
        "grid size-11 shrink-0 place-items-center rounded-xl bg-tea-soft text-primary",
        className,
      )}
    >
      <Icon className="size-5" />
    </div>
  );
}

export function EmptyState({
  title = "Không tìm thấy kết quả",
  description = "Hãy thử nhập từ khóa rộng hơn hoặc dùng cách diễn đạt khác.",
  icon: Icon = SearchX,
  children,
}: {
  title?: string;
  description?: string;
  icon?: LucideIcon;
  children?: ReactNode;
}) {
  return (
    <div className="grid min-h-64 place-items-center rounded-2xl border border-dashed bg-card/60 p-8 text-center">
      <div className="max-w-md">
        <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-tea-soft text-primary">
          <Icon className="size-7" />
        </div>
        <h2 className="mt-5 text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
        {children && <div className="mt-5">{children}</div>}
      </div>
    </div>
  );
}
