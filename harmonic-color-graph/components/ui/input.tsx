import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      data-slot="input"
      type={type}
      className={cn(
        "selection:bg-primary selection:text-primary-foreground flex h-11 w-full min-w-0 rounded-lg border border-[var(--border-default)] bg-[var(--bg-input)] px-3 py-2 text-base text-[var(--text-primary)] transition-[color,border-color,box-shadow] outline-none placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)] disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-3",
        "aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Input }
