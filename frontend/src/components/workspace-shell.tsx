"use client";

import { type ReactNode, useState } from "react";
import { AppNavigation } from "./app-navigation";

export function WorkspaceShell({ active, eyebrow, title, detail, children }: {
  active: "dashboard" | "capture" | "none";
  eyebrow: string;
  title: string;
  detail?: string;
  children: ReactNode;
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="app-shell workspace-shell">
      <AppNavigation active={active} mobileOpen={menuOpen} onClose={() => setMenuOpen(false)} />
      <main className="workspace-main">
        <header className="topbar workspace-topbar">
          <button type="button" className="mobile-menu-button" aria-label={menuOpen ? "ปิดเมนู" : "เปิดเมนู"} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><span /><span /><span /></button>
          <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div>
          {detail && <span className="workspace-detail">{detail}</span>}
        </header>
        {children}
      </main>
    </div>
  );
}
