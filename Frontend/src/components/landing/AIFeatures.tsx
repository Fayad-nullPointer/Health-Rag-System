import { Brain, MessageCircleHeart, Mic, ShieldAlert, History, Globe } from "lucide-react";
import { SectionHeader, FadeIn } from "./Section";

const features = [
  { icon: Brain, title: "Emotion Detection", text: "Understands your emotional tone and meets you where you are." },
  { icon: MessageCircleHeart, title: "Personalized Conversations", text: "Responds with empathy, context, and care." },
  { icon: Mic, title: "Voice Interaction", text: "Speak naturally with MindCare AI when typing feels like too much." },
  { icon: ShieldAlert, title: "Crisis Support", text: "Immediate guidance and trusted safety resources when it matters most." },
  { icon: History, title: "Conversation History", text: "Revisit your reflections and notice how far you've grown." },
  { icon: Globe, title: "Multi-Language Support", text: "Get support in the language that feels most like home." },
];

export function AIFeatures() {
  return (
    <section id="features" aria-labelledby="features-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-5">
        <SectionHeader
          eyebrow="Designed for wellness"
          title={<span id="features-title">Built to support every shade of you</span>}
          description="Thoughtful AI capabilities, wrapped in a warm and human experience."
        />

        <div className="mt-14 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <FadeIn key={f.title} delay={i * 0.06}>
              <article className="group relative h-full overflow-hidden rounded-3xl border border-border bg-card p-7 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-petal">
                <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-bloom opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-30" />
                <div className="relative">
                  <span className="grid h-12 w-12 place-items-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/20 transition-colors group-hover:bg-gradient-bloom group-hover:text-white">
                    <f.icon className="h-6 w-6" />
                  </span>
                  <h3 className="mt-5 font-display text-lg font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.text}</p>
                </div>
              </article>
            </FadeIn>
          ))}
        </div>
      </div>
    </section>
  );
}
