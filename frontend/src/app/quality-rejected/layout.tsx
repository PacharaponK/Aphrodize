import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Quality check",
  "Review why an image cannot be used for skin comparison and follow lighting and camera guidance before taking a new photo.",
  "/quality-rejected",
  false,
  "en_US",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
