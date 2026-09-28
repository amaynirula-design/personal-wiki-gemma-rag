# Test 2: TikTok Shop take rate (paraphrased)

| | |
|---|---|
| Mode | **ask** (standalone; no chat history, no persona) |
| Execution | **local** · internet: **online** |
| Model | `gemma4-e2b-qat` = google/gemma-4-E2B-it-qat-q4_0-gguf (gemma-4-E2B_q4_0-it.gguf) · Q4_0 (quantization-aware trained) |
| Runtime | ollama 0.34.4 |
| Run at | 2026-09-28T10:39:31 on Darwin 26.5.2 (arm64) |
| Test type | answerable, worded differently from the source |
| Saved run | `runs/20260928-103959-ask.json` |

## Question

> What cut does TikTok take when someone buys something through TikTok Shop?

## Expected (written before the run)

- Behavior: **answer**
- Expected answer: A seller commission of typically 2-8% per transaction depending on category; TikTok also charges sellers to advertise their products.
- Expected sources:
- Tiktok Interview Prep.docx › How does Tiktok monetize?
- Expected passage: "taking a commission on every transaction, typically 2-8% depending on category, and charging sellers to advertise their products on the platform."

## Retrieved passages (top 5, in the order given to Gemma)

**[1] Tiktok Interview Prep.docx › How does Tiktok monetize? (¶20-22)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 11.66 · matched: cut, tiktok, take, shop

> Third, brand partnerships - these are premium, high-value deals like branded hashtag challenges where brands pay $150K-500K+, brand takeover days for exclusive daily placement, and large-scale brand awareness campaigns. These command premium pricing compared to standard advertising.
> And fourth, virtual gifts - when users send gifts like roses or galaxies to creators during LIVE streams to show appreciation, TikTok takes a cut of those transactions before paying out creators.
> The key insight is that TikTok Shop's growth shows they're successfully diversifying beyond pure advertising into commerce, which improves their revenue resilience and deepens user engagement on the platform

**[2] Tiktok Interview Prep.docx › How does Tiktok monetize? (¶12-20)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 9.85 · matched: cut, tiktok, take, shop

> - Ads: In-feed (every 2 to 3 videos) & top view ads (as soon as you open the app).
> - Tiktok shop: Charges seller commission on every transaction & sellers have to pay to advertise their products. HIGHEST growth over the past two years.
> - Brand partnerships – Hashtag challenges, Brand takeover days, Brand Awareness campaign.
> - Gifts to Creators- When people give roses or galaxies to creators to show appreciation, tiktok gets a cut.
> Sample Answer:
> TikTok has four main revenue streams, with advertising being the largest.
> First, advertising - primarily through in-feed ads that appear every 2-3 videos in the For You Page, and TopView ads that take over the screen when users first open the app. This is their core revenue driver.
> Second, TikTok Shop, which has seen the highest growth over the past two years. They monetize this in two ways: taking a commission on every transaction, typically 2-8% depending on category, and charging sellers to advertise their products on the platform. This creates a dual revenue stream where TikTok profits both from the sale itself and from the ads driving traffic to those products.
> Third, brand partnerships - these are premium, high-value deals like branded hashtag challenges where brands pay $150K-500K+, brand takeover days for exclusive daily placement, and large-scale brand awareness campaigns. These command premium pricing compared to standard advertising.

**[3] Tiktok Interview Prep.docx › Who are Tiktok’s competitors and what are their strengths? (¶24-30)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 8.41 · matched: tiktok, someth, shop

> Sample Answer:
> Meta's biggest strength is cross-platform targeting which means it can track users across Facebook, Instagram, WhatsApp, and Messenger,
> from a monetization perspective, they can give advertisers incredibly rich data and the ability to reach users across multiple touchpoints.
> They also have deep user data from two decades of social networking, which enables sophisticated targeting that TikTok is still building.
> YouTube's strength is their unmatched scale - they have over 2 billion monthly users globally and offer both long-form and short-form content with Shorts, which means they can monetize both forms of video content.
> They also benefit from Google's ad tech infrastructure, which is the most sophisticated in the industry with advanced analytics, attribution, and measurement tools that advertisers trust.
> - Amazon competes directly with TikTok Shop, and their strength is unbeatable logistics and delivery speed. Their fulfillment infrastructure is so advanced that you can order something at 1 AM and have it delivered by 8 AM the same morning. TikTok Shop simply can't match that level of operational excellence and customer trust in delivery reliability. Amazon also has decades of customer reviews, return policies, and Prime loyalty that TikTok is years away from replicating.

**[4] Tiktok Interview Prep.docx › What are Tiktok’s strengths? (¶32-46)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 7.15 · matched: tiktok, buys, shop

> Algorithm Superiority:
> - Best in class recommendations
> - Keeps users engaged longer
> - Markes ads feel native to the app. Ads feel like just another reel
> - Introducting long format videos to compete with the likes of YT. Uploaded reels can now be up to 60 mins.
> Users:
> - Gen Z dominant.
> - Highly engaged audience that drives a high engagement rate with plenty of comments, likes and sharing of reels.
> Tiktok Shop Integration:
> - Seamless purchasing experience
> - Live Shopping and Flash Sales create urgency
> - Lower barrier for impulse buys.
> TikTok has three core competitive advantages that set them apart.
> First, algorithm superiority - they have best-in-class content recommendations that keep users engaged significantly longer than competitors. What's particularly powerful is that their algorithm makes ads feel native to the platform - ads blend seamlessly into the feed and feel like just another piece of content rather than an interruption. This is crucial for advertisers because users don't skip or tune out.
> Second, their user base and engagement - TikTok is Gen Z dominant, and this demographic is incredibly active on the platform spending around 95 mins on the app every day, which is far higher than competitors. They don't just passively watch; they drive high engagement rates through comments, likes, and sharing content. This creates a viral flywheel that advertisers can tap into, where content spreads organically much faster than on other platforms.

**[5] Tanium Interview Prep.docx › Why Cybersecurity & Tanium? (¶20-22)**  
`vault/raw/Tanium Interview Prep.docx` · BM25 score 5.73 · matched: take, someth

> My interest in cybersecurity actually started off with a canceled flight. Last year in July, I was supposed to fly Delta, but because of the CrowdStrike outage my flight was cancelled. I was annoyed in the moment, but also genuinely curious on how a single update could take down systems all around the world? That question led me down a rabbit hole because I wanted to understand the technical and operational failures that led to this catastrophe. And like anytime I’m genuinely curious about something, I ended up on Reddit reading threads from people way smarter — and way angrier — than I was.
> That curiosity pushed me deeper into endpoint security. I started comparing different companies in the space and Tanium kept appearing in those comparisons. I’d driven past your Emeryville office countless times and seen the huge Tanium logo on the building, but this was the first time I truly understood the significance of what you were building.
> After speaking with [former Tanium intern] who interned here last year and learning more about Tanium’s mission, it felt like everything aligned — the type of problems you solve, the scale you operate at, and the way the company thinks about risk. That’s why Tanium stood out to me, and why I’m excited about the opportunity today.


## Actual Gemma answer

```text
INSUFFICIENT EVIDENCE: The provided passages state that TikTok takes a commission on every transaction through TikTok Shop, typically 2-8% depending on the category, but they do not specify the exact cut taken.
```

Model call: 8.79 s wall · 1719 prompt tokens · 44 output tokens · 19.7 tok/s · retrieval 0.3 ms

## Automatic citation check

insufficient-evidence response

## Assessment

**FAIL — over-refusal.** Retrieval was correct: the expected sentence ("typically 2-8% depending on category") is in passage [2]. The model even quoted the 2-8% figure but still answered INSUFFICIENT EVIDENCE, apparently because the question says "cut" while the source says "commission". Failure is in the model's sufficiency judgment, not retrieval. Fix tried next: extract-then-answer pipeline (see online-dev-run-2).

_This is the first development run (single-prompt RAG, before fixes). Kept unchanged as evidence._
