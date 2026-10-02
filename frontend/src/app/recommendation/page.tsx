import { redirect } from "next/navigation";
import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Skin care",
  "Continue to your image analysis results and skin care guidance based on your reported profile and reviewed product information.",
  "/capture",
  false,
  "en_US",
);

export default function Page() {
  redirect("/capture#products");
}
