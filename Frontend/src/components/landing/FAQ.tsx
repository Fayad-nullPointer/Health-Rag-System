import { SectionHeader, FadeIn } from "./Section";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  { q: "How does Serenity work?", a: "Serenity is a conversational support companion. You share what you're feeling, and it responds with empathy, reflection, and gentle guidance based on evidence-informed mental wellness practices." },
  { q: "Is my data private?", a: "Yes. Your conversations are encrypted in transit and at rest. We never sell your data and you can delete your history at any time." },
  { q: "Can I use voice conversations?", a: "Yes. You can speak naturally with Serenity, and it can respond out loud — whatever feels most comfortable in the moment." },
  { q: "Can Serenity replace a therapist?", a: "No. Serenity is a supportive companion, not a substitute for professional care. We encourage working with a licensed therapist when possible, and we'll always point you to professional resources." },
  { q: "What happens during a crisis situation?", a: "If we detect signs of immediate risk, Serenity shares emergency resources and hotlines for your region, and gently encourages reaching a trusted person or professional right away." },
  { q: "Can I access previous conversations?", a: "Yes. Your conversation history is saved to your account so you can revisit reflections and track your growth journey over time." },
];

export function FAQ() {
  return (
    <section id="faq" aria-labelledby="faq-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-3xl px-5">
        <SectionHeader eyebrow="FAQ" title={<span id="faq-title">Questions, gently answered</span>} />

        <FadeIn delay={0.1}>
          <Accordion type="single" collapsible className="mt-12 space-y-3">
            {faqs.map((f, i) => (
              <AccordionItem
                key={f.q}
                value={`q-${i}`}
                className="overflow-hidden rounded-2xl border border-border bg-card px-5 shadow-soft data-[state=open]:border-primary/30"
              >
                <AccordionTrigger className="text-left font-display text-base font-semibold hover:no-underline">
                  {f.q}
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                  {f.a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </FadeIn>
      </div>
    </section>
  );
}
