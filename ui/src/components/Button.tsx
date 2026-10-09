import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const variants = {
  primary: "bg-[var(--accent)] text-[var(--on-accent)] hover:bg-[var(--accent-hover)]",
  secondary:
    "border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:border-[var(--border-strong)] hover:bg-[var(--hover)]",
  ghost: "text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--foreground)]",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof variants }
>(function Button({ variant = "primary", className, type = "button", ...props }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
});
