import { useEffect, useState } from "react";

import { api } from "@/services/api";

export function useAuthenticatedImage(url: string | null | undefined): string | null {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!url) {
      setBlobUrl(null);
      return;
    }
    // `url` comes from the backend as an absolute "/api/..." path; the `api`
    // client's own baseURL already includes "/api", so strip it to avoid doubling.
    const relativePath = url.startsWith("/api") ? url.slice(4) : url;

    let cancelled = false;
    let createdUrl: string | null = null;

    api
      .get(relativePath, { responseType: "blob" })
      .then((response) => {
        if (cancelled) return;
        createdUrl = URL.createObjectURL(response.data as Blob);
        setBlobUrl(createdUrl);
      })
      .catch(() => {
        if (!cancelled) setBlobUrl(null);
      });

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [url]);

  return blobUrl;
}
