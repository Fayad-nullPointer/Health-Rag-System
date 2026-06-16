import { UserPlus, MessageSquareHeart, Sparkles, TrendingUp } from "lucide-react";
import { SectionHeader, FadeIn } from "./Section";

const steps = [
  { icon: UserPlus, title: "Create your account", text: "Take a moment for yourself. Sign up in under a minute." },
  { icon: MessageSquareHeart, title: "Share what you're feeling", text: "Type or speak. There's no wrong way to begin." },
  { icon: Sparkles, title: "Receive personalized support", text: "Empathetic, thoughtful guidance tailored to you." },
  { icon: TrendingUp, title: "Track your growth journey", text: "Look back, notice patterns, celebrate every small bloom." },
];

export function HowItWorks() {
  return (
    <section id="how" aria-labelledby="how-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHeader
          eyebrow="How it works"
          title={<span id="how-title">Your journey starts with a conversation</span>}
        />

        <div className="relative mt-16">
          {/* Vine line */}
          <div className="absolute left-1/2 top-0 hidden h-full w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-primary/30 to-transparent md:block" />

          <ol className="space-y-10 md:space-y-16">
            {steps.map((s, i) => {
              const right = i % 2 === 1;
              return (
                <FadeIn key={s.title} delay={i * 0.1}>
                  <li className={`grid items-center gap-6 md:grid-cols-[1fr_auto_1fr] ${right ? "" : ""}`}>
                    <div className={`${right ? "md:order-3 md:text-left" : "md:text-right"}`}>
                      <span className="text-xs font-semibold tracking-widest text-primary/70">STEP 0{i + 1}</span>
                      <h3 className="mt-1 font-display text-2xl font-bold">{s.title}</h3>
                      <p className="mt-2 text-muted-foreground">{s.text}</p>
                    </div>
                    <div className="hidden md:block md:order-2">
                      <span className="relative grid h-16 w-16 place-items-center rounded-full bg-gradient-bloom text-white shadow-petal">
                        <s.icon className="h-7 w-7" />
                        <span className="absolute inset-0 animate-sun-pulse rounded-full bg-primary/30 blur-md -z-10" />
                      </span>
                    </div>
                    <div className={`${right ? "md:order-1" : "md:order-3"} hidden md:block`} aria-hidden />
                    {/* mobile icon */}
                    <span className="grid h-12 w-12 place-items-center rounded-full bg-gradient-bloom text-white shadow-soft md:hidden">
                      <s.icon className="h-5 w-5" />
                    </span>
                  </li>
                </FadeIn>
              );
            })}
          </ol>
        </div>
      </div>
    </section>
  );
}
