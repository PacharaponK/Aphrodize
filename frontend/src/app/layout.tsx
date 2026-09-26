import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import "./prototype.css";
import "./analysis.css";
import "./design-system.css";

export const metadata: Metadata = {
  title: "Aphrodize",
  description: "Aphrodize skin tracking prototype.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="th">
      <body>
        {children}
        <Script src="/legacy/theme.js" strategy="afterInteractive" />
      </body>
    </html>
  );
}
