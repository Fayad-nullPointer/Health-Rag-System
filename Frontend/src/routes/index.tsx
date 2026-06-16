import { createFileRoute } from "@tanstack/react-router";
import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { Benefits } from "@/components/landing/Benefits";
import { WhoWeHelp } from "@/components/landing/WhoWeHelp";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { Testimonials } from "@/components/landing/Testimonials";
import { TrustMetrics } from "@/components/landing/TrustMetrics";
import { AIFeatures } from "@/components/landing/AIFeatures";
import { Topics } from "@/components/landing/Topics";
import { FAQ } from "@/components/landing/FAQ";
import { FinalCTA } from "@/components/landing/FinalCTA";
import { Footer } from "@/components/landing/Footer";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "MindCare AI — Bloom into the life you deserve" },
      { name: "description", content: "Compassionate, confidential, AI-powered emotional support, available 24/7. A safe space to grow, heal, and bloom." },
      { property: "og:title", content: "MindCare AI — Bloom into the life you deserve" },
      { property: "og:description", content: "Compassionate, confidential, AI-powered emotional support, available 24/7." },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  return (
    <div className="overflow-x-hidden">
      <Navbar />
      <Hero />
      <Benefits />
      <WhoWeHelp />
      <HowItWorks />
      <Testimonials />
      <TrustMetrics />
      <AIFeatures />
      <Topics />
      <FAQ />
      <FinalCTA />
      <Footer />
    </div>
  );
}
