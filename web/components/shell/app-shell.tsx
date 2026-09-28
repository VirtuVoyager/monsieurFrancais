"use client";

import { BookOpen, Gauge, Home, Layers, Library, Repeat, Timer } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cx } from "@/components/ui/cx";
import { api } from "@/lib/api/client";
import { useQueryClient } from "@tanstack/react-query";

const NAV = [
  { href: "/", label: "Home", icon: Home },
  { href: "/path", label: "Path", icon: Layers },
  { href: "/review", label: "Review", icon: Repeat },
  { href: "/drills", label: "Drills", icon: Timer },
  { href: "/library", label: "Library", icon: Library },
  { href: "/progress", label: "Progress", icon: Gauge },
];

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-dvh md:grid md:grid-cols-[15rem_1fr]">
      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface px-4 py-6 md:flex">
        <Link href="/" className="mb-8 flex items-center gap-2 px-2">
          <BookOpen className="size-6 text-accent" aria-hidden />
          <span className="font-serif text-lg font-semibold">Monsieur Français</span>
        </Link>
        <nav aria-label="Main" className="flex flex-col gap-1">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={isActive(pathname, href) ? "page" : undefined}
              className={cx(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                isActive(pathname, href)
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:bg-surface-2 hover:text-ink",
              )}
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-1 text-sm">
          <Link
            href="/settings"
            className="rounded-xl px-3 py-2 text-muted hover:bg-surface-2 hover:text-ink"
          >
            Settings
          </Link>
          <Link
            href="/settings/budget"
            className="rounded-xl px-3 py-2 text-muted hover:bg-surface-2 hover:text-ink"
          >
            Budget
          </Link>
          <SignOut />
        </div>
      </aside>

      <main className="mx-auto w-full max-w-4xl px-4 pt-6 pb-28 sm:px-6 md:pt-10 md:pb-12">
        {children}
      </main>

      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-10 grid grid-cols-6 border-t border-line bg-surface/95 backdrop-blur md:hidden"
      >
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={isActive(pathname, href) ? "page" : undefined}
            className={cx(
              "flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium",
              isActive(pathname, href) ? "text-accent" : "text-muted",
            )}
          >
            <Icon className="size-5" aria-hidden />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}

function SignOut() {
  const queryClient = useQueryClient();
  const signOut = async () => {
    await api.POST("/auth/logout");
    queryClient.clear();
    await queryClient.invalidateQueries();
  };
  return (
    <button
      type="button"
      onClick={signOut}
      className="rounded-xl px-3 py-2 text-left text-muted hover:bg-surface-2 hover:text-ink"
    >
      Sign out
    </button>
  );
}
