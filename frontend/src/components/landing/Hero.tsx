import { motion } from "motion/react";
import { ArrowRight, MessageCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroBloom from "@/assets/hero-bloom.png";
import sunflower from "@/assets/sunflower.png";
import { getUser } from "@/lib/auth";
import { Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";

export function Hero() {

  const [user,setUser] = useState(getUser());


  useEffect(()=>{

    const syncUser = () => {
      setUser(getUser());
    };

    window.addEventListener(
      "storage",
      syncUser
    );

    return () =>
      window.removeEventListener(
        "storage",
        syncUser
      );

  },[]);

  const capitalize = (text:string="") =>
    text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();

  const displayName = user
    ? capitalize(
        user.first_name ||
        user.full_name?.split(" ")[0] ||
        user.username
      )
    : "";

  const heroText = user
    ? `Welcome back ${displayName}. Serenity is here whenever you need a calm space to reflect, heal, and grow.`
    : `Life can feel overwhelming at times. Serenity offers compassionate, confidential, and always-available emotional support to help you navigate every step of your journey.`;

  return (
    <section className="relative isolate overflow-hidden pt-32 pb-24 md:pt-40 md:pb-32">
      {/* Soft sunlight wash */}
      <div className="absolute inset-0 -z-10 bg-gradient-soft" />
      <div className="absolute inset-x-0 top-0 -z-10 h-[80%] bg-gradient-sunlight" />

      {/* Floating decorative leaves */}
      <img
        src={sunflower}
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute left-[6%] top-[18%] hidden h-20 w-20 animate-float-leaf opacity-80 md:block"
      />
      <img
        src={sunflower}
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute right-[8%] bottom-[14%] hidden h-16 w-16 animate-sway opacity-70 md:block"
        style={{ animationDelay: "1s" }}
      />

      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-5 lg:grid-cols-2 lg:gap-8">
        <div className="relative z-10 text-center lg:text-left">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-medium text-primary"
          >
            <Sparkles className="h-3.5 w-3.5" />
            Compassionate AI support, available 24/7
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="mt-6 font-display text-5xl font-extrabold leading-[1.05] tracking-tight text-foreground sm:text-6xl lg:text-7xl"
          >
            Bloom into the{" "}
            <span className="relative inline-block">
              <span className="bg-gradient-bloom bg-clip-text text-transparent">life you deserve</span>
              <svg className="absolute -bottom-2 left-0 w-full" height="10" viewBox="0 0 200 10" fill="none" aria-hidden="true">
                <path d="M2 6 Q 50 -2, 100 5 T 198 4" stroke="var(--gold)" strokeWidth="3" strokeLinecap="round" fill="none" />
              </svg>
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="mx-auto mt-6 max-w-xl text-lg text-muted-foreground lg:mx-0"
          >
            {heroText}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.3 }}
            className="mt-9 flex flex-wrap items-center justify-center gap-3 lg:justify-start"
          >
            {user ? (
              <>
                <Button
                  size="lg"
                  className="h-12 rounded-full bg-gradient-bloom px-7 text-base font-semibold text-white shadow-petal hover:opacity-90"
                  asChild
                >
                  <Link to="/chat">
                    Continue your journey
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>

                <Button
                  size="lg"
                  variant="outline"
                  className="h-12 rounded-full border-2 px-7 text-base font-semibold"
                  asChild
                >
                  <Link to="/chat">
                    <MessageCircle className="mr-1 h-4 w-4" />
                    Talk to Serenity
                  </Link>
                </Button>
              </>
            ) : (
              <>
                <Button
                  size="lg"
                  className="h-12 rounded-full bg-gradient-bloom px-7 text-base font-semibold text-white shadow-petal hover:opacity-90"
                  asChild
                >
                  <Link to="/register">
                    Start your journey
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>

                <Button
                  size="lg"
                  variant="outline"
                  className="h-12 rounded-full border-2 px-7 text-base font-semibold"
                  asChild
                >
                  <Link to="/chat">
                    <MessageCircle className="mr-1 h-4 w-4" />
                    Talk to Serenity
                  </Link>
                </Button>
              </>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="mt-8 flex items-center justify-center gap-6 text-xs text-muted-foreground lg:justify-start"
          >
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-secondary" /> 100% Private
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" /> Free to start
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" /> No card required
            </span>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="relative mx-auto w-full max-w-lg"
        >
          {/* Glowing aura */}
          <div className="absolute inset-0 -z-10 animate-sun-pulse rounded-full bg-gradient-bloom opacity-30 blur-3xl" />
          <div className="absolute -right-6 -top-6 -z-10 h-40 w-40 animate-sun-pulse rounded-full bg-accent/40 blur-3xl" style={{ animationDelay: "2s" }} />

          <div className="relative aspect-square rounded-[2.5rem] bg-gradient-petal p-6 shadow-petal ring-1 ring-white/40 backdrop-blur">
            <img
              src={heroBloom}
              alt="A person sitting peacefully in meditation, surrounded by blooming flowers"
              width={1280}
              height={1280}
              className="h-full w-full object-contain drop-shadow-2xl"
            />
            {/* Floating chips */}
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              className="absolute -left-4 top-12 rounded-2xl border border-border bg-background/90 px-4 py-2.5 shadow-soft backdrop-blur"
            >
              <p className="text-xs font-medium text-muted-foreground">Today's mood</p>
              <p className="text-sm font-semibold text-foreground">Hopeful 🌻</p>
            </motion.div>
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              className="absolute -right-3 bottom-16 max-w-[14rem] rounded-2xl border border-border bg-background/90 p-4 shadow-soft backdrop-blur"
            >
              <div className="flex items-center gap-2">
                <span className="grid h-7 w-7 place-items-center rounded-full bg-gradient-bloom text-white">
                  <Sparkles className="h-3.5 w-3.5" />
                </span>
                <p className="text-xs font-semibold">Serenity</p>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                "I hear you. Let's take a deep breath together."
              </p>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
