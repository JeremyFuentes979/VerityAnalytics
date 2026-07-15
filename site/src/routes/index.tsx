import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Home,
});

const services = [
  {
    title: "Data Profiling & Discovery",
    desc: "We ingest your raw data — CSV, Excel, or PDF — and produce a comprehensive profile: schema, statistics, null analysis, and anomaly detection. No commitment required.",
    agent: "Researcher",
    icon: "📋",
  },
  {
    title: "Pattern Analysis & Metrics",
    desc: "Our Analyst examines your data for trends, outliers, correlations, and generates actionable hypotheses — the foundation of every sound financial decision.",
    agent: "Analyst",
    icon: "📊",
  },
  {
    title: "Validation & Audit Trail",
    desc: "The Auditor cross-checks every finding, deduplicates, standardizes, and maintains a complete audit trail. Nothing leaves the firm without a second look.",
    agent: "Auditor",
    icon: "✅",
  },
  {
    title: "Synthesis & Delivery",
    desc: "The Manager adjudicates any conflicts, produces a decision memo, and delivers a polished Excel workbook with summary, cleaned data, analysis, and full audit trail.",
    agent: "Manager",
    icon: "📑",
  },
];

function Home() {
  return (
    <div>
      {/* Hero Section */}
      <section className="bg-navy py-24 text-white sm:py-32">
        <div className="mx-auto max-w-5xl px-8 text-center">
          <span className="inline-block rounded-sm border border-gold/40 px-3 py-1 text-xs font-medium uppercase tracking-[0.15em] text-gold">
            Virtual Accounting &amp; Analytics Firm
          </span>
          <h1 className="mx-auto mt-8 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl sm:leading-tight">
            Your Financial Data, Scrutinized by a Full Firm — Not a Single Algorithm
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-navy-200">
            Quorum operates like a real accounting firm: a team of specialists works your data
            through a structured process of discovery, analysis, validation, and delivery.
            Every result includes a complete audit trail — so you can trust what you see.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              to="/upload"
              className="rounded-sm bg-gold px-8 py-3.5 text-sm font-semibold uppercase tracking-wider text-navy transition-colors hover:bg-gold-600"
            >
              Upload Your Data — Free
            </Link>
            <a
              href="#services"
              className="rounded-sm border border-navy-400 px-8 py-3.5 text-sm font-medium text-navy-200 transition-colors hover:border-white hover:text-white"
            >
              Learn How It Works
            </a>
          </div>
          <p className="mt-6 text-sm text-navy-400">Free preview. One-time $50 fee for full analysis. No subscription.</p>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-b border-navy-100 bg-navy-50">
        <div className="mx-auto max-w-5xl px-8 py-10">
          <div className="grid grid-cols-3 gap-8 text-center">
            <div>
              <p className="font-serif text-3xl font-bold text-navy">4</p>
              <p className="mt-1 text-sm text-navy-500">Specialist Agents</p>
            </div>
            <div className="border-x border-navy-100">
              <p className="font-serif text-3xl font-bold text-navy">$50</p>
              <p className="mt-1 text-sm text-navy-500">One-Time Fee</p>
            </div>
            <div>
              <p className="font-serif text-3xl font-bold text-navy">100%</p>
              <p className="mt-1 text-sm text-navy-500">Audit Trail Included</p>
            </div>
          </div>
        </div>
      </section>

      {/* Process Section */}
      <section id="services" className="py-24">
        <div className="mx-auto max-w-5xl px-8">
          <div className="text-center">
            <span className="inline-block rounded-sm border border-navy-200 px-3 py-1 text-xs font-medium uppercase tracking-[0.15em] text-navy-500">
              Our Process
            </span>
            <h2 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">
              A Methodical Approach to Every Engagement
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-navy-500">
              Each file is processed through our four-stage workflow — a division of labor
              designed for accuracy, accountability, and auditability.
            </p>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2">
            {services.map((s, i) => (
              <div
                key={s.title}
                className="group rounded-sm border border-navy-100 bg-white p-8 transition-all hover:border-navy-300 hover:shadow-lg"
              >
                <div className="flex items-center justify-between">
                  <span className="font-serif text-3xl font-bold text-navy-200">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="text-2xl">{s.icon}</span>
                </div>
                <h3 className="mt-4 font-serif text-xl font-bold text-navy">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-navy-500">{s.desc}</p>
                <p className="mt-4 text-xs font-medium uppercase tracking-[0.1em] text-gold">
                  {s.agent}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Firm Ethos */}
      <section className="bg-navy-50 py-24">
        <div className="mx-auto max-w-3xl px-8 text-center">
          <span className="inline-block rounded-sm border border-navy-200 px-3 py-1 text-xs font-medium uppercase tracking-[0.15em] text-navy-500">
            Why Quorum
          </span>
          <h2 className="mt-4 font-serif text-3xl font-bold text-navy sm:text-4xl">
            More Than a Spreadsheet Tool
          </h2>
          <p className="mx-auto mt-6 max-w-xl leading-relaxed text-navy-500">
            Unlike single-pass chatbots or basic spreadsheet plugins, Quorum applies a genuine
            multi-agent workflow. Each specialist works independently, findings are
            cross-validated, and every correction is logged. The result is financial analysis
            you can present to stakeholders, auditors, or your board.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-3">
            {[
              { stat: "Adversarial Review", desc: "Every finding is checked by a second agent before it reaches you." },
              { stat: "Full Audit Trail", desc: "Every correction, every decision, every conflict — documented and timestamped." },
              { stat: "Deterministic Output", desc: "Our calculations are reproducible and verifiable. No black boxes." },
            ].map((item) => (
              <div key={item.stat} className="rounded-sm border border-navy-100 bg-white p-6">
                <p className="font-serif text-lg font-bold text-navy">{item.stat}</p>
                <p className="mt-2 text-sm leading-relaxed text-navy-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-navy py-24 text-white">
        <div className="mx-auto max-w-3xl px-8 text-center">
          <h2 className="font-serif text-3xl font-bold sm:text-4xl">
            Ready to Put Your Data in Order?
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-navy-200">
            Upload a file and get a free data profile within seconds. No credit card, no subscription —
            only pay when you need the full firm analysis.
          </p>
          <Link
            to="/upload"
            className="mt-8 inline-block rounded-sm bg-gold px-10 py-3.5 text-sm font-semibold uppercase tracking-wider text-navy transition-colors hover:bg-gold-600"
          >
            Upload Your Data
          </Link>
        </div>
      </section>
    </div>
  );
}