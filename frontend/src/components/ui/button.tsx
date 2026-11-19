import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-[13px] font-medium transition-[background,border-color,color,transform,box-shadow] duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default:
          "bg-signal text-primary-foreground shadow-[0_0_0_1px_rgba(91,141,239,0.35),0_8px_24px_-12px_rgba(91,141,239,0.55)] hover:bg-[#6b9af3]",
        secondary: "bg-secondary text-secondary-foreground border border-border hover:border-white/20 hover:bg-secondary/80",
        outline: "border border-border bg-transparent hover:bg-white/[0.04] hover:border-white/18",
        ghost: "text-muted-foreground hover:bg-white/[0.04] hover:text-foreground",
        destructive: "bg-destructive text-white hover:bg-destructive/90",
      },
      size: {
        default: "h-10 px-3.5 md:h-8",
        sm: "h-9 px-2.5 text-[12px] md:h-7",
        lg: "h-11 px-4 md:h-9",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
