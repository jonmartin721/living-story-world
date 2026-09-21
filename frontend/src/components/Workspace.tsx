import { useEffect, useRef, type ReactNode } from "react";

export function Workspace({
  title,
  backLabel = "Back to story",
  onBack,
  children,
  wide = false,
}: {
  title: string;
  backLabel?: string;
  onBack: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
    window.scrollTo({ top: 0, behavior: "instant" });
  }, []);
  return (
    <main className={`workspace ${wide ? "workspace--wide" : ""}`}>
      <header className="workspace__bar">
        <span className="workspace__brand">Living Storyworld</span>
        <button type="button" className="button button--ghost" onClick={onBack}>
          ← {backLabel}
        </button>
      </header>
      <div className="workspace__body">
        <header className="workspace__heading">
          <h1 ref={heading} tabIndex={-1}>
            {title}
          </h1>
        </header>
        {children}
      </div>
    </main>
  );
}
