import { Flower, Flower2, Leaf, Sprout, Sun, Cloud, Wind, Heart } from "lucide-react";
import { SectionHeader, FadeIn } from "./Section";

const scenarios = [
  { icon: Cloud, label: "Feeling anxious" },
  { icon: Wind, label: "Feeling overwhelmed" },
  { icon: Sun, label: "Experiencing stress" },
  { icon: Flower, label: "Loneliness" },
  { icon: Heart, label: "Relationship difficulties" },
  { icon: Sprout, label: "Academic pressure" },
  { icon: Leaf, label: "Career challenges" },
  { icon: Flower2, label: "Emotional burnout" },
];

export function WhoWeHelp() {
  return (
    <section aria-labelledby="who-title" className="relative bg-gradient-petal/40 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHeader
          eyebrow="Who we help"
          title={<span id="who-title">Is Serenity right for you?</span>}
          description="Whatever you're carrying, you're welcome here. These are some of the moments we walk through together."
        />

        <div className="mt-14 grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 lg:grid-cols-4">
          {scenarios.map((s, i) => (
            <FadeIn key={s.label} delay={i * 0.05}>
              <div className="group flex h-full items-center gap-3 rounded-2xl border border-border bg-card px-4 py-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-soft sm:px-5 sm:py-5">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-bloom/10 text-primary transition-transform group-hover:scale-110 group-hover:bg-gradient-bloom group-hover:text-white">
                  <s.icon className="h-5 w-5" />
                </span>
                <p className="text-sm font-medium leading-tight">{s.label}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}
