import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Health setup",
  "Provide or update your wellness profile, skin concerns and safety information to support relevant skin care guidance.",
  "/onboarding/health",
  false,
  "en_US",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
