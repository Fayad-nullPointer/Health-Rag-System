import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Flower2,
  Plus,
  Settings,
  LogOut,
  Mic,
  Send,
  Menu,
  X,
  Sparkles,
  LifeBuoy,
  MessageCircle,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import sunflower from "@/assets/sunflower.png";
import serenityIcon from "@/assets/serenity-icon.png";

export const Route = createFileRoute("/chat")({
  head: () => ({
    meta: [
      { title: "Chat — Serenity" },
      { name: "description", content: "A calm, safe space to talk through what you're feeling." },
    ],
  }),
  component: ChatPage,
});

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  at: number;
};

type Conversation = {
  id: string;
  title: string;
  messages: Message[];
};

const STARTERS = [
  "I feel anxious",
  "I'm overwhelmed",
  "I feel lonely",
  "I'm stressed about work",
  "I need emotional support",
];

const CRISIS_WORDS = ["suicide", "kill myself", "end my life", "hurt myself", "self harm"];

function mockReplyFor(text: string): string {
  const t = text.toLowerCase();
  if (t.includes("anx")) return "I hear you. Anxiety can feel heavy. Let's slow it down together — can you tell me what's swirling in your mind right now?";
  if (t.includes("overwhelm")) return "That sounds like a lot to carry. You don't need to solve everything at once. What feels heaviest today?";
  if (t.includes("lonely")) return "I'm really glad you reached out. Loneliness is painful, and it doesn't mean anything is wrong with you. Tell me more about your day.";
  if (t.includes("work") || t.includes("stress")) return "Work stress builds quietly. Let's name it together — what's one thing weighing on you most right now?";
  return "Thank you for sharing that with me. I'm here, and we can take this at your pace. Would you like to explore it a little more?";
}

function newConversation(): Conversation {
  return {
    id: crypto.randomUUID(),
    title: "New conversation",
    messages: [],
  };
}

function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>(() => [newConversation()]);
  const [activeId, setActiveId] = useState(() => conversations[0].id);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [crisis, setCrisis] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const active = conversations.find((c) => c.id === activeId) ?? conversations[0];

  useEffect(() => {
    textareaRef.current?.focus();
  }, [activeId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [active?.messages.length, isTyping]);

  const updateActive = (updater: (c: Conversation) => Conversation) => {
    setConversations((cs) => cs.map((c) => (c.id === activeId ? updater(c) : c)));
  };

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    if (CRISIS_WORDS.some((w) => trimmed.toLowerCase().includes(w))) {
      setCrisis(true);
    }

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: trimmed, at: Date.now() };
    updateActive((c) => ({
      ...c,
      title: c.messages.length === 0 ? trimmed.slice(0, 40) : c.title,
      messages: [...c.messages, userMsg],
    }));
    setInput("");
    setIsTyping(true);

    setTimeout(() => {
      const reply: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: mockReplyFor(trimmed),
        at: Date.now(),
      };
      updateActive((c) => ({ ...c, messages: [...c.messages, reply] }));
      setIsTyping(false);
      textareaRef.current?.focus();
    }, 1100);
  };

  const startNew = () => {
    const c = newConversation();
    setConversations((cs) => [c, ...cs]);
    setActiveId(c.id);
    setSidebarOpen(false);
  };

  return (
    <div className="relative flex h-[100dvh] w-full overflow-hidden bg-gradient-soft">
      {/* Decorative floral background */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-32 -top-32 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 right-0 h-[28rem] w-[28rem] rounded-full bg-secondary/15 blur-3xl" />
        <img src={sunflower} alt="" className="absolute -right-10 top-1/3 h-48 w-48 opacity-20 animate-float-leaf" />
      </div>

      {/* Sidebar */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarOpen(false)}
            className="fixed inset-0 z-30 bg-foreground/40 backdrop-blur-sm md:hidden"
          />
        )}
      </AnimatePresence>

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-border bg-card/90 backdrop-blur-xl shadow-petal transition-transform md:relative md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <Link to="/" className="flex items-center gap-1 font-display font-bold">
            <img src={serenityIcon} alt="" className="h-auto w-35 object-contain" />
          </Link>
          <button className="md:hidden" aria-label="Close menu" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-4">
          <Button onClick={startNew} className="w-full rounded-full bg-gradient-bloom text-white shadow-soft hover:opacity-90">
            <Plus className="h-4 w-4" /> New conversation
          </Button>
        </div>

        <div className="mt-5 flex-1 overflow-y-auto px-3">
          <p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Recent</p>
          <ul className="space-y-1">
            {conversations.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => {
                    setActiveId(c.id);
                    setSidebarOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                    c.id === activeId ? "bg-primary/10 text-foreground" : "text-foreground/70 hover:bg-muted/60"
                  }`}
                >
                  <MessageCircle className="h-4 w-4 shrink-0 text-primary/70" />
                  <span className="truncate">{c.title}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="border-t border-border p-3">
          <div className="flex items-center gap-3 rounded-xl bg-muted/50 px-3 py-2.5">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-gradient-bloom text-sm font-semibold text-white">
              Y
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">You</p>
              <p className="truncate text-xs text-muted-foreground">Free plan</p>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Button variant="ghost" size="sm" className="justify-start rounded-lg">
              <Settings className="h-4 w-4" /> Settings
            </Button>
            <Button variant="ghost" size="sm" className="justify-start rounded-lg" asChild>
              <Link to="/login">
                <LogOut className="h-4 w-4" /> Logout
              </Link>
            </Button>
          </div>
        </div>
      </aside>

      {/* Chat area */}
      <main className="relative z-10 flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="flex items-center gap-3 border-b border-border/60 bg-background/60 px-4 py-3 backdrop-blur-xl">
          <button
            className="grid h-10 w-10 place-items-center rounded-full border border-border bg-background md:hidden"
            aria-label="Open menu"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-bloom text-white shadow-soft">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate font-display text-sm font-semibold">Serenity</p>
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-secondary opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-secondary" />
                </span>
                Online · here for you
              </p>
            </div>
          </div>
          <Button variant="outline" size="icon" className="rounded-full" aria-label="Voice chat (coming soon)" disabled>
            <Mic className="h-4 w-4" />
          </Button>
        </header>

        {/* Crisis banner */}
        <AnimatePresence>
          {crisis && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="mx-4 mt-3 flex items-start gap-3 rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm"
            >
              <LifeBuoy className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
              <div className="flex-1">
                <p className="font-semibold text-destructive">You are not alone.</p>
                <p className="mt-1 text-foreground/80">
                  If you're in crisis, please reach out now. Call or text <strong>988</strong> (US Suicide & Crisis Lifeline), or visit your local emergency services.
                </p>
              </div>
              <button onClick={() => setCrisis(false)} aria-label="Dismiss" className="text-destructive/70 hover:text-destructive">
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          {active.messages.length === 0 ? (
            <EmptyState onPick={send} />
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-4">
              <AnimatePresence initial={false}>
                {active.messages.map((m) => (
                  <MessageBubble key={m.id} message={m} />
                ))}
              </AnimatePresence>
              {isTyping && <TypingBubble />}
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="border-t border-border/60 bg-background/70 px-4 py-4 backdrop-blur-xl sm:px-8">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="mx-auto flex max-w-3xl items-end gap-2 rounded-3xl border border-border bg-card p-2 shadow-soft focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20"
          >
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send(input);
                }
              }}
              placeholder="Share what's on your mind…"
              rows={1}
              className="min-h-[44px] flex-1 resize-none border-0 bg-transparent px-3 py-2.5 text-sm shadow-none focus-visible:ring-0"
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="shrink-0 rounded-full text-muted-foreground"
              aria-label="Voice input (coming soon)"
              disabled
            >
              <Mic className="h-4 w-4" />
            </Button>
            <Button
              type="submit"
              size="icon"
              className="shrink-0 rounded-full bg-gradient-bloom text-white shadow-soft hover:opacity-90"
              aria-label="Send message"
              disabled={!input.trim()}
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
          <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted-foreground">
            Serenity offers supportive guidance, not medical advice. In an emergency, call 988 or your local services.
          </p>
        </div>
      </main>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (s: string) => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="mx-auto flex max-w-2xl flex-col items-center justify-center py-10 text-center"
    >
      <div className="relative mb-6">
        <div className="absolute inset-0 -z-10 rounded-full bg-gradient-sunlight blur-2xl" />
        <img src={sunflower} alt="" className="h-40 w-40 animate-sway" />
      </div>
      <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
        What would you like to talk about today?
      </h1>
      <p className="mt-3 text-muted-foreground">
        This is a safe space. Take your time — there's no right way to start.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        {STARTERS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="rounded-full border border-primary/20 bg-primary/5 px-4 py-2 text-sm font-medium text-foreground/80 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-primary/10 hover:text-primary"
          >
            {s}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={`flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-bloom text-white">
          <Sparkles className="h-4 w-4" />
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-3xl px-4 py-3 text-sm leading-relaxed shadow-soft ${
          isUser
            ? "rounded-br-md bg-gradient-bloom text-primary-foreground"
            : "rounded-bl-md border border-border bg-card text-foreground"
        }`}
      >
        {message.content}
      </div>
    </motion.div>
  );
}

function TypingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-end gap-2"
    >
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-bloom text-white">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="flex items-center gap-1.5 rounded-3xl rounded-bl-md border border-border bg-card px-4 py-3 shadow-soft">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-bounce rounded-full bg-primary/60"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </motion.div>
  );
}
