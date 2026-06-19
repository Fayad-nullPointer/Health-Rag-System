import { motion } from "motion/react";
import { ArrowRight, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import ctaBloom from "@/assets/cta-bloom.png";
import { getUser } from "@/lib/auth";
import { Link } from "@tanstack/react-router";

export function FinalCTA() {
  const user = getUser();

  return (
    <section aria-labelledby="cta-title" className="relative overflow-hidden py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5">
        <div className="relative isolate overflow-hidden rounded-[2.5rem] bg-gradient-bloom px-6 py-16 text-center text-white shadow-petal sm:px-16 sm:py-24">
          {/* Glows */}
          <div className="absolute -left-20 -top-20 h-72 w-72 rounded-full bg-accent/50 blur-3xl" aria-hidden />
          <div className="absolute -right-20 -bottom-20 h-80 w-80 rounded-full bg-lavender/60 blur-3xl" aria-hidden />

          <motion.img
            src={ctaBloom}
            alt=""
            aria-hidden
            initial={{ opacity: 0, scale: 0.8, rotate: -10 }}
            whileInView={{ opacity: 0.35, scale: 1, rotate: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
            className="pointer-events-none absolute -right-8 -bottom-10 w-80 max-w-[60%] drop-shadow-2xl sm:w-[28rem]"
          />
          <motion.img
            src={ctaBloom}
            alt=""
            aria-hidden
            initial={{ opacity: 0, scale: 0.8, rotate: 10 }}
            whileInView={{ opacity: 0.25, scale: 1, rotate: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 1.2, delay: 0.2 }}
            className="pointer-events-none absolute -left-10 -top-12 hidden w-64 sm:block"
          />

          <div className="relative mx-auto max-w-2xl">
            <h2 id="cta-title" className="font-display text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl md:text-6xl">
              Your journey toward growth starts today
            </h2>
            <p className="mx-auto mt-5 max-w-xl text-base text-white/85 sm:text-lg">
              Every flower blooms at its own pace. Serenity is here to support you, every step of the way.
            </p>

            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">

              {user ? (

                <Button
                  size="lg"
                  className="h-12 rounded-full bg-white px-7 text-base font-semibold text-primary hover:bg-white/90"
                  asChild
                >
                  <Link to="/chat">
                    Continue your journey
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>

              ) : (

                <>
                  <Button
                    size="lg"
                    className="h-12 rounded-full bg-white px-7 text-base font-semibold text-primary hover:bg-white/90"
                    asChild
                  >
                    <Link to="/register">
                      Start free
                      <ArrowRight className="ml-1 h-4 w-4" />
                    </Link>
                  </Button>


                  <Button
                    size="lg"
                    variant="outline"
                    className="h-12 rounded-full border-2 border-white/70 bg-transparent px-7 text-base font-semibold text-white hover:bg-white/10 hover:text-white"
                    asChild
                  >
                    <Link to="/chat">
                      <MessageCircle className="mr-1 h-4 w-4" />
                      Talk to Serenity
                    </Link>
                  </Button>
                </>

              )}

            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
