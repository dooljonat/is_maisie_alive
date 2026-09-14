"""Keyword-based spam filter for guest comments.

No one on a pug blog says "boost your Google rankings." The filter scores a
comment against sales/SEO vocabulary and rejects anything that trips the
threshold — plus a few patterns (URLs, prices, contact grabs) that are damning
on their own. Kept deliberately blunt: a false positive costs Dad one retyped
comment, a false negative puts an SEO pitch under a photo of a sleeping dog.
"""
import re

# Terms that have no business in a dog-blog comment. One alone isn't proof;
# the threshold below is what decides.
SPAM_TERMS = [
    # sales / marketing vocabulary
    "advertise", "advertising", "advertisement", "marketing", "campaign",
    "impactful", "engaging", "conversion", "conversions", "leads",
    "lead generation", "roi", "outreach", "cold email", "promote",
    "promotion", "brand awareness", "boost your", "grow your", "scale your",
    "drive traffic", "generate results", "impressive results",
    # SEO
    "seo", "search engine", "google ranking", "google rankings", "rankings",
    "backlink", "backlinks", "keyword research", "organic growth",
    "organic traffic", "first page of google", "domain authority",
    "web traffic", "page speed",
    # agency / pitch framing
    "our team", "our agency", "our company", "our videos", "our services",
    "proposal", "pricing proposal", "portfolio", "samples of our",
    "previous work", "free consultation", "free quote", "free trial",
    "no obligation", "let me know if you're interested",
    "would you be open", "happy to send", "send some over", "send over",
    "i can show you", "just visited your", "looking over your website",
    "noticed a few", "i was looking over",
    # web-dev / design cold pitches
    "web design", "website redesign", "mobile friendly", "wordpress",
    "e-commerce", "ecommerce", "app development", "software development",
    "outsourcing", "offshore", "dedicated developers",
    # money / crypto / pharma
    "make money", "earn money", "passive income", "work from home",
    "investment opportunity", "crypto", "bitcoin", "forex", "casino",
    "viagra", "cialis", "pharmacy", "weight loss", "cbd",
    # generic business-speak that never appears in family comments
    "your business", "your brand", "your company", "b2b", "clients",
    "client base", "customer base", "revenue", "sales team",
]

# Mentioning the site by name is what family does, not what spammers do.
OWN_DOMAIN = re.compile(r"\bis\s?maisie\s?alive\.(?:org|net|com)\b", re.I)

# Individually damning patterns: a single hit is enough.
HARD_PATTERNS = [
    (re.compile(r"https?://|www\.\w|\w+\.(?:com|net|org|io|biz|ru|cn)\b", re.I), "link"),
    (re.compile(r"\$\s?\d{2,}|\b\d{2,}\s?(?:usd|dollars)\b", re.I), "price quote"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.\w{2,}\b"), "email address"),
    (re.compile(r"\b(?:whatsapp|telegram|skype)\b", re.I), "messaging handle"),
    (re.compile(r"<\s*a\s|\[url", re.I), "markup link"),
]

# Two soft terms are a coincidence; three is a sales pitch.
SOFT_THRESHOLD = 3


# Runs of single letters separated by spaces/dots ("s e o", "b.o.o.s.t").
_SPACED_OUT = re.compile(r"\b(?:[a-z][\s.\-_*]+){2,}[a-z]\b")


def _normalize(text: str) -> str:
    """Lowercase and undo the usual filter-evasion tricks."""
    lowered = text.lower()
    # Leetspeak substitutions: adverti$e, m0ney, v1agra.
    for bad, good in (("$", "s"), ("0", "o"), ("1", "i"), ("3", "e"), ("@", "a")):
        lowered = lowered.replace(bad, good)
    lowered = re.sub(r"\s+", " ", lowered)
    # Squash letter-spacing evasion, then keep both forms so ordinary text
    # (initials, "I am") still matches normally.
    squashed = _SPACED_OUT.sub(lambda m: re.sub(r"[\s.\-_*]", "", m.group()), lowered)
    return f"{lowered} {squashed}" if squashed != lowered else lowered


def check(author: str, body: str) -> tuple[bool, str]:
    """Return (is_spam, reason). Reason is empty when the comment is clean."""
    haystack = _normalize(f"{author} {body}")
    # Drop self-references before link detection so "I love ismaisiealive.org"
    # from a relative isn't mistaken for a spammer dropping a URL.
    haystack = OWN_DOMAIN.sub(" this site ", haystack)

    for pattern, label in HARD_PATTERNS:
        if pattern.search(haystack):
            return True, label

    hits = [term for term in SPAM_TERMS if term in haystack]
    if len(hits) >= SOFT_THRESHOLD:
        return True, "sales vocabulary: " + ", ".join(hits[:5])

    return False, ""
