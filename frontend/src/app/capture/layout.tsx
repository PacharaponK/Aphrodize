import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Analyze",
  "Capture or upload a face image with your consent, check image quality and review experimental skin observations and related care guidance.",
  "/capture",
  false,
  "en_US",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
