import type { ReactNode } from "react";

import { Card, CardBody } from "@/components/ui/Card";
import { cn } from "@/utils/cn";

export function StatCard({
  label,
  value,
  icon,
  accentClass = "bg-brand-light text-brand",
}: {
  label: string;
  value: string | number;
  icon: ReactNode;
  accentClass?: string;
}) {
  return (
    <Card>
      <CardBody className="flex items-center gap-4">
        <div className={cn("flex h-11 w-11 shrink-0 items-center justify-center rounded-lg", accentClass)}>{icon}</div>
        <div className="min-w-0">
          <p className="truncate font-display text-2xl font-semibold tabular-nums text-ink">{value}</p>
          <p className="text-sm text-ink-muted">{label}</p>
        </div>
      </CardBody>
    </Card>
  );
}
