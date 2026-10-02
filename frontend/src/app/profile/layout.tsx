import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Profile",
  "Review and update your skin profile, wellness information, allergy details and recorded cycle information in Aphrodize.",
  "/profile",
  false,
  "en_US",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
