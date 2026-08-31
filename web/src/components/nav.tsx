import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/upload", label: "Upload" },
  { href: "/results", label: "Results" },
  { href: "/explorer", label: "Explorer" },
  { href: "/benchmark", label: "Benchmark" },
];

export function Nav({ current }: { current: string }) {
  return (
    <header className="border-b border-[var(--line)] bg-[var(--paper)]">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="font-serif text-xl tracking-tight text-[var(--ink)]">
          Distant Contradiction Auditor
        </Link>
        <nav className="flex flex-wrap gap-1">
          {links.map((l) => {
            const active = current === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-full px-3 py-1.5 text-sm ${
                  active
                    ? "bg-[var(--ink)] text-[var(--paper)]"
                    : "text-[var(--muted)] hover:bg-[var(--wash)] hover:text-[var(--ink)]"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
