"use client";

import { type ReactNode } from "react";
import { AppNavigation } from "./app-navigation";
import { ThemeToggle } from "./theme-toggle";

export function WorkspaceShell({ active, eyebrow, title, detail, children }: {
  active: "dashboard" | "capture" | "clients" | "trend" | "profile" | "none";
  eyebrow: string;
  title: string;
  detail?: string;
  children: ReactNode;
}) {
  return (
    <div className="app-shell workspace-shell">
      <AppNavigation active={active} />
      <main className="workspace-main">
        <header className="topbar workspace-topbar">
          <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div>
          <div className="workspace-header-actions">
            {detail && <span className="workspace-detail">{detail}</span>}
            <ThemeToggle />
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
