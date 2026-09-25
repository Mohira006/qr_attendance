import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { useAuth } from "@/contexts/AuthContext";
import { tokenStorage } from "@/services/tokenStorage";
import type { AttendanceResponse, NotificationResponse } from "@/types/models";

type ConnectionState = "connecting" | "open" | "closed";

interface LiveAttendanceEvent {
  type: "attendance.checked_in" | "attendance.checked_out";
  attendanceId: number;
  employeeId: number;
  status: AttendanceResponse["status"];
  at: number; // Date.now() - lets consumers expire a "just happened" flash after a few seconds
}

interface WebSocketContextValue {
  connectionState: ConnectionState;
  lastEvent: LiveAttendanceEvent | null;
}

const WebSocketContext = createContext<WebSocketContextValue>({ connectionState: "closed", lastEvent: null });

const MAX_BACKOFF_MS = 30_000;
const BASE_BACKOFF_MS = 1_000;

type IncomingMessage =
  | { type: "attendance.checked_in" | "attendance.checked_out"; data: AttendanceResponse }
  | { type: "notification.new"; data: NotificationResponse };

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [connectionState, setConnectionState] = useState<ConnectionState>("closed");
  const [lastEvent, setLastEvent] = useState<LiveAttendanceEvent | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (!user) {
      return;
    }
    stoppedRef.current = false;

    function connect() {
      const token = tokenStorage.getAccessToken();
      if (!token) return;

      setConnectionState("connecting");
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${protocol}://${window.location.host}/ws?token=${encodeURIComponent(token)}`);
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        setConnectionState("open");
        // A reconnect may have missed events while disconnected (edge cases:
        // network drop, backend restart) - refresh the views that show live state.
        void queryClient.invalidateQueries({ queryKey: ["attendance"] });
        void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      };

      socket.onmessage = (event) => {
        let payload: IncomingMessage;
        try {
          payload = JSON.parse(event.data as string) as IncomingMessage;
        } catch {
          return;
        }

        if (payload.type === "attendance.checked_in" || payload.type === "attendance.checked_out") {
          setLastEvent({
            type: payload.type,
            attendanceId: payload.data.id,
            employeeId: payload.data.employee.id,
            status: payload.data.status,
            at: Date.now(),
          });
          void queryClient.invalidateQueries({ queryKey: ["attendance"] });
          void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
        } else if (payload.type === "notification.new") {
          void queryClient.invalidateQueries({ queryKey: ["notifications"] });
        }
      };

      socket.onclose = () => {
        setConnectionState("closed");
        socketRef.current = null;
        if (stoppedRef.current) return;
        const delay = Math.min(BASE_BACKOFF_MS * 2 ** attemptRef.current, MAX_BACKOFF_MS);
        attemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      stoppedRef.current = true;
      clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [user, queryClient]);

  return <WebSocketContext.Provider value={{ connectionState, lastEvent }}>{children}</WebSocketContext.Provider>;
}

export function useLiveUpdates(): WebSocketContextValue {
  return useContext(WebSocketContext);
}
