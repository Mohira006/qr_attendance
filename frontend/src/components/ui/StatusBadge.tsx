import { useTranslation } from "react-i18next";

import { cn } from "@/utils/cn";
import type { StatusTokens } from "@/utils/status";

export function StatusBadge({ tokens, className }: { tokens: StatusTokens; className?: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        tokens.bg,
        tokens.text,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", tokens.dot)} />
      {t(tokens.labelKey)}
    </span>
  );
}
