---
week: 4
title: "W4: Build an AI That Actually Answers"
audience: students
release: "Monday 2026-05-03 morning"
deadline: "Friday 2026-05-08, group presentation"
---

# W4: Build an AI That Actually Answers

> May 3 — May 8, 2026

---

## The Challenge

You are building an AI system that answers questions about **GeekBrain** — a fintech startup running six production services. You will receive a data package: markdown documents about how the company operates, CSV files with cost and performance history, a seed script that loads the CSVs into your database, and a monitoring API that returns live system state.

**Your system must answer questions at four progressive levels.** Each level demands a capability the previous one did not. The levels are defined by what the questions require — not by what architecture to build.

**Your system must answer questions at four progressive levels.** We provide the data. You design the architecture.

---

## The Four Levels

Levels are cumulative. Each builds on the previous. You cannot skip levels — L3 requires a working L1-L2 foundation, and L4 requires working tools from L3.

You can build each layer yourself — handle retrieval, tool routing, orchestration, and memory using frameworks like LangChain, LlamaIndex, or raw API calls. Or you can use a managed service like **Amazon Bedrock AgentCore**, which handles orchestration, tool routing, KB sync, and session memory for you. Either way, you still write the tool functions, the agent instructions, and the knowledge base setup. The level requirements and pass conditions are the same regardless of approach.

---

### L1 — Retrieval (Simple RAG)

**What the questions demand:** A straightforward fact that lives in one document.

*Example: "What is GeekBrain's API rate limit for PaymentGW?"*

*Example: "Who is the Team Platform lead?"*

**Pass condition:** System returns the correct fact and names the source document.

**Architecture hint — pick one:**

| Approach | What it looks like | Pros / Cons |
|----------|-------------------|-------------|
| **Bedrock Knowledge Bases** | Upload docs to S3 → Create Bedrock KB → Call `RetrieveAndGenerate` API | Fastest to set up. AWS handles chunking, embedding, vector store. Less control over retrieval quality. |
| **Custom RAG pipeline** | Chunk docs yourself → Embed with Titan/OpenAI → Store in OpenSearch or ChromaDB/FAISS → Retrieve top-K → Send to LLM | Full control over chunking, embedding model, retrieval parameters. More setup time. |
| **Bedrock KB + custom prompt** | Use Bedrock KB `Retrieve` API (returns raw chunks) → Build your own prompt with the chunks → Call LLM | Best of both: managed retrieval + full prompt control. Recommended starting point. |

**Step-by-step to get L1 running:**

1. Upload the 36 knowledge base markdown files to an S3 bucket
2. Create a Bedrock Knowledge Base pointing to that S3 bucket
3. Choose an embedding model (Amazon Titan Embeddings v2 is the default)
4. Sync the knowledge base (wait for sync to complete)
5. Test with the `Retrieve` API — does it return the right chunks for a simple question?
6. Send the retrieved chunks + question to an LLM (Claude Sonnet via Bedrock) with a system prompt: "Answer the question using only the provided context. Cite the source document."
7. Verify: ask "Who is the Team Platform lead?" — answer should be "Alex Chen" from `team_platform.md`

**If L1 works, you have a foundation. Everything else builds on it.**

---

### L2 — Multi-Source Retrieval (Advanced RAG)

**What the questions demand:** Information that comes from two or more documents, or answers where two documents conflict and the system must resolve which one is correct.

*Example: "If Team Commerce has a P1 bug in OrderSvc on Friday night, can they deploy a fix? What approvals do they need?"*

*Example: "What is GeekBrain's API rate limit for PaymentGW?" (Two documents give different numbers — the system must resolve which is current.)*

**Pass condition:** System synthesizes across sources and resolves conflicts correctly.

**Architecture hint — improve your L1 pipeline:**

| Technique | What it does | When to use |
|-----------|-------------|-------------|
| **Increase top-K** | Retrieve more chunks (e.g., K=10 instead of K=3) | When answers span multiple documents |
| **Hybrid search** | Combine vector search (semantic) + keyword search (BM25) | When questions mention exact IDs, error codes, or names that vector search misses |
| **Metadata filtering** | Filter chunks by document date, version, status before ranking | When documents conflict (v1 vs v2, archived vs current) |
| **Improved system prompt** | Tell the LLM: "If sources conflict, prefer the most recent version. State the conflict." | Always — this is free and high-impact |

**Step-by-step to get L2 running:**

1. Start from your working L1 pipeline
2. Increase retrieval K from 3-5 to 8-10 chunks
3. Add to your system prompt: "When multiple documents provide different information, check their dates and version numbers. Prefer the most recent. If documents conflict, explain which you trust and why."
4. Test with the conflict question: "What is PaymentGW's API rate limit?" — system should retrieve both v1 (500) and v2 (1000) and correctly identify v2 as current
5. Test with the multi-doc question: "Can Team Commerce deploy on Friday night?" — system should combine deployment_policy.md + incident_response_policy.md + team info

---

### L3 — Retrieval + Tools (Tool-Augmented RAG)

**What the questions demand:** Answers that cannot be found in any document. Some questions need current system state from the monitoring API. Some need historical numbers from the database. Some need both.

*Example: "What was PaymentGW's total infrastructure cost in Q1/2026?"*

*Example: "Is PaymentGW's latency right now better or worse than its Q1 average?"*

**Pass condition:** System returns a numerically correct answer grounded in real data.

**Architecture hint — add tools to your L2 pipeline:**

| Approach | What it looks like | Pros / Cons |
|----------|-------------------|-------------|
| **Bedrock Agents** | Create an Agent with Action Groups (Lambda functions) + your KB. Agent decides per-query: retrieve from KB, call a tool, or both. | Managed orchestration. Agent handles routing. Less control over when tools are called. |
| **Framework tool integration** | Use LangChain or LlamaIndex to define tools. Framework handles the LLM ↔ tool call loop. | More control over routing. Familiar if you know the framework. |
| **Raw function calling** | Call LLM API directly with tool definitions in the request. Parse tool call responses in your code. Execute. Feed result back. | Full control. Most code to write. Best for understanding what's happening. |

**Step-by-step to get L3 running:**

1. **Set up the data layer first:**
   - Run `seed_data.py` to load CSVs into your database: `python seed_data.py`
   - Start `monitoring_api.py` locally (`uvicorn monitoring_api:app --port 8000`)
   - Test both: query your database, hit each API endpoint

2. **Build at least 2 tool functions:**
   - **Tool 1 — Database Query:** Takes a SQL query string, executes against the database, returns rows. This covers cost questions, incident queries, SLA lookups.
   - **Tool 2 — Service Metrics:** Calls `GET /metrics/{service_name}` on the monitoring API, returns current latency, error rate, requests/min.

3. **Register tools with your LLM:**
   - Write clear tool descriptions: what each tool returns, when to use it (current data vs historical data)
   - If using Bedrock Agents: create Action Groups with Lambda functions
   - If using framework/raw API: define tools in your code

4. **Test the routing:**
   - "What was PaymentGW's total cost in Q1 2026?" → system should call Database Query tool → return $16,500
   - "What is PaymentGW's current p99 latency?" → system should call Service Metrics tool → return ~185ms
   - "Is PaymentGW within its latency SLA?" → system should call BOTH (metrics for current, DB for target) → compare 185ms vs 200ms

5. **Verify the numbers are correct** — L3 is graded on numerical accuracy. Wrong numbers = no credit.

**Common L3 mistakes:**
- Tool descriptions are too vague → LLM calls the wrong tool
- Monitoring API not running → tool call fails silently → LLM hallucinates a number
- Database not seeded → query returns empty → LLM makes up data
- Not testing with actual L3 questions before Friday

---

### L4 — Retrieval + Tools + Memory (10% of grade)

**What the questions demand:** A multi-turn conversation where follow-up questions reference prior turns. The user never restates context.

*Example:*
- *Turn 1: "Which service had the highest infrastructure cost in March 2026?"*
- *Turn 2: "What was the main cause of the cost increase that month?"*
- *Turn 3: "Which team is responsible?"*
- *Turn 4: "The postmortem mentioned a review deadline. Is it overdue?"*

**Pass condition:** System correctly handles a 3-4 turn conversation. Follow-ups using "that service", "their team", "the same issue" are resolved without the user repeating themselves.

**Think about this:** Your L3 system treats every question independently. Ask it "Which service had the highest cost?" then ask "Why did its costs spike?" — it has no idea what "its" refers to. The second question arrives with zero context from the first.

Without memory, every question is independent. The LLM has no idea what "its costs" or "that service" refers to — because it never saw Turn 1's answer. L4 is about solving this: how do you carry context across turns so the conversation feels continuous?

This is a **context engineering** problem. Everything your LLM receives — system prompt, retrieved chunks, tool results, conversation history — competes for space in the context window. You must decide what to include and what to leave out. The question is: how do you make sure the LLM can still resolve "that service" or "their team" three turns later — without flooding the context and degrading answer quality?

---

### Bonus Opportunities (+1.0 max)

Bonuses are scored ONLY if L1-L3 are working. They do NOT count toward the base 10-point grade.

**Bonus A — Observability Dashboard (+0.5)**

Build a screen or UI that shows the system's internals as it processes a question: what was retrieved, which tool was called, what the LLM received, what it decided, what it returned. Think of it as a window into the pipeline — trainers can see the reasoning happen in real time, not just the final answer.

**Bonus B — Agent Reasoning (+0.5)**

Handle open-ended investigation questions that require multi-step reasoning.

*Example: "Is NotificationSvc in a healthy state? Assess its reliability and flag anything that needs attention."*

System must plan its approach, gather from multiple sources, and produce a structured report with visible reasoning steps.

**Bonus C — Knowledge Base Sync (+0.5)**

Documents change. A knowledge base synced once becomes stale. Build a mechanism to re-sync your Bedrock KB when documents are updated in S3 — automatic or manual, your choice.

*Example: S3 event → Lambda → `StartIngestionJob`. Or a Jupyter notebook that triggers sync on demand. Any working approach counts.*

**Maximum bonus: +1.0.** A or B = +0.5. C = +0.5. Final score capped at 11.0.

---

## What You Receive

1. **Knowledge base documents** — ~36 markdown files about GeekBrain: company overview, team structure, service architecture, deployment policies, incident postmortems, SLA policy, security policy, meeting notes, runbooks, and more. Read them carefully before you start building. Not all documents have the same format. Some conflict with each other.

2. **CSV files** — structured data with exact numbers:
   - `monthly_costs.csv` — per-service cost breakdown by month (Oct 2025 - Mar 2026)
   - `incidents.csv` — incident history with severity, duration, root cause, resolution
   - `sla_targets.csv` — SLA targets per service per metric
   - `daily_metrics.csv` — daily latency, error rate, and request volume (Jan - Mar 2026)

3. **Seed script** (`seed_data.py`) — loads the CSV files into SQLite (default) or PostgreSQL. Creates the tables automatically if they don't exist. Run the script once and your data is ready.

4. **Monitoring API** (`monitoring_api.py`) — a Python script you run locally. It returns live system state as JSON. Hit every endpoint before you start building — there is data available from the API that is not in any document.

5. **Tool list** — the tools your AI system needs to implement (see below).

---

## Tools Your System Needs

These are the tools your AI system must be able to call. You decide how to implement each one — what parameters it accepts, what it returns, how it connects to the data.

| Tool | What it does |
|------|-------------|
| **Service Status** | Get the current live status of a service |
| **Service Metrics** | Get current performance metrics for a service |
| **List Services** | List all available services in the system |
| **Incident History** | Get past incidents for a service |
| **Team Info** | Get details about a team |
| **Compare Services** | Compare a metric across multiple services |
| **Database Query** | Query structured data (costs, SLAs, daily metrics) |

These tools bridge the gap between what is in documents and what is not. L3 questions require tools.

---

## What You Must Deliver on Friday

### 1. Working System

A running AI system — local or cloud — that accepts questions and returns answers. It must be demoable live on Friday. No hardcoded responses. Trainers will ask questions your system has not seen before.

### 2. Slides

Your Friday slides are derived from your Evidence Pack (see below). Build the markdown first, then pull the key screenshots and decisions into slides.

### 3. Evidence Pack

> Trainers grade against this file after you leave the room. See the dedicated **Evidence Pack** section below.

---

## Evidence Pack

> **This is the most important deliverable of the week.** Your Friday slides are derived from this. Trainers re-verify your claims against this file after presentations.

**What it is:** a single markdown file at `docs/W4_evidence.md` in your group repository.

**Why markdown:** Slides get lost, bullets get cut, screenshots shrink. A markdown file in the repo stays with the code, keeps full-resolution screenshots, and lets trainers verify everything after Friday.

---

### Section 1 — Cover

- Group number
- Member names
- LLM used (e.g., Claude Sonnet via Bedrock)
- Framework used (e.g., LangChain / Bedrock Agents / raw API)
- Link to your repo

---

### Section 2 — Architecture Overview

- System architecture diagram (ASCII, Mermaid, or image)
- Component list: what each piece does
- Data flow: how a question travels from user input → retrieval/tool → LLM → final answer
- Screenshot of your system running (terminal showing the app started, or a URL if cloud-deployed)

---

### Section 3 — Decision Log

3 key decisions you made during the week. For each:
- What you chose
- What you learned from it

At least 1 thing that did not work and what you did instead. "We tried X, it failed because Y, so we switched to Z" is more valuable than "everything worked perfectly."

---

### Section 4 — Per-Level Evidence

**For each level, show two things:**

1. **The correct answer** — screenshot of your system's output
2. **Proof the question actually went through your system** — not just the final answer, but evidence that your pipeline processed it (retrieved chunks, called tools, hit Bedrock, etc.)

**How to provide proof:**
- If you built an observability dashboard (Bonus A) — screenshot it. That IS your proof.
- If not — show 1-2 terminal logs or CloudWatch logs showing the request flowing through your system: Bedrock API call, retrieved chunks, tool invocation and response. We need to see the LLM received real data, not that it guessed.

**You don't need many screenshots. 1-2 per level is enough.** Quality over quantity.

---

**L1 Evidence:**
- Screenshot: correct answer with source document cited
- Proof: log showing retrieval happened (Bedrock Retrieve call returning chunks, or your custom pipeline output)

**L2 Evidence:**
- Screenshot: correct multi-doc synthesis or conflict resolution (e.g., API rate limit → 1000, not 500)
- 1-2 lines: how your system handles conflicting documents

**L3 Evidence:**
- Screenshot: correct numerical answer (e.g., "PaymentGW Q1 cost = $16,500")
- Proof: log showing the tool was called and returned real data. **This is the most important proof in the entire Evidence Pack.** We need to see the tool call — not just the answer.

**L4 Evidence (if attempted):**
- Screenshot: a 3-4 turn conversation where follow-ups reference prior turns
- 1-2 lines: what memory strategy you used

**If you used AgentCore:**
- Architecture diagram: what AgentCore manages vs what you built
- Annotated trace logs for at least 2 questions (1 RAG-only, 1 tool-augmented) — explain what happened at each step

**Bonus A Evidence (Observability Dashboard):**
- Screenshot: the dashboard showing a question being processed — retrieval, tool calls, LLM decisions visible in real time

**Bonus B Evidence (Agent Reasoning):**
- Screenshot: structured investigation output with visible reasoning steps

---

### Section 5 — Reflection

Hardest level and why. What you would do differently with one more day.

---

### Evidence Pack Grading

| What you submit | Max evidence score |
|----------------|-------------------|
| No Evidence Pack | Capped at 2/5 |
| Screenshots of answers only — no logs, no proof of system processing | Capped at 3/5 |
| Screenshots + system proof (logs/dashboard) + notes + decision log | 4/5 |
| All of the above, clean and well-organized | 5/5 |

**Link discipline:** Slides on Friday must link to the Evidence Pack commit. Post the commit link in Slack before your slot. No link = evidence score capped at 3 before the demo starts.

---

## Scoring (out of 10)

### Base Score (10 points)

| Criterion | Points | What it measures |
|-----------|--------|-----------------|
| **L1 — Retrieval** | 2.0 | Correct single-doc answers with source citation |
| **L2 — Multi-Source Retrieval** | 3.0 | Multi-doc synthesis, conflict resolution |
| **L3 — Retrieval + Tools** | 4.0 | Numerically correct answers from tools/DB/API |
| **L4 — Memory** | 1.0 | Multi-turn conversation with pronoun resolution |
| **Total** | **10.0** | |

**L1-L3 account for 90% of your grade.** If your system handles L1-L3 reliably, you score 9/10 before L4.

### Bonus (+1.0 max)

| Bonus | Points |
|-------|--------|
| **Bonus A — Observability Dashboard** | +0.5 — UI showing pipeline internals: what was retrieved, which tool called, LLM input/output |
| **Bonus B — Agent Reasoning** | +0.5 — Multi-step investigation with structured output and visible reasoning |
| **Bonus C — Data Operations** | +0.5 — Auto-sync S3 → Bedrock KB + production mindset |

**Maximum possible score: 11.0.** Bonus A and B share +0.5; Bonus C is a separate +0.5. Bonus only scored if L1-L3 are working.

### How each level is scored (Likert 1-5)

| Score | Meaning |
|-------|---------|
| 1 | Not attempted or completely broken |
| 2 | Attempted but mostly incorrect — wrong answers, missing sources, wrong numbers |
| 3 | Partially working — some answers correct, some wrong. Tool calls happen but results are inconsistent |
| 4 | Working reliably — correct answers, source citations, accurate numbers. Minor edge case issues |
| 5 | Excellent — handles all test questions correctly, graceful error handling, clean output |

**Level score → point conversion:** `points = (score / 5) * max_points_for_level`

Example: L3 score of 4/5 → (4/5) * 4.0 = 3.2 points

### Presentation components

The 10-point grade comes from:

| Component | Weight | What trainers evaluate |
|-----------|--------|----------------------|
| Live Demo (L1-L4) | 50% | Does the system answer correctly at each level? |
| Individual QnA | 30% | Do you understand how your system works? |
| Architecture & Evidence Pack | 20% | Diagram, decision log, evidence quality |

---

## Rules

1. **Architecture is open.** Any approach, any framework, any LLM.
2. **LLM choice is open on AWS Bedrock.**
3. **No hardcoded answers.** Trainers ask questions outside the example set.
4. **Every team gets the same data package.**
5. **AI-assisted coding is allowed and expected.**

---

## Schedule

| Day | What happens |
|-----|-------------|
| **Tuesday** | Receive data package. Read all documents. Start the monitoring API and hit every endpoint. Run the seed script. Draw your architecture before writing code. |
| **Thursday 08:30-10:00** | Introduction: RAG systems, tools, memory, agent reasoning. |
| **Thursday 13:00-17:00** | Build. Get L1 working first. Do not start L3 until L1 is reliable. |
| **Friday 08:00-12:00** | Finalize system, write Evidence Pack, prepare slides. Post Evidence Pack commit link to Slack before your slot. |
| **Friday 14:00-18:00** | Presentations (~10-12 min per group). |

---

## Friday Presentation Format (~10-12 min)

**Before you present:** post your `docs/W4_evidence.md` commit link in the trainer Slack channel. No link = evidence score pre-flagged at cap 2.

**Part 1 — Architecture (3 min):** Walk through your system diagram. Name every component. Explain one key decision and one thing you changed during the week.

**Part 2 — Individual QnA (3 min):** 2-3 team members picked randomly and asked questions about how your system works.

**Part 3 — Live Demo (4-5 min):** Show your system answering questions at each attempted level.

If a live answer fails, the Evidence Pack screenshot for that level is an acceptable substitute — no penalty. Missing both live and screenshot for a level caps that level's score at 2.

**Part 4 — Lessons Learned (1 min):** Hardest level and why. What you would do differently.

---

## Getting Started — The Critical Path to L3

Follow this order. Do not skip ahead.

### Day 1 (Tuesday): Explore the data

1. Read every document in the knowledge base. Which ones cover the same topic? Where do they conflict? (You need this for L2.)
2. Start the monitoring API: `cd data_package/scripts && uv sync && uv run uvicorn monitoring_api:app --port 8000`
3. Hit every API endpoint manually. Write down what data is ONLY available from the API.
4. Run the seed script: `uv run python seed_data.py --db-type sqlite` — this loads the CSVs into your database.
5. Check your data: query the database — you should see PaymentGW at 7500 for March 2026.

### Day 2 (Thursday): Build L1 → L2 → L3

**Morning — L1 (target: working by 12:00):**
1. Upload knowledge base docs to S3
2. Create Bedrock KB, sync, verify
3. Test retrieval: does it return the right chunks?
4. Connect to LLM with system prompt
5. Verify: "Who leads Team Platform?" → "Alex Chen"

**Afternoon — L2 (target: working by 15:00):**
1. Increase retrieval K to 8-10
2. Improve system prompt for conflict resolution
3. Test: "What is the API rate limit?" → should resolve v1 vs v2

**Late afternoon — L3 (target: first tool call working by 17:00):**
1. Build Database Query tool function
2. Build Service Metrics tool function
3. Register tools with your LLM
4. Test: "What was PaymentGW's total cost in Q1?" → $16,500

### Day 3 (Friday morning): Polish + Evidence

1. Test all levels end-to-end
2. Add L4 memory if time allows (even simple last-5-turns window counts)
3. Write Evidence Pack with screenshots and logs
4. Prepare slides

---

Good luck. Build something that actually answers.
