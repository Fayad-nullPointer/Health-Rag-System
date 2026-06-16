import { Heart, Clock, Shield, Sparkles } from "lucide-react";
import { SectionHeader, FadeIn } from "./Section";

const items = [
  { icon: Heart, title: "Compassionate Support", text: "We listen without judgment, with warmth and care.", color: "from-primary/20 to-primary/5" },
  { icon: Clock, title: "Available Anytime", text: "Get support whenever you need it — day or night.", color: "from-accent/30 to-accent/5" },
  { icon: Shield, title: "Private & Secure", text: "Your conversations stay confidential and encrypted.", color: "from-secondary/30 to-secondary/5" },
  { icon: Sparkles, title: "Personalized Guidance", text: "Support tailored to your emotional needs.", color: "from-primary/20 to-accent/10" },
];

export function Benefits() {
  return (
    <section id="benefits" aria-labelledby="benefits-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHeader
          eyebrow="A safe place to grow"
          title={<span id="benefits-title">Healing, made gentle</span>}
          description="Serenity meets you where you are, offering compassionate, judgment-free support to help you find clarity and peace."
        />

        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((b, i) => (
            <FadeIn key={b.title} delay={i * 0.08}>
              <article className="group relative h-full overflow-hidden rounded-3xl border border-border bg-card p-7 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-petal">
                <div className={`absolute inset-0 -z-10 bg-gradient-to-br ${b.color} opacity-0 transition-opacity duration-500 group-hover:opacity-100`} />
                <span className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-bloom text-white shadow-soft">
                  <b.icon className="h-6 w-6" />
                </span>
                <h3 className="mt-5 font-display text-lg font-semibold">{b.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{b.text}</p>
              </article>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}
