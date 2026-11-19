import { Label } from "@/components/ui/label";

export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor} className="text-[13px] font-medium">
        {label}
      </Label>
      {hint ? <p className="text-[12px] leading-5 text-faint">{hint}</p> : null}
      {children}
      {error ? <p className="text-[12px] text-destructive">{error}</p> : null}
    </div>
  );
}
