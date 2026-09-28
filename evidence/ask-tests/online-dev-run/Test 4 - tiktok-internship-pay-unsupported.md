# Test 4: TikTok internship pay (unsupported)

| | |
|---|---|
| Mode | **ask** (standalone; no chat history, no persona) |
| Execution | **local** · internet: **online** |
| Model | `gemma4-e2b-qat` = google/gemma-4-E2B-it-qat-q4_0-gguf (gemma-4-E2B_q4_0-it.gguf) · Q4_0 (quantization-aware trained) |
| Runtime | ollama 0.34.4 |
| Run at | 2026-09-28T10:39:31 on Darwin 26.5.2 (arm64) |
| Test type | plausible question the wiki cannot answer |
| Saved run | `runs/20260928-104018-ask.json` |

## Question

> What is the salary or hourly pay for the TikTok Monetization Strategy & Ops internship?

## Expected (written before the run)

- Behavior: **insufficient_evidence**
- Expected answer: INSUFFICIENT EVIDENCE — the sources do not mention internship pay.
- Expected sources:
- (none — unanswerable)
- Expected passage: None. The TikTok prep discusses why MSO and TikTok's monetization, but never compensation.

## Retrieved passages (top 5, in the order given to Gemma)

**[1] Tiktok Interview Prep.docx › Why do you want to work for Tiktok and why MSO? (¶95-97)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 10.72 · matched: tiktok, monet, strategy, ops

> I’m drawn to TikTok because it’s a trendsetter in a highly competitive industry and revolutionized how brands approach marketing — from the polished ads we used to see on TV to a more raw, unpolished, and authentic experience that really connects with Gen Z audiences who value connection over perfection. I think that shift in how brands communicate is incredibly powerful.
> I want to work in MSO because I love working on monetization, revenue and really increasing bottom line revenue for my products. This interest in monetization and revenue building stems from Otis and its business model. Almost every project that I worked on at Otis was sold at cost, 0% margin, and it was up to me to turn this ship around and hit my profit goals of 5-10%. I became obsesses with finding every lever to drive revenue, whether it was negotiationg with supliers to get better pricing on materials, working with mechanics to figure out a more effeicient installation process or upselling products and service to our customers. I loved using insights and turning operational efficiency into financial results.
> I’m especially excited about the Monetization Strategy & Ops team because it sits right at the intersection of creativity, data, and business impact. The team’s focus on understanding revenue trends, optimizing ad effectiveness, and launching new monetization models aligns perfectly with my background, which is combining execution skills from project management with an analytical, data-driven mindset

**[2] Tiktok Interview Prep.docx › How does Tiktok monetize? (¶20-22)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 8.58 · matched: pay, tiktok, monet

> Third, brand partnerships - these are premium, high-value deals like branded hashtag challenges where brands pay $150K-500K+, brand takeover days for exclusive daily placement, and large-scale brand awareness campaigns. These command premium pricing compared to standard advertising.
> And fourth, virtual gifts - when users send gifts like roses or galaxies to creators during LIVE streams to show appreciation, TikTok takes a cut of those transactions before paying out creators.
> The key insight is that TikTok Shop's growth shows they're successfully diversifying beyond pure advertising into commerce, which improves their revenue resilience and deepens user engagement on the platform

**[3] Tiktok Interview Prep.docx › How does Tiktok monetize? (¶12-20)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 8.57 · matched: pay, tiktok, monet

> - Ads: In-feed (every 2 to 3 videos) & top view ads (as soon as you open the app).
> - Tiktok shop: Charges seller commission on every transaction & sellers have to pay to advertise their products. HIGHEST growth over the past two years.
> - Brand partnerships – Hashtag challenges, Brand takeover days, Brand Awareness campaign.
> - Gifts to Creators- When people give roses or galaxies to creators to show appreciation, tiktok gets a cut.
> Sample Answer:
> TikTok has four main revenue streams, with advertising being the largest.
> First, advertising - primarily through in-feed ads that appear every 2-3 videos in the For You Page, and TopView ads that take over the screen when users first open the app. This is their core revenue driver.
> Second, TikTok Shop, which has seen the highest growth over the past two years. They monetize this in two ways: taking a commission on every transaction, typically 2-8% depending on category, and charging sellers to advertise their products on the platform. This creates a dual revenue stream where TikTok profits both from the sale itself and from the ads driving traffic to those products.
> Third, brand partnerships - these are premium, high-value deals like branded hashtag challenges where brands pay $150K-500K+, brand takeover days for exclusive daily placement, and large-scale brand awareness campaigns. These command premium pricing compared to standard advertising.

**[4] Tiktok Interview Prep.docx › Introduction (¶1-10)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 7.68 · matched: tiktok, monet, ops

> • How does Tiktok Monetize? (Shop, Ads, Content Creator Marketplace, Commissions, brand deals)
> • Who are Tiktok’s competitors? (Meta, YT, Amazon)
> • What are their Strengths? (Cross-platform targeting, social, messaging elements)
> • What are Tiktok’s strengths? (Algorithm -> Organic, Natural, Ads feel authentic + Tiktok Shop -> Seamless experience + AI driven content and ad creation and management)
> • What are the types of Ad formats?
> • What metrics are associate with each type of Ad (Think Top of Funnel vs Bottom of Funnel -> Daily users, Engagement, Clickthrough rate)
> • How would you go about deciding the pricing for an Ad for a client? (CPM/CPC/CPV -> What are multipliers, what is the math behind calculating these metrics)
> • What would you investigate from an Ops standpoint if you missed Revenue or Cost targets at Tiktok?
> • Really explain how your current career trajectory NEEDS tiktok as the next step?
> • What kind of ad/marketing campaign would you recommend for this kind of client? (Branded hashtags, Filters, Ads, Influencer Marketing)

**[5] Tiktok Interview Prep.docx › Who are Tiktok’s competitors and what are their strengths? (¶24-30)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 5.43 · matched: tiktok, monet

> Sample Answer:
> Meta's biggest strength is cross-platform targeting which means it can track users across Facebook, Instagram, WhatsApp, and Messenger,
> from a monetization perspective, they can give advertisers incredibly rich data and the ability to reach users across multiple touchpoints.
> They also have deep user data from two decades of social networking, which enables sophisticated targeting that TikTok is still building.
> YouTube's strength is their unmatched scale - they have over 2 billion monthly users globally and offer both long-form and short-form content with Shorts, which means they can monetize both forms of video content.
> They also benefit from Google's ad tech infrastructure, which is the most sophisticated in the industry with advanced analytics, attribution, and measurement tools that advertisers trust.
> - Amazon competes directly with TikTok Shop, and their strength is unbeatable logistics and delivery speed. Their fulfillment infrastructure is so advanced that you can order something at 1 AM and have it delivered by 8 AM the same morning. TikTok Shop simply can't match that level of operational excellence and customer trust in delivery reliability. Amazon also has decades of customer reviews, return policies, and Prime loyalty that TikTok is years away from replicating.


## Actual Gemma answer

```text
INSUFFICIENT EVIDENCE: The provided passages do not contain information about the salary or hourly pay for the TikTok Monetization Strategy & Ops internship.
```

Model call: 8.03 s wall · 1694 prompt tokens · 30 output tokens · 19.5 tok/s · retrieval 0.4 ms

## Automatic citation check

insufficient-evidence response

## Assessment

**PASS.** No passage mentions pay; the model answered INSUFFICIENT EVIDENCE without citing anything.

_This is the first development run (single-prompt RAG, before fixes). Kept unchanged as evidence._
