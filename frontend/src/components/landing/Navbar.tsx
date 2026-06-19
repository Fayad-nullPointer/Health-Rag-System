import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import serenityIcon from "@/assets/serenity-icon.png";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { getUser, clearAuth } from "@/lib/auth";
import { useNavigate } from "@tanstack/react-router";

const links = [
  { href: "#benefits", label: "Benefits" },
  { href: "#how", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#topics", label: "Topics" },
  { href: "#faq", label: "FAQ" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const [user, setUser] = useState(() => getUser());

  useEffect(()=>{

    const updateUser = () => {
      setUser(getUser());
    };


    window.addEventListener(
      "auth-change",
      updateUser
    );


    return () =>
      window.removeEventListener(
        "auth-change",
        updateUser
      );

  },[]);

  const handleLogout = () => {

    clearAuth();

    setUser(null); // update navbar immediately

    navigate({
      to:"/"
    });

  };

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-background/80 backdrop-blur-xl border-b border-border/50 shadow-soft" : "bg-transparent"
      }`}
    >
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4">
        <Link
          to="/"
          className="flex items-center gap-2 font-display text-lg font-bold"
        >
          <img
            src={serenityIcon}
            alt="Serenity"
            className="h-22 w-auto -my-3 object-contain"
          />
        </Link>

        <ul className="hidden items-center gap-7 md:flex">
          {links.map((l) => (
            <li key={l.href}>
              <a href={l.href} className="text-sm font-medium text-foreground/70 transition-colors hover:text-primary">
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-3 md:flex">

          {
          user ? (

          <>
            <span className="text-sm font-medium">
              Welcome, {user.full_name || user.username} 🌸
            </span>

            <Button
              variant="ghost"
              className="rounded-full"
              onClick={handleLogout}
            >
              Logout
            </Button>

          </>

          ) : (

          <>

          <Button variant="ghost" className="rounded-full" asChild>
            <Link to="/login">
              Sign in
            </Link>
          </Button>


          <Button
          className="rounded-full bg-gradient-bloom text-white shadow-soft hover:opacity-90"
          asChild
          >
          <Link to="/register">
          Start your journey
          </Link>
          </Button>

          </>

          )

          }

        </div>

        <button
          className="grid h-11 w-11 place-items-center rounded-full border border-border bg-background md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>

      {open && (
        <div className="border-t border-border bg-background/95 backdrop-blur-xl md:hidden">
          <ul className="mx-auto flex max-w-7xl flex-col gap-1 px-5 py-4">
            {links.map((l) => (
              <li key={l.href}>
                <a href={l.href} onClick={() => setOpen(false)} className="block rounded-xl px-3 py-3 text-sm font-medium hover:bg-muted">
                  {l.label}
                </a>
              </li>
            ))}
            <li className="mt-2 flex gap-2">
              {
              user ? (

              <Button
              className="flex-1 rounded-full"
              onClick={handleLogout}
              >
              Logout
              </Button>

              )

              :

              (
              <>
              <Button variant="outline" className="flex-1 rounded-full" asChild>
              <Link to="/login">Sign in</Link>
              </Button>

              <Button className="flex-1 rounded-full bg-gradient-bloom text-white" asChild>
              <Link to="/register">Start</Link>
              </Button>
              </>

              )

              }
            </li>
          </ul>
        </div>
      )}
    </header>
  );
}
