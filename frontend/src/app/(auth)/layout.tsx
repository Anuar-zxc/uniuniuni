import { Logo } from "@/components/app-shell";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="px-4 py-5 sm:px-8"><Logo /></header>
      <main className="flex flex-1 items-start justify-center px-4 pt-[8vh]">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}
