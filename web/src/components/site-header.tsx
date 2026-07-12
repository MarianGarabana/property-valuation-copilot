import Link from "next/link";

const links = [
  { href: "/", label: "Overview" },
  { href: "/valuation", label: "Valuation" },
  { href: "/cnn-study", label: "CNN study" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span
            aria-hidden
            className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path
                d="M3 11.5 12 4l9 7.5"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M6 10.5V20h12v-9.5"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span className="font-display text-[17px] font-semibold tracking-tight">
            Valuation Copilot
          </span>
          <span className="hidden rounded-full border border-caveat-border bg-caveat-bg px-2 py-0.5 text-[11px] font-medium leading-4 text-caveat-fg sm:inline-block">
            2018 data prototype
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-md px-3 py-1.5 text-sm font-medium text-ink-soft transition-colors duration-150 hover:bg-secondary hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
