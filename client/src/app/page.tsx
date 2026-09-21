import {
  Activity,
  ArrowUpRight,
  Boxes,
  Database,
  FileText,
  Network,
  Tags,
} from "lucide-react";

const services = [
  {
    name: "FastAPI",
    description: "Versioned APIs, job orchestration, and OpenAPI documentation.",
    href: "http://localhost:8000/docs",
    icon: Network,
  },
  {
    name: "Label Studio",
    description: "Human-managed annotation projects and review workflows.",
    href: "http://localhost:8080",
    icon: Tags,
  },
  {
    name: "MLflow",
    description: "Experiment metadata, model lineage, and artifact tracking.",
    href: "http://localhost:5000",
    icon: Activity,
  },
  {
    name: "MinIO Console",
    description: "Private object storage for application and MLflow artifacts.",
    href: "http://localhost:9001",
    icon: Database,
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-background px-5 py-8 sm:px-8 lg:px-12">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-12">
        <header className="flex flex-col gap-6 border-b border-border pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <Boxes aria-hidden="true" className="size-4" />
              Local ML platform
            </div>
            <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
              Aphrodize workspace
            </h1>
            <p className="max-w-xl text-base leading-7 text-muted-foreground">
              A private local foundation for time-series and general-purpose model
              workflows. Start the Compose stack, then use the services below.
            </p>
          </div>
          <a
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/85 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            href="http://localhost:8000/docs"
          >
            Open API docs
            <ArrowUpRight aria-hidden="true" className="size-4" />
          </a>
        </header>

        <section aria-labelledby="services-heading" className="space-y-5">
          <div className="space-y-1">
            <h2 id="services-heading" className="text-xl font-semibold tracking-tight">
              Local services
            </h2>
            <p className="text-sm text-muted-foreground">
              Links are available after running <code>docker compose up -d --build</code> from the repository root.
            </p>
          </div>
          <ul className="grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2" role="list">
            {services.map(({ name, description, href, icon: Icon }) => (
              <li key={name} className="bg-card">
                <a
                  className="group flex min-h-44 flex-col justify-between gap-6 p-5 transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                  href={href}
                >
                  <div className="flex items-start justify-between gap-4">
                    <Icon aria-hidden="true" className="size-5 text-muted-foreground" />
                    <ArrowUpRight
                      aria-hidden="true"
                      className="size-4 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                    />
                  </div>
                  <div>
                    <h3 className="font-medium text-card-foreground">{name}</h3>
                    <p className="mt-1.5 text-sm leading-6 text-muted-foreground">{description}</p>
                  </div>
                </a>
              </li>
            ))}
          </ul>
        </section>

        <section
          aria-labelledby="model-heading"
          className="grid gap-6 border-t border-border pt-8 md:grid-cols-[1fr_1.5fr]"
        >
          <div className="space-y-2">
            <h2 id="model-heading" className="text-xl font-semibold tracking-tight">
              Model workspace
            </h2>
            <p className="text-sm leading-6 text-muted-foreground">
              Model packages are reserved in the repository. Artifacts and weights belong in MinIO through MLflow.
            </p>
          </div>
          <pre className="overflow-x-auto rounded-lg border border-border bg-muted/40 p-4 text-sm leading-6 text-foreground"><code>{`models/
├── time-series/
│   └── modelx/
└── non-time-series/
    └── u-net/`}</code></pre>
        </section>

        <footer className="flex flex-col gap-3 border-t border-border py-6 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>Client: Next.js, Tailwind CSS, and shadcn/ui.</span>
          <a
            className="inline-flex items-center gap-1.5 font-medium text-foreground underline-offset-4 hover:underline"
            href="http://localhost:8000/api/v1/health"
          >
            <FileText aria-hidden="true" className="size-4" />
            API health
          </a>
        </footer>
      </div>
    </main>
  );
}
