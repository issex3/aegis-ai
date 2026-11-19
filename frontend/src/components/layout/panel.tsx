import { cn } from "@/lib/utils";

type PanelProps = React.ComponentProps<"section"> & {
  inset?: boolean;
  padded?: boolean;
};

/** Premium tonal surface — hairline + soft shine. */
export function Panel({ className, inset = false, padded = true, ...props }: PanelProps) {
  return (
    <section
      className={cn(
        inset ? "surface-inset" : "surface",
        "rounded-md",
        padded && "p-4 md:p-5",
        className,
      )}
      {...props}
    />
  );
}
