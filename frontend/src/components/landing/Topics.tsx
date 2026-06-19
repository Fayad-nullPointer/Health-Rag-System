import {
  Flower2,
  CloudRain,
  Wind,
  Sun,
  Bird,
  Moon,
  HeartHandshake,
  Sprout,
  Sparkles,
} from "lucide-react";

import { SectionHeader, FadeIn } from "./Section";

const topics = [
  {
    name: "Anxiety",
    icon: Flower2,
    color: "from-primary/20 to-primary/5",
  },
  {
    name: "Depression",
    icon: CloudRain,
    color: "from-secondary/30 to-secondary/5",
  },
  {
    name: "Stress",
    icon: Wind,
    color: "from-leaf/40 to-leaf/5",
  },
  {
    name: "Self-Esteem",
    icon: Sun,
    color: "from-accent/40 to-accent/5",
  },
  {
    name: "Burnout",
    icon: Sparkles,
    color: "from-gold/40 to-gold/5",
  },
  {
    name: "Grief",
    icon: Bird,
    color: "from-lavender/30 to-lavender/5",
  },
  {
    name: "Loneliness",
    icon: Moon,
    color: "from-primary/15 to-primary/5",
  },
  {
    name: "Relationships",
    icon: HeartHandshake,
    color: "from-violet-deep/20 to-violet-deep/5",
  },
  {
    name: "Motivation",
    icon: Sprout,
    color: "from-sage/30 to-sage/5",
  },
  {
    name: "Emotional Wellness",
    icon: Flower2,
    color: "from-primary/20 to-accent/10",
  },
];

export function Topics() {
  return (
    <section
      id="topics"
      aria-labelledby="topics-title"
      className="relative bg-gradient-petal/30 py-24 sm:py-32"
    >
      <div className="mx-auto max-w-7xl px-5">
        <SectionHeader
          eyebrow="What we talk about"
          title={
            <span id="topics-title">
              Mental health topics, gently explored
            </span>
          }
          description="Bring any of these to the conversation — or something the world hasn't named yet."
        />

        <div className="mt-14 grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 md:grid-cols-4 lg:grid-cols-5">
          {topics.map((topic, i) => {
            const Icon = topic.icon;

            return (
              <FadeIn key={topic.name} delay={i * 0.04}>
                <button
                  className={`group flex aspect-square w-full flex-col items-center justify-center gap-3 rounded-3xl border border-border bg-gradient-to-br ${topic.color} p-4 text-center transition-all duration-300 hover:-translate-y-1 hover:shadow-petal`}
                >
                  <Icon
                    className="h-12 w-12 text-primary transition-all duration-300 group-hover:scale-125 group-hover:rotate-6 sm:h-14 sm:w-14"
                    strokeWidth={1.75}
                  />

                  <span className="text-sm font-semibold leading-tight">
                    {topic.name}
                  </span>
                </button>
              </FadeIn>
            );
          })}
        </div>
      </div>
    </section>
  );
}