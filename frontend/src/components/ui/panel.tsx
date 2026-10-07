import * as React from "react";
import { cn } from "@/lib/utils";

/** A raised surface for things that are objects (a question, a weakness). Sections themselves stay flat. */
export function Panel({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-panel border border-line bg-raised", className)} {...props} />;
}

export function Section({ title, aside, children, className }: { title?: React.ReactNode; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("py-6", className)}>
      {(title || aside) && (
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          {title && <h2>{title}</h2>}
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function Chip({ children, className }: { children: React.ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center rounded-full border border-line px-2.5 py-0.5 text-sm text-ink", className)}>{children}</span>;
}
