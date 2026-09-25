import { useEffect, useState } from "react";

import { getCompanyTimezone } from "@/utils/timezone";

export function LiveClock() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const date = new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    timeZone: getCompanyTimezone(),
  }).format(now);
  const time = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: getCompanyTimezone(),
  }).format(now);

  return (
    <div className="hidden items-baseline gap-2 font-mono text-sm text-ink-muted md:flex">
      <span>{date}</span>
      <span className="tabular-nums text-ink">{time}</span>
    </div>
  );
}
