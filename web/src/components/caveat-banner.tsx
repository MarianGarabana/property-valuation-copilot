export function CaveatBanner({ text }: { text: string }) {
  return (
    <div
      role="note"
      className="flex items-start gap-3 rounded-lg border border-caveat-border bg-caveat-bg px-4 py-3 text-caveat-fg"
    >
      <svg
        className="mt-0.5 size-4 shrink-0"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden
      >
        <path
          d="M12 8.5v5m0 3.5v.01M10.3 4.1 2.9 17a2 2 0 0 0 1.7 3h14.8a2 2 0 0 0 1.7-3L13.7 4.1a2 2 0 0 0-3.4 0Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <p className="text-sm font-medium leading-5">{text}</p>
    </div>
  );
}
