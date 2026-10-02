import type { Metadata } from "next";

export const siteUrl = process.env.SITE_URL ? new URL(process.env.SITE_URL) : undefined;

export function pageMetadata(
  title: string,
  description: string,
  path: string,
  index = false,
  locale = "en_US",
): Metadata {
  const pageTitle = `${title} | Aphrodize`;
  const url = siteUrl ? new URL(path, siteUrl).toString() : undefined;

  return {
    title: pageTitle,
    description,
    alternates: url ? { canonical: url } : undefined,
    robots: { index, follow: true },
    openGraph: { title: pageTitle, description, siteName: "Aphrodize", type: "website", locale, url },
    twitter: { card: "summary", title: pageTitle, description },
  };
}
