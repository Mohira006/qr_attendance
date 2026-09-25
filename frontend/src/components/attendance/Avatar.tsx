import { useAuthenticatedImage } from "@/hooks/useAuthenticatedImage";
import type { EmployeeBrief } from "@/types/models";

export function Avatar({ employee, size = 32 }: { employee: EmployeeBrief; size?: number }) {
  const photoUrl = useAuthenticatedImage(employee.profile_photo_url);
  const initials = `${employee.first_name.charAt(0)}${employee.last_name.charAt(0)}`.toUpperCase();

  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={employee.full_name}
        className="shrink-0 rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full bg-brand-light font-display font-semibold text-brand"
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      aria-hidden
    >
      {initials}
    </div>
  );
}
