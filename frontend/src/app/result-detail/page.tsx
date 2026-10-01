import { redirect } from "next/navigation";
import { pageMetadata } from "@/lib/page-metadata";

export const metadata = pageMetadata(
  "Results",
  "Continue to your experimental skin image observations, analysis details and related skin care guidance. Results are not a medical diagnosis.",
  "/capture",
  false,
  "en_US",
);

export default function Page() {
  redirect("/capture#results");
}
