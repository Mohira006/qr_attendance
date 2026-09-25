// Attendance times must always read in the office's configured timezone, not the
// viewing browser's local zone (an HR user checking in remotely should still see
// "09:15", not their own local time). Settings load once per session and set this.
let companyTimezone = "UTC";

export function setCompanyTimezone(timezone: string): void {
  companyTimezone = timezone;
}

export function getCompanyTimezone(): string {
  return companyTimezone;
}
