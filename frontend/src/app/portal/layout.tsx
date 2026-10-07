import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Service portal",
  "Open Aphrodize applications, API documentation, annotation, experiment tracking and object storage from one place.",
  "/portal",
);

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
