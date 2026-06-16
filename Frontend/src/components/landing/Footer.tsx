import { Instagram, Facebook, Linkedin } from "lucide-react";
import serenityIcon from "@/assets/serenity-icon.png";

const cols = [
  {
    title: "Serenity",
    links: [
      { label: "Home", href: "#" },
      { label: "About", href: "#benefits" },
      { label: "Features", href: "#features" },
      { label: "FAQ", href: "#faq" },
      { label: "Contact", href: "#" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "#" },
      { label: "Terms of Service", href: "#" },
      { label: "Cookies", href: "#" },
    ],
  },
  {
    title: "Support",
    links: [
      { label: "Help Center", href: "#" },
      { label: "Crisis Resources", href: "#" },
      { label: "Community", href: "#" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-border bg-gradient-soft">
      <div className="pointer-events-none absolute -left-20 top-10 h-48 w-48 rounded-full bg-primary/10 blur-3xl" aria-hidden />
      <div className="pointer-events-none absolute right-0 bottom-0 h-56 w-56 rounded-full bg-accent/10 blur-3xl" aria-hidden />

      <div className="relative mx-auto max-w-7xl px-5 py-16">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <a href="#" className="flex items-center gap-2 font-display text-lg font-bold">
              <img src={serenityIcon} alt="" className="h-auto w-30 object-contain" />
            </a>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Bloom into the life you deserve. Compassionate, confidential, AI-powered emotional support — wherever you are on your journey.
            </p>
            <div className="mt-5 flex gap-2">
              {[
                { icon: Linkedin, label: "LinkedIn" },
                { icon: Facebook, label: "Facebook" },
                { icon: Instagram, label: "Instagram" },
              ].map((s) => (
                <a
                  key={s.label}
                  href="#"
                  aria-label={s.label}
                  className="grid h-10 w-10 place-items-center rounded-full border border-border bg-card text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/10 hover:text-primary"
                >
                  <s.icon className="h-4 w-4" />
                </a>
              ))}
            </div>
          </div>

          {cols.map((c) => (
            <div key={c.title}>
              <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-foreground">{c.title}</h3>
              <ul className="mt-4 space-y-3">
                {c.links.map((l) => (
                  <li key={l.label}>
                    <a href={l.href} className="text-sm text-muted-foreground transition-colors hover:text-primary">
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border pt-8 text-center sm:flex-row sm:text-left">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Serenity. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
