import type { Metadata } from "next";
import { WorkspaceShell } from "@/components/workspace-shell";
import { UvRecommendation } from "./uv-recommendation";
import "./uv.css";

export const metadata: Metadata = { title: "คำแนะนำกันแดด — Aphrodize" };

export default function Page() {
  return (
    <WorkspaceShell active="none" eyebrow="UV GUIDANCE" title="คำแนะนำกันแดด">
      <UvRecommendation />
    </WorkspaceShell>
  );
}
