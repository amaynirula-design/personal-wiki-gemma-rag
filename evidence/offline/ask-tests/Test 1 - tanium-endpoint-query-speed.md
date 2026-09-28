# Test 1: Tanium endpoint query speed

| | |
|---|---|
| Mode | **ask** (standalone; no chat history, no persona) |
| Execution | **local** · internet: **offline** |
| Model | `gemma4-e2b-qat` = google/gemma-4-E2B-it-qat-q4_0-gguf (gemma-4-E2B_q4_0-it.gguf) · Q4_0 (quantization-aware trained) |
| Runtime | ollama 0.34.4 |
| Run at | 2026-09-28T15:29:12 on Darwin 26.5.2 (arm64) |
| Test type | direct question, one source |
| Saved run | `runs/20260928-152922-ask.json` |

## Question

> How quickly can Tanium query all endpoints, and what makes that possible?

## Expected (written before the run)

- Behavior: **answer**
- Expected answer: Under 15 seconds, made possible by Tanium's linear chain architecture, which reduces server load.
- Expected sources:
- Tanium Interview Prep.docx › What does Tanium do?
- Expected passage: "What sets Tanium apart from competitors are two key innovations: First is their ability to query all endpoints in under 15 seconds, thanks to the linear chain architecture, which dramatically reduces server load."

## Step 1: retrieved passages (top 5 by BM25, in the order given to Gemma)

**[1] Tanium Interview Prep.docx › What does Tanium do? (¶24-26)** ← cited  
`vault/raw/Tanium Interview Prep.docx` · BM25 score 9.29 · matched: tanium, query, endpoint

> Tanium is an endpoint management and security platform that gives IT departments real-time visibility and control over all endpoints - laptops, servers, smartphones, and any other devices connected to the company's network.
> What sets Tanium apart from competitors are two key innovations: First is their ability to query all endpoints in under 15 seconds, thanks to the linear chain architecture, which dramatically reduces server load. (2) Its unified platform of modules that cover the full lifecycle: security, operations, patching, compliance, incident response, asset discovery, automation, and more. Tools like Tanium Guardian provide proactive vulnerability monitoring, while Tanium Automate lets teams execute playbooks and workflows that simplify everything from patching to onboarding new devices.
> Instead of stitching together multiple solutions for asset management, patching, EDR, compliance, and configuration, Tanium consolidates them into one platform. That’s why many enterprises think of Tanium as the backbone of their IT and security operations — real-time, accurate, and massively scalable.

**[2] Tanium Interview Prep.docx › Tell me about yourself and how you fit the role? (¶6-8)**  
`vault/raw/Tanium Interview Prep.docx` · BM25 score 4.34 · matched: tanium, make

> Outside of work, I love exploring different cultures through food and travel, staying active through hiking, and I’m also an amateur golfer.
> What excites me about the product management role at Tanium is that it blends everything I did well at Otis — coordinating complex projects, managing high-stakes operations, and driving measurable outcomes — but in a domain where the stakes are even higher and the scale is far greater. Tanium’s AEM system and focus on solving deep operational problems make it a place where I can apply my strengths while growing into a more product-focused role
> I think I’m a strong fit for this role because my background combines technical understanding, cross-functional leadership, and experience managing complex systems — all of which translate directly into product work at Tanium.

**[3] Tanium Interview Prep.docx › Why Cybersecurity & Tanium? (¶20-22)**  
`vault/raw/Tanium Interview Prep.docx` · BM25 score 4.21 · matched: tanium, endpoint

> My interest in cybersecurity actually started off with a canceled flight. Last year in July, I was supposed to fly Delta, but because of the CrowdStrike outage my flight was cancelled. I was annoyed in the moment, but also genuinely curious on how a single update could take down systems all around the world? That question led me down a rabbit hole because I wanted to understand the technical and operational failures that led to this catastrophe. And like anytime I’m genuinely curious about something, I ended up on Reddit reading threads from people way smarter — and way angrier — than I was.
> That curiosity pushed me deeper into endpoint security. I started comparing different companies in the space and Tanium kept appearing in those comparisons. I’d driven past your Emeryville office countless times and seen the huge Tanium logo on the building, but this was the first time I truly understood the significance of what you were building.
> After speaking with [former Tanium intern] who interned here last year and learning more about Tanium’s mission, it felt like everything aligned — the type of problems you solve, the scale you operate at, and the way the company thinks about risk. That’s why Tanium stood out to me, and why I’m excited about the opportunity today.

**[4] Tanium Interview Prep.docx › What did you do at Otis? (¶14-18)**  
`vault/raw/Tanium Interview Prep.docx` · BM25 score 3.91 · matched: quickly, tanium

> At Otis, I was a project manager managing a $47M portfolio of 50+ new construction elevator projects simultaneously. My role had three main focus areas:
> First, stakeholder coordination: I had to align multiple internal and external parties - contractors, architects, city officials, building owners - who all had different priorities and timelines. I had no direct authority over most of them, so I had to rely on leadership without formal power and bridge organizational silos to keep everyone aligned.
> Second, risk management at scale: With 50+ projects running concurrently, issues emerged constantly. I had to monitor for early warning signs, flag problems before they escalated, and coordinate rapid responses to prevent them from cascading into larger project failures. This meant developing a sense of pattern recognition for common failure and building relationships so stakeholders would escalate issues early rather than trying to solve them independently.
> Third, technical problem-solving: I was responsible for handling any technical challenges - design modifications, code compliance issues, construction conflicts - which meant quickly understanding complex problems, coming up with a game plan, and then getting team buy off in order to execute this game plan.
> Finally, beyond the three main focus areas, I had full P&L responsibility for the portfolio and was accountable for hitting financial metrics across all projects.

**[5] Tanium Interview Prep.docx › Tell me about yourself and how you fit the role? (¶3-6)**  
`vault/raw/Tanium Interview Prep.docx` · BM25 score 3.55 · matched: tanium, make

> I grew up across India and China before moving to the U.S. for college, where I studied at the University of Illinois. I majored in Materials Engineering because I had been drawn to understanding how things are built and how materials perform under stress.
> After graduation, I spent four years at Otis Elevator Company, progressing through three roles in project management. I managed a $47M portfolio of 50+ new-construction projects, coordinating installations and aligning multiple stakeholders on every project. The highlight of my time there was receiving the 2024 PM Excellence Award, which recognized both execution and leadership.
> Over time, I realized that I wanted to take on a role where I could make longer-term strategic decisions rather than focusing primarily on day-to-day execution. That led me to pursue my MBA at Haas with the intention of transitioning into the product management field in the tech space — a path where I can combine my operational experience with more strategic, product-driven work.
> Outside of work, I love exploring different cultures through food and travel, staying active through hiking, and I’m also an amateur golfer.


## Step 2: evidence quotes extracted by Gemma and verified by the harness

Verified (found word-for-word in the cited passage):
- [1] "First is their ability to query all endpoints in under 15 seconds, thanks to the linear chain architecture, which dramatically reduces server load."

Rejected (not found in the passage the model named):
- (none)

Number conflicts between sources detected by the harness:
- (none detected)

## Actual Gemma answer

```text
Tanium can query all endpoints in under 15 seconds [1]. This speed is due to the linear chain architecture, which dramatically reduces server load [1].
```

Timing: retrieval 0.1 ms · extract: 7.46 s, 1497 prompt → 56 output tokens · answer: 2.81 s, 354 prompt → 34 output tokens · total model time 10.27 s

## Automatic citation check

PASS — 1 passage(s) cited: [1]

## Assessment

**PASS.**
- *Retrieval:* the expected passage (*Tanium Interview Prep.docx › What does Tanium do?*, ¶24-26) ranked #1 (BM25 9.29, next best 4.34).
- *Evidence:* Gemma quoted exactly the expected sentence; the harness verified it in passage [1].
- *Answer:* "under 15 seconds [1]" and "linear chain architecture, which dramatically reduces server load [1]" — both claims are stated in passage [1]. I opened the original document and confirmed the wording. Citation correct.

_Official offline run (Wi-Fi off, model server restarted from local weights). Transcript: `../terminal-transcript.txt`._
