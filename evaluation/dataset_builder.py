eval_queries = [
    # ---------------- BASIC BUT REALISTIC ----------------
    {"query": "I feel anxious and depressed. What should I do?"},
    {"query": "How can I deal with loneliness?"},
    {"query": "I feel worthless and can't sleep. Help me."},
    {"query": "I can't sleep because of overthinking"},
    {"query": "I feel empty after relationship issues"},

    # ---------------- MORE COMPLEX ENGLISH ----------------
    {"query": "I've been feeling emotionally drained for weeks, losing motivation, and I can't tell if it's burnout or depression. What should I do?"},
    {"query": "I keep overthinking every small mistake I make at work, and it's affecting my sleep and confidence. How can I stop this cycle?"},
    {"query": "I feel detached from people even when I'm surrounded by friends. Is this normal or something serious?"},
    {"query": "After a breakup, I feel like I lost my sense of identity and daily routine feels meaningless. How do I recover?"},
    {"query": "I experience sudden anxiety attacks without any clear reason, and I don't understand why it's happening."},
    {"query": "I keep comparing myself to others on social media and it makes me feel like I'm failing in life."},
    {"query": "I feel stuck in life with no direction, even though nothing objectively bad is happening."},
    {"query": "I have trouble sleeping because I replay conversations in my head and feel regret or embarrassment."},

    # ---------------- ARABIC SIMPLE ----------------
    {"query": "أشعر بالقلق والاكتئاب، ماذا أفعل؟"},
    {"query": "كيف أتعامل مع الشعور بالوحدة؟"},
    {"query": "لا أستطيع النوم بسبب كثرة التفكير"},
    {"query": "أشعر بأنني بلا قيمة ولا أستطيع التركيز"},
    {"query": "أشعر بفراغ بعد انتهاء علاقة عاطفية"},

    # ---------------- ARABIC COMPLEX / NATURAL ----------------
    {"query": "أشعر أني مرهق نفسيًا منذ فترة طويلة ولا أستطيع الاستمتاع بأي شيء، هل هذا اكتئاب أم مجرد ضغط؟"},
    {"query": "أفكر كثيرًا في أخطائي الماضية وهذا يجعلني أفقد النوم والثقة بنفسي، كيف أوقف هذا التفكير؟"},
    {"query": "أشعر بالانفصال عن الناس حتى وأنا معهم، وكأنني غير موجود، هل هذا طبيعي؟"},
    {"query": "بعد انتهاء علاقة مهمة في حياتي، أشعر أني فقدت هويتي ولا أعرف كيف أبدأ من جديد"},
    {"query": "تأتيني نوبات قلق مفاجئة بدون سبب واضح وأشعر بخوف شديد لا أستطيع تفسيره"},
    {"query": "أقارن نفسي دائمًا بالآخرين على وسائل التواصل وهذا يجعلني أشعر أنني متأخر في حياتي"},
    {"query": "أشعر أن حياتي بلا هدف رغم أن كل شيء يبدو طبيعيًا من الخارج"},
    {"query": "أعيد في رأسي كل موقف محرج حدث لي وأشعر بالندم الشديد"},

     # ================= MULTI-INTENT (ENGLISH) =================
    {
        "query": "I can't sleep, I keep overthinking work mistakes, and I feel like I'm not good enough anymore. What can I do?"
    },
    {
        "query": "I feel anxious most of the day, I lost motivation to study, and I also avoid talking to people. What's happening to me?"
    },
    {
        "query": "After my breakup, I feel lonely, my sleep is broken, and I keep checking my ex's social media. How do I stop this?"
    },
    {
        "query": "I feel burned out from work, I can't focus anymore, and I'm starting to question if I even like my life right now."
    },
    {
        "query": "I keep feeling anxious without reason, I also feel tired all the time, and I don't enjoy things like before."
    },
    {
        "query": "I feel stuck in life, my sleep schedule is ruined, and I keep comparing myself to others online."
    },
    {
        "query": "I feel emotionally numb, I can't connect with people, and I don't know if this is stress or something else."
    },

    # ================= NON-CLINICAL / AMBIGUOUS (ENGLISH) =================
    {
        "query": "I don't feel like myself lately. Everything feels off but I can't explain why."
    },
    {
        "query": "I feel weird recently, like I'm just existing and not really living."
    },
    {
        "query": "I think I'm just tired of everything, but nothing in my life is actually bad."
    },
    {
        "query": "I don't know what's wrong with me, I just feel off and disconnected."
    },
    {
        "query": "I feel fine on paper, but inside I feel empty and unmotivated."
    },
    {
        "query": "Sometimes I feel okay, but suddenly I get overwhelmed for no reason."
    },
]