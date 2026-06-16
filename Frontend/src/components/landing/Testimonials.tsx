import { Star } from "lucide-react";
import { SectionHeader, FadeIn } from "./Section";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";

const testimonials = [
  {
    name: "Maya R.",
    role: "Graduate student",
    quote: "Serenity helped me feel heard during one of the most difficult periods of my life. It was the gentle nudge I needed.",
    initial: "M",
    color: "from-primary to-violet-deep",
  },
  {
    name: "Daniel K.",
    role: "Software engineer",
    quote: "It felt like having a supportive companion available whenever I needed it. Late nights stopped feeling so heavy.",
    initial: "D",
    color: "from-secondary to-sage",
  },
  {
    name: "Aisha N.",
    role: "Teacher",
    quote: "The conversations encouraged me to reflect and manage my emotions more effectively. I feel more like myself.",
    initial: "A",
    color: "from-accent to-gold",
  },
  {
    name: "Jordan P.",
    role: "Designer",
    quote: "I didn't know an AI could feel this warm. It's like a journal that listens back with kindness.",
    initial: "J",
    color: "from-lavender to-primary",
  },
];

export function Testimonials() {
  return (
    <section aria-labelledby="t-title" className="relative bg-gradient-soft py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHeader eyebrow="Stories of growth" title={<span id="t-title">From seeds to bloom</span>} />

        <FadeIn delay={0.1}>
          <Carousel opts={{ align: "start", loop: true }} className="mt-14">
            <CarouselContent className="-ml-4">
              {testimonials.map((t) => (
                <CarouselItem key={t.name} className="pl-4 md:basis-1/2 lg:basis-1/3">
                  <figure className="flex h-full flex-col justify-between rounded-3xl border border-border bg-card p-7 shadow-soft">
                    <div>
                      <div className="flex gap-0.5 text-accent">
                        {Array.from({ length: 5 }).map((_, i) => (
                          <Star key={i} className="h-4 w-4 fill-current" />
                        ))}
                      </div>
                      <blockquote className="mt-4 text-base leading-relaxed text-foreground">
                        "{t.quote}"
                      </blockquote>
                    </div>
                    <figcaption className="mt-6 flex items-center gap-3">
                      <span className={`grid h-11 w-11 place-items-center rounded-full bg-gradient-to-br ${t.color} font-display text-base font-semibold text-white`}>
                        {t.initial}
                      </span>
                      <div>
                        <p className="text-sm font-semibold">{t.name}</p>
                        <p className="text-xs text-muted-foreground">{t.role}</p>
                      </div>
                    </figcaption>
                  </figure>
                </CarouselItem>
              ))}
            </CarouselContent>
            <div className="mt-8 flex items-center justify-center gap-3">
              <CarouselPrevious className="static translate-y-0" />
              <CarouselNext className="static translate-y-0" />
            </div>
          </Carousel>
        </FadeIn>
      </div>
    </section>
  );
}
