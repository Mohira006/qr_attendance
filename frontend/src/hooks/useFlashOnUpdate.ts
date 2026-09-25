import { useEffect, useState } from "react";

import { useLiveUpdates } from "@/contexts/WebSocketContext";

const FLASH_DURATION_MS = 1800;

export function useFlashOnUpdate(attendanceId: number): boolean {
  const { lastEvent } = useLiveUpdates();
  const [flashing, setFlashing] = useState(false);

  useEffect(() => {
    if (lastEvent?.attendanceId !== attendanceId) return;
    setFlashing(true);
    const timer = setTimeout(() => setFlashing(false), FLASH_DURATION_MS);
    return () => clearTimeout(timer);
  }, [lastEvent, attendanceId]);

  return flashing;
}
