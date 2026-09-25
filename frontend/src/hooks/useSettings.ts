import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { settingsApi } from "@/services/settingsApi";
import { setCompanyTimezone } from "@/utils/timezone";

export function useSettings() {
  const query = useQuery({ queryKey: ["settings"], queryFn: settingsApi.get, staleTime: 5 * 60 * 1000 });

  useEffect(() => {
    if (query.data) {
      setCompanyTimezone(query.data.timezone);
    }
  }, [query.data]);

  return query;
}
