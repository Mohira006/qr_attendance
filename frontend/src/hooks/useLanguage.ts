import { useTranslation } from "react-i18next";

import { useAuth } from "@/contexts/AuthContext";
import { authApi } from "@/services/authApi";
import type { Language } from "@/types/enums";

interface UseLanguageResult {
  currentLanguage: Language;
  changeLanguage: (language: Language) => Promise<void>;
}

export function useLanguage(): UseLanguageResult {
  const { i18n } = useTranslation();
  const { user } = useAuth();

  async function changeLanguage(language: Language): Promise<void> {
    // Updates the UI immediately (and localStorage, via the detector's cache) -
    // this always succeeds and doesn't depend on the network.
    await i18n.changeLanguage(language);
    if (user) {
      try {
        await authApi.updateLanguage(language);
      } catch {
        // Non-critical: the UI already reflects the change. A failed server sync
        // just means it won't follow the person to another device until they
        // change it again there too.
      }
    }
  }

  return { currentLanguage: i18n.language as Language, changeLanguage };
}
