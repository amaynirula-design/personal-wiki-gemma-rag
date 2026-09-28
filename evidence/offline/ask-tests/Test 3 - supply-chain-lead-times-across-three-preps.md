# Test 3: Supply chain lead times across three preps

| | |
|---|---|
| Mode | **ask** (standalone; no chat history, no persona) |
| Execution | **local** · internet: **offline** |
| Model | `gemma4-e2b-qat` = google/gemma-4-E2B-it-qat-q4_0-gguf (gemma-4-E2B_q4_0-it.gguf) · Q4_0 (quantization-aware trained) |
| Runtime | ollama 0.34.4 |
| Run at | 2026-09-28T15:29:12 on Darwin 26.5.2 (arm64) |
| Test type | known evidence connecting several sources (with a discrepancy) |
| Saved run | `runs/20260928-152946-ask.json` |

## Question

> In my Otis supply chain delay story, how much did material lead times increase, and how did I keep projects on schedule?

## Expected (written before the run)

- Behavior: **answer**
- Expected answer: Lead times rose to 16 weeks — from 10 weeks in the Amazon prep, but from 12 weeks in the Tanium and TikTok preps (the sources disagree). Projects stayed on schedule through partial shipments from the factory and overtime from field mechanics.
- Expected sources:
- Amazon Interview.docx › 2. Tell me about a time you used multiple resources...
- Tanium Interview Prep.docx › Tell me about a time you used multiple resources...
- Tiktok Interview Prep.docx › Tell me about a time you used multiple resources...
- Expected passage: Amazon: "increased our material lead times from 10 to 16 weeks". Tanium and TikTok: "increased our material lead times from 12 to 16 weeks". All three: partial shipments from the factory plus field-mechanic overtime.

## Step 1: retrieved passages (top 5 by BM25, in the order given to Gemma)

**[1] Amazon Interview.docx › Tell me about a time you used multiple resources to overcome a challenge/had to work un... (¶25-28)** ← cited  
`vault/raw/Amazon Interview.docx` · BM25 score 19.26 · matched: supply, chain, delay, material, lead, time, keep, project, schedule

> Last year, supply chain disruptions increased our material lead times from 10 to 16 weeks, putting multiple projects at risk of significant delays. I had to inform customers of this bad news, and understandably, they were not happy.
> I needed to keep projects on schedule despite the delays and maintain customer satisfaction. This was important to me because I had committed to these timelines, and I knew delays would damage both customer relationships and our reputation for reliable delivery.
> I took a two-pronged approach leveraging different resources. First, I worked with our factory to implement partial shipments - getting materials shipped as they became available rather than waiting for complete orders. This allowed our mechanics to start assembly immediately with available parts and install missing components later. Second, I coordinated with our field mechanics to put in significant overtime to make up for any remaining schedule gaps and ensure we hit our deadlines.
> By strategically using both factory flexibility and mechanic capacity, I kept all projects on track and maintained customer satisfaction despite the supply chain crisis. Customers appreciated the proactive problem-solving, and we didn't lose any projects due to delays.

**[2] Tanium Interview Prep.docx › Tell me about a time you used multiple resources to overcome a challenge/had to work un... (¶46-49)** ← cited  
`vault/raw/Tanium Interview Prep.docx` · BM25 score 19.15 · matched: supply, chain, delay, material, lead, time, keep, project, schedule

> Last year, supply chain disruptions increased our material lead times from 12 to 16 weeks, putting multiple projects at risk of significant delays. I had to inform customers of this bad news, and understandably, they were not happy.
> I knew I needed to keep projects on schedule despite delays in order to maintain customer satisfaction and our reputation for reliable delivery.
> I took a novel two-pronged approach leveraging different resources. First, I worked with our factory to implement partial shipments - getting materials shipped as they became available rather than waiting for complete orders. This allowed our mechanics to start assembly immediately with available parts and install missing components later. Second, I coordinated with our field mechanics to put in significant overtime to make up for any remaining schedule gaps and ensure we hit our deadlines.
> By strategically using both factory flexibility and mechanic capacity, I kept all projects on track and maintained customer satisfaction despite the supply chain crisis. Customers appreciated the proactive problem-solving, and we didn't lose any projects due to delays.

**[3] Tiktok Interview Prep.docx › Tell me about a time you used multiple resources to overcome a challenge/had to work un... (¶64-67)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 19.14 · matched: supply, chain, delay, material, lead, time, keep, project, schedule

> Last year, supply chain disruptions increased our material lead times from 12 to 16 weeks, putting multiple projects at risk of significant delays. I had to inform customers of this bad news, and understandably, they were not happy.
> I needed to keep projects on schedule despite the delays and maintain customer satisfaction. This was important to me because I had committed to these timelines, and I knew delays would damage both customer relationships and our reputation for reliable delivery.
> I took a two-pronged approach leveraging different resources. First, I worked with our factory to implement partial shipments - getting materials shipped as they became available rather than waiting for complete orders. This allowed our mechanics to start assembly immediately with available parts and install missing components later. Second, I coordinated with our field mechanics to put in significant overtime to make up for any remaining schedule gaps and ensure we hit our deadlines.
> By strategically using both factory flexibility and mechanic capacity, I kept all projects on track and maintained customer satisfaction despite the supply chain crisis. Customers appreciated the proactive problem-solving, and we didn't lose any projects due to delays.

**[4] Amazon Interview.docx › Why Amazon? (¶7-9)**  
`vault/raw/Amazon Interview.docx` · BM25 score 7.87 · matched: otis, delay, keep, project, schedule

> I would like to work for Amazon because it’s managed to build the most sophisticated delivery and logistics network in the world. Moreover, it’s also managed to defend that advantage for decades against competitors like Walmart, Target, and now Tiktok Shop. What really sets Amazon apart besides the technology is its operational excellence at a massive scale.
> At Otis, I managed a $47M portfolio across 50+ construction projects where I learned that great operations come down to always putting your customer first and delivering on your commitments. When delays cascaded, it directly impacted families moving into buildings or businesses opening on schedule. That experience taught me the same thing I see at Amazon: keep the customer at the center and deliver on your promises.
> Whether it’s promising same-day delivery or the use of robotics in fulfillment centers, Amazon continually raises the bar for reliability and speed. I’d love to be part of the team that maintains that operational edge and helps drive the next generation of improvements.

**[5] Tiktok Interview Prep.docx › Tell me about a time you had to overcome challenges when working with a team (cross-fun... (¶55-62)**  
`vault/raw/Tiktok Interview Prep.docx` · BM25 score 6.26 · matched: supply, delay, project, schedule

> - On my largest project to date, Graton Casino Expansion, a $2.9M project, I was coordinating between our internal teams and external stakeholders including architects, general contractors, and global supply vendors.
> - The challenge here was that everyone had competing priorities. The customer wanted premium customizations, vendors were pushing back on the timeline stating that this was not feasible and my internal team was worried about scope creep.
> - My task was to align all of these different parties and deliver the project without any overruns or delays.
> - Established weekly coordination meetings
> - Purpose was to understand each team’s constrains and then coming up with compromises like identifying which customizations we could adopt without impacting deadlines greatly
> - Presented all possible options to the client with cost and time implications.
> - The result was that we delivered the $2.9M project with over $400k in customizations on schedule.
> - The structured communication prevented small misalignments from becoming major conflicts, and the client was satisfied with both the process and outcome.


## Step 2: evidence quotes extracted by Gemma and verified by the harness

Verified (found word-for-word in the cited passage):
- [1] "Last year, supply chain disruptions increased our material lead times from 10 to 16 weeks, putting multiple projects at risk of significant delays."
- [2] "Last year, supply chain disruptions increased our material lead times from 12 to 16 weeks, putting multiple projects at risk of significant delays."

Rejected (not found in the passage the model named):
- (none)

Number conflicts between sources detected by the harness:
- passage(s) [1] say 10 / 16; passage(s) [2] say 12 / 16

## Actual Gemma answer

```text
The owner stated that supply chain disruptions increased material lead times from 10 to 16 weeks [1]. Another source states that supply chain disruptions increased material lead times from 12 to 16 weeks [2]. The sources disagree on the initial increase in lead times.
```

Timing: retrieval 0.3 ms · extract: 9.4 s, 1487 prompt → 93 output tokens · answer: 4.68 s, 512 prompt → 58 output tokens · total model time 14.08 s

## Automatic citation check

CHECK — 2 passage(s) cited: [1], [2]; 1 sentence(s) without a citation

## Assessment

**PARTIAL PASS — conflict handled correctly, second half of the question not answered.**
- *Retrieval:* correct. All three versions of the story (Amazon, Tanium, TikTok) ranked #1-3 with near-identical scores.
- *Evidence:* Gemma quoted the lead-time sentence from the Amazon [1] and Tanium [2] passages only — not the TikTok passage [3] (which also says 12 to 16), and none of the sentences about *how* projects stayed on schedule.
- *Answer:* "from 10 to 16 weeks [1]" (Amazon — correct) and "from 12 to 16 weeks [2]" (Tanium — correct), and it states that the sources disagree. That is the behavior the development-run-1 failure lacked. But the question's second part — partial shipments from the factory plus mechanic overtime, present in all three passages — is **not answered**, because the extract step never selected those sentences.
- *Automatic check:* "1 sentence without a citation" refers to "The sources disagree on the initial increase in lead times." — a statement about the sources rather than a factual claim, so this flag is a false positive; the numeric citations all check out.
- *Compared with development run 2* (same question, full answer): after I added document names to the retrieval index the passage order changed (Amazon first instead of Tanium), and at temperature 0 Gemma's extraction changed with it. The small model's evidence selection is sensitive to passage order — the same limitation as test 2.

_Official offline run (Wi-Fi off, model server restarted from local weights). Transcript: `../terminal-transcript.txt`._
