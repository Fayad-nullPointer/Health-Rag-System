import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "motion/react";

const metrics = [
  { value: 50000, suffix: "+", label: "Conversations supported" },
  { value: 95, suffix: "%", label: "Feel better after talking" },
  { value: 24, suffix: "/7", label: "Always available", noCount: true },
  { value: 100, suffix: "%", label: "Private and secure" },
];

function Counter({ to, suffix, noCount }: { to: number; suffix: string; noCount?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const [n, setN] = useState(noCount ? to : 0);

  useEffect(() => {
    if (!inView || noCount) return;
    const duration = 1600;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setN(Math.floor(eased * to));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, to, noCount]);

  return <span ref={ref}>{n.toLocaleString()}{suffix}</span>;
}

export function TrustMetrics() {
  return (
    <section aria-labelledby="trust-title" className="relative py-20 sm:py-24">
      <div className="mx-auto max-w-7xl px-5">
        <h2 id="trust-title" className="sr-only">Trusted by people seeking support</h2>
        <div className="rounded-[2rem] border border-border bg-gradient-bloom p-1 shadow-petal">
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[1.85rem] bg-border lg:grid-cols-4">
            {metrics.map((m) => (
              <div key={m.label} className="bg-card p-8 text-center sm:p-10">
                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5 }}
                  className="font-display text-4xl font-extrabold tracking-tight text-primary sm:text-5xl"
                >
                  <Counter to={m.value} suffix={m.suffix} noCount={m.noCount} />
                </motion.p>
                <p className="mt-2 text-sm text-muted-foreground">{m.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
