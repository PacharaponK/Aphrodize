import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Sign in",
  "Sign in to Aphrodize to access your skin observations, daily wellness records and personalized care guidance.",
  "/login",
  true,
  "en_US",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
