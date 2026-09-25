import { useLanguage } from "@/hooks/useLanguage";
import type { Language } from "@/types/enums";
import { cn } from "@/utils/cn";

const LANGUAGES: { code: Language; label: string }[] = [
  { code: "uz", label: "UZ" },
  { code: "ru", label: "RU" },
  { code: "en", label: "EN" },
];

export function LanguageSwitcher({ variant = "light" }: { variant?: "light" | "dark" }) {
  const { currentLanguage, changeLanguage } = useLanguage();

  return (
    <div
      className={cn("flex items-center gap-0.5 rounded-lg p-0.5", variant === "dark" ? "bg-white/10" : "bg-canvas")}
      role="group"
      aria-label="Language"
    >
      {LANGUAGES.map(({ code, label }) => {
        const isActive = currentLanguage === code;
        return (
          <button
            key={code}
            type="button"
            onClick={() => void changeLanguage(code)}
            aria-pressed={isActive}
            className={cn(
              "rounded-md px-2 py-1 text-xs font-semibold transition-colors",
              isActive
                ? variant === "dark"
                  ? "bg-white text-ink"
                  : "bg-brand text-white"
                : variant === "dark"
                  ? "text-white/60 hover:text-white"
                  : "text-ink-muted hover:text-ink",
            )}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
