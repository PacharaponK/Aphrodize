import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Sign up",
  "Create your Aphrodize account to start tracking skin observations and daily wellness with consent-based image analysis.",
  "/signup",
  true,
  "en_US",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
