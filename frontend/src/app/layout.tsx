import type { Metadata } from "next";
import Script from "next/script";
import localFont from "next/font/local";
import { LanguageProvider } from "@/components/language-provider";
import "./globals.css";
import "./prototype.css";
import "./analysis.css";
import "./design-system.css";

const libreBaskerville = localFont({
  src: "./fonts/LibreBaskerville-Variable.ttf",
  weight: "400 700",
  style: "normal",
  display: "swap",
  variable: "--font-libre-baskerville",
});

const montserrat = localFont({
  src: "./fonts/Montserrat-Variable.ttf",
  weight: "400 700",
  style: "normal",
  display: "swap",
  variable: "--font-montserrat",
});

const notoSansThai = localFont({
  src: "./fonts/NotoSansThai-Variable.ttf",
  weight: "400 700",
  style: "normal",
  display: "swap",
  variable: "--font-noto-sans-thai",
});

export const metadata: Metadata = {
  title: "Aphrodize",
  description: "Aphrodize skin tracking prototype.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${libreBaskerville.variable} ${montserrat.variable} ${notoSansThai.variable}`}
      suppressHydrationWarning
    >
      <body>
        <LanguageProvider>{children}</LanguageProvider>
        <Script src="/legacy/theme.js" strategy="beforeInteractive" />
      </body>
    </html>
  );
}
