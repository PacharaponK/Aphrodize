import type { Metadata } from "next";
import Script from "next/script";
import localFont from "next/font/local";
import { LanguageProvider } from "@/components/language-provider";
import { SharedNavigation } from "@/components/shared-navigation";
import { PageTransition } from "@/components/page-transition";
import { AuthPresentationProvider } from "@/components/auth-presentation";
import { pageMetadata, siteUrl } from "@/lib/page-metadata";
import "./globals.css";
import "./prototype.css";
import "./analysis.css";
import "./design-system.css";
import "./component-hierarchy.css";

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
  ...pageMetadata(
    "Skin tracking",
    "Track skin observations, sleep, hydration and daily habits with Aphrodize. Experimental insights support your wellness routine and are not a medical diagnosis.",
    "/",
  ),
  metadataBase: siteUrl,
  applicationName: "Aphrodize",
  icons: { icon: { url: "/assets/aphrodize-logo.svg", type: "image/svg+xml" } },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${libreBaskerville.variable} ${montserrat.variable} ${notoSansThai.variable}`}
      suppressHydrationWarning
    >
      <body>
        <LanguageProvider><AuthPresentationProvider><SharedNavigation /><PageTransition>{children}</PageTransition></AuthPresentationProvider></LanguageProvider>
        <Script src="/legacy/theme.js" strategy="beforeInteractive" />
      </body>
    </html>
  );
}
