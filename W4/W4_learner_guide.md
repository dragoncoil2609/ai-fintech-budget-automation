# Week 4 — Building AI Systems: From Retrieval to Reasoning

## What You Will Learn This Week

This week you build a product — an AI system that answers questions about a real company's data. The questions get progressively harder: from "find a fact in a document" to "query live data and do math" to "remember what we talked about."

By Friday, your group must have a working system that answers questions live. **The target: L1-L3 working reliably = 90% of your grade.**

This week you combine multiple services into one complete system — S3 for documents, Bedrock KB for RAG, DynamoDB or RDS for structured data, Lambda for tool functions, and Bedrock as the reasoning brain.

---

## Key Knowledge Areas

This week on AI/ML, you will learn about:

- AI fundamentals: traditional programming vs machine learning, how models learn from data (training, weights, backpropagation, overfitting)
- The AI/ML landscape: supervised / unsupervised / reinforcement learning, deep learning architectures (CNN, RNN, Transformer, GAN), the road from classical ML to GenAI
- How LLMs work: tokenization, embedding, attention mechanism, context window, temperature
- Core limitations of LLMs and patterns that address them
- Evaluation & trust: how to assess AI output quality
- AI safety & responsible AI

### Key AWS Services This Week

| Service | Role in project |
|---------|----------------|
| **Amazon S3** | Store 36 knowledge base documents — data source for RAG |
| **Bedrock Knowledge Bases** | RAG pipeline: S3 → chunking → embeddings → vector search → retrieval |
| **Amazon Bedrock (Claude)** | LLM that generates answers from context + tool results |
| **Bedrock Agents** | (Optional) Managed tool use — agent decides when to retrieve vs call tools |
| **OpenSearch Serverless** | Vector store behind Bedrock KB — stores embeddings, performs similarity search. Not used directly but is the engine behind every retrieve call |
| **DynamoDB** | Store conversation state for L4 (memory) |
| **Database (RDS/Aurora/SQLite/DynamoDB)** | Store structured data (costs, incidents, SLA targets) for L3 tool queries |
| **Lambda** | Run tool functions when using Bedrock Agents — glue between LLM and data |

---

## The Big Picture

Your system has three data sources. Understanding what is WHERE determines everything:

| Data source | What's in it | How to access it | Used by |
|-------------|-------------|-----------------|---------|
| **Knowledge base** (36 markdown docs) | Company info, team structure, policies, postmortems, architecture docs | RAG retrieval (vector search) | L1, L2 |
| **Database** (4 CSV files, seeded) | Exact costs, incident records, SLA targets, daily metrics | SQL queries via tool functions | L3 |
| **Monitoring API** (Python script, run locally) | Current live status, latency, error rate, request volume | HTTP calls via tool functions | L3 |

**Key insight:** The knowledge base has ZERO dollar amounts, ZERO daily metrics, and ZERO current system state. If a question asks for numbers or live data, documents cannot answer it. Only tools can.

---

## Your Schedule

| Day | What to do | Target by end of day |
|-----|-----------|---------------------|
| **Tuesday** | Read all 36 docs. Start monitoring API. Seed database. Map what data is where. | Know the data cold. Architecture sketched. |
| **Thursday 08:30-10:00** | GenAI in practice | Understand the theory |
| **Thursday 13:00-14:30** | Build L1: upload docs to S3, create Bedrock KB, test retrieval | **L1 working** |
| **Thursday 14:30-16:00** | Build L2: improve prompts, increase K, handle conflicts | **L2 working** |
| **Thursday 16:00-17:00** | Build L3: seed DB, start API, build 2 tool functions, register with LLM | **First tool call working** |
| **Friday 08:00-10:00** | Polish L3, test all questions. Add L4 memory if time allows. | **L3 reliable** |
| **Friday 10:00-12:00** | Write Evidence Pack, capture screenshots, prepare slides | **Evidence Pack committed** |
| **Friday 14:00-18:00** | Present | |

---

## Tuesday: Explore the Data (Before You Write Any Code)

This is the most important preparation day. Groups that skip this and jump into coding build the wrong thing.

### Step 1: Read the knowledge base documents (1 hour)

All 36 documents are in `knowledge_base/`. Read every one. As you read, note:

- **Which documents cover the same topic?** (e.g., multiple team docs, multiple postmortems)
- **Where do documents conflict?** There are TWO API reference docs with different rate limits — one is archived (500 req/min), one is current (1000 req/min). Your system must handle this.
- **What information is qualitative only?** Docs mention "costs are rising" but never say the exact dollar amount. That's intentional — exact numbers are in the CSV only.

### Step 2: Start the monitoring API (15 min)

```bash
cd data_package/scripts
uv sync
uv run uvicorn monitoring_api:app --port 8000
```

Then hit every endpoint:
```bash
curl http://localhost:8000/services
curl http://localhost:8000/status/PaymentGW
curl http://localhost:8000/status/NotificationSvc    # <-- this one is degraded!
curl http://localhost:8000/metrics/PaymentGW
curl http://localhost:8000/metrics/NotificationSvc
curl http://localhost:8000/incidents
curl http://localhost:8000/incidents/PaymentGW
```

**Write down:** What data is ONLY available from the API? (Answer: current status, current latency/error/requests, active alerts. No document contains this.)

### Step 3: Seed the database (15 min)

```bash
cd data_package/scripts
uv run python seed_data.py --db-type sqlite
```

Then query it:
```sql
-- Total cost for PaymentGW in Q1 2026
SELECT SUM(total_cost) FROM monthly_costs 
WHERE service = 'PaymentGW' AND month IN ('2026-01', '2026-02', '2026-03');
-- Answer: 16500

-- Highest cost service in March 2026
SELECT service, total_cost FROM monthly_costs 
WHERE month = '2026-03' ORDER BY total_cost DESC LIMIT 1;
-- Answer: PaymentGW, 7500

-- SLA target for NotificationSvc latency
SELECT * FROM sla_targets WHERE service = 'NotificationSvc';
-- Answer: latency_p99_ms target = 2000
```

**Write down:** What questions can the database answer that no document can? (Answer: exact costs, exact SLA target numbers, daily metric history.)

### Step 4: Draw your architecture (30 min)

On a whiteboard or paper, sketch:
- Where do documents go? (S3 → Bedrock KB or custom index)
- Where does the LLM sit? (Bedrock API call)
- How do tool calls work? (LLM requests → your code executes → result back to LLM)
- Where does conversation state go? (DynamoDB, local dict, or file)

**Agree as a team before writing code.**

---

## Thursday: Build L1 → L2 → L3

### L1 — Simple RAG

**What you're building:** A system that takes a question, searches your knowledge base, and returns an answer with source citation.

**Recommended approach (fastest path):**

1. **Upload docs to S3:**
   - Create an S3 bucket (e.g., `geekbrain-kb-{your-group}`)
   - Upload all 36 markdown files from `knowledge_base/`

2. **Create a Bedrock Knowledge Base:**
   - In Bedrock console → Knowledge Bases → Create
   - Data source: your S3 bucket
   - Embedding model: Amazon Titan Embeddings v2
   - Vector store: OpenSearch Serverless (auto-created)
   - Sync the knowledge base — wait for sync to complete

3. **Test retrieval:**
   - Use the `Retrieve` API to search for "Team Platform lead"
   - You should get chunks from `team_platform.md` mentioning Alex Chen
   - If you get irrelevant chunks, your sync may have failed or your chunking is too coarse

4. **Connect to LLM:**
   - Call Claude Sonnet via Bedrock with this pattern:
     ```
     System prompt: "Answer the question using only the provided context. 
     Always cite the source document name. If the context does not contain 
     the answer, say 'I don't have enough information to answer this.'"
     
     User message: [retrieved chunks] + [user question]
     ```

5. **Verify with test questions:**
   - "Who is the Team Platform lead?" → "Alex Chen" (from team_platform.md)
   - "What is the deployment freeze window?" → "Friday 18:00 to Monday 08:00" (from deployment_policy.md)
   - "What authentication method does PaymentGW use?" → "API key + HMAC-SHA256" (from api_reference_v2.md)

**If all three return correct answers with source citations, L1 is done. Move to L2.**

### L2 — Advanced RAG

**What changes from L1:** Your system now handles questions that span multiple documents or have version conflicts.

**Changes to make:**

1. **Increase retrieval K** — retrieve 8-10 chunks instead of 3-5. Multi-doc questions need chunks from different documents.

2. **Improve your system prompt:**
   ```
   Add to system prompt:
   "When answering, consider ALL retrieved documents. If two documents 
   provide different information about the same topic:
   - Check if one is marked as 'archived' or 'superseded' — prefer the current version
   - Check document dates — prefer the most recent
   - If you cannot determine which is correct, state both values and explain the discrepancy"
   ```

3. **Test with conflict and synthesis questions:**
   - "What is PaymentGW's API rate limit?" → Should say 1000 (v2), acknowledging v1 said 500
   - "Can Team Commerce deploy a fix on Friday night for a P1 bug?" → Should combine deployment_policy.md (freeze) + incident_response_policy.md (P1 override) + team info (VP Mark Sullivan approval)
   - "What lessons were common across March 2026 incidents?" → Should synthesize two postmortems

**If your system resolves the rate limit conflict correctly, L2 is working.**

### L3 — Tool-Augmented RAG

**What changes from L2:** Your system can now call external tools to get data that is NOT in any document.

**This is the biggest jump. Take it step by step.**

#### Step 1: Make sure your data layer works

Before touching the LLM, verify:
- Database is seeded: `SELECT COUNT(*) FROM monthly_costs;` → 36 rows
- Monitoring API is running: `curl http://localhost:8000/metrics/PaymentGW` → JSON with latency data

#### Step 2: Build two tool functions

You need at minimum:

**Tool 1 — Database Query:**
```python
def query_database(sql: str) -> list[dict]:
    """Execute a read-only SQL query against the GeekBrain database.
    Contains: monthly_costs, incidents, sla_targets, daily_metrics tables.
    Use for historical data: costs, past incidents, SLA target numbers, daily metrics.
    Do NOT use for current/live system state — use Service Metrics for that."""
    # Execute sql against your sqlite/postgres connection
    # Return results as list of dicts
```

**Tool 2 — Service Metrics:**
```python
def get_service_metrics(service_name: str) -> dict:
    """Get CURRENT live performance metrics for a specific GeekBrain service.
    Returns: p50/p95/p99 latency in ms, error_rate_percent, requests_per_minute.
    Use for current/live data. For historical data, use Database Query."""
    # Call GET http://localhost:8000/metrics/{service_name}
    # Return the JSON response
```

#### Step 3: Register tools with your LLM

How you do this depends on your approach:

**If using Bedrock Agents:** Create Action Groups with Lambda functions wrapping your tools.

**If using a framework (LangChain, LlamaIndex):** Define tools using the framework's tool abstraction.

**If using raw API (recommended for understanding):** Pass tool definitions in the LLM API request:
```json
{
  "tools": [
    {
      "name": "query_database",
      "description": "Execute a read-only SQL query against the GeekBrain database...",
      "input_schema": { "type": "object", "properties": { "sql": { "type": "string" } } }
    },
    {
      "name": "get_service_metrics", 
      "description": "Get CURRENT live metrics for a GeekBrain service...",
      "input_schema": { "type": "object", "properties": { "service_name": { "type": "string" } } }
    }
  ]
}
```

#### Step 4: Handle the tool call loop

When the LLM decides to call a tool, it returns a `tool_use` response instead of text. Your code must:
1. Parse the tool call (which tool, what parameters)
2. Execute the tool function
3. Send the result back to the LLM
4. Let the LLM generate the final answer using the tool result

#### Step 5: Test with L3 questions

- "What was PaymentGW's total infrastructure cost in Q1 2026?" → Should call `query_database` → $16,500
- "What is PaymentGW's current p99 latency?" → Should call `get_service_metrics` → ~185ms
- "Is NotificationSvc meeting its SLA targets?" → Should call BOTH tools → latency 3200ms vs target 2000ms, error 2.1% vs target 1.0% → No, both breaching

**If your system returns $16,500 for the cost question (from a real DB query, not a guess), L3 is working.**

---

## Friday Morning: Polish + Evidence Pack

### Add L4 Memory

L4 is a **context engineering** problem. Without memory, the LLM treats every question independently. "Why did its costs spike?" means nothing if the system doesn't know "its" = PaymentGW from the previous turn.

**The concept:** Everything the LLM receives competes for space in its context window — system prompt, retrieved chunks, tool results, and conversation history. Memory is about deciding what history to include so the LLM can resolve pronouns ("it", "their", "that service") without flooding the context.

**Pick a memory strategy:**

| Strategy | What to do | Best for |
|----------|-----------|----------|
| **Buffer** | Store all turns, send everything | Simple demo (<10 turns) |
| **Window** | Store all turns, send only last 5 | Bounded context, predictable |
| **Query rewriting** | Before retrieval, rewrite "What incidents did it have?" → "What incidents did FraudDetector have?" using the LLM + history | Better retrieval on follow-ups |

**The simplest implementation (buffer, in-memory):**
```python
conversation_history = []

def chat(user_message):
    conversation_history.append({"role": "user", "content": user_message})
    
    # Include last 5 exchanges in the LLM call
    recent = conversation_history[-10:]
    
    response = call_llm(
        system_prompt=your_system_prompt,
        messages=recent + [{"role": "user", "content": user_message}],
        tools=your_tools
    )
    
    conversation_history.append({"role": "assistant", "content": response})
    return response
```

**For better retrieval on follow-ups, add query rewriting:**
```python
def rewrite_query(user_message, recent_history):
    rewrite_prompt = """Given this conversation history, rewrite the user's 
    latest question to be self-contained. Replace pronouns with specific 
    names/services. Output ONLY the rewritten question."""
    
    rewritten = call_llm(
        system_prompt=rewrite_prompt,
        messages=recent_history + [{"role": "user", "content": user_message}]
    )
    return rewritten  # "Why did its costs spike?" → "Why did PaymentGW's costs spike in March 2026?"
```

**Where to store state:** In-memory list is fine for a demo. Document in the Evidence Pack that production would use DynamoDB (PK=session_id, SK=turn_number) or Redis.

**Test with this conversation:**
- Turn 1: "Which service had the highest cost in March?" → DB query → "PaymentGW at $7,500"
- Turn 2: "Why did its costs spike?" → must resolve "its" = PaymentGW → retrieves postmortem
- Turn 3: "Which team is responsible?" → must know we're still talking about PaymentGW → "Team Platform, led by Alex Chen"
- Turn 4: "The postmortem mentioned a review deadline. Is it overdue?" → must retrieve April 15 deadline → compare to current date → "Yes, overdue"

**Why this works:** The LLM resolves pronouns naturally when it can see prior turns. Your job is just getting the right history into the context. Even a simple "include last 5 turns" dramatically improves multi-turn accuracy.

### Write the Evidence Pack

See the project announcement for the full Evidence Pack structure. Key: **capture screenshots as you test, not at the last minute.**

For each level, you need:
- Screenshot of a correct answer
- Screenshot or log proving the system actually did what it claims (tool call log for L3, conversation state for L4)
- 1-2 lines of notes

---

## How You Will Be Evaluated

### Grade out of 10

| Level | Points | What you need |
|-------|--------|--------------|
| L1 — Retrieval | 2.0 | Correct answers citing source documents |
| L2 — Multi-Source | 3.0 | Multi-doc synthesis, conflict resolution |
| L3 — Tools | 4.0 | Numerically correct answers from DB/API |
| L4 — Memory | 1.0 | Multi-turn conversation works |
| **Total** | **10.0** | |
| L5 — Bonus | +0.5 | Investigation with structured output |

**L1-L3 = 90% of your grade.** Focus here.

### Presentation breakdown

| Component | Weight |
|-----------|--------|
| Live Demo (L1-L4) | 50% |
| Individual QnA | 30% |
| Architecture & Evidence Pack | 20% |

---

## Common Mistakes (Avoid These)

1. **Building without reading the docs first.** You'll build conflict resolution for L2 without knowing which docs conflict. Read first.
2. **Jumping to L5 before L1 works.** If retrieval is broken, tools and agents are useless. L1 first.
3. **Not starting the monitoring API.** Groups that only build document retrieval fail L3 entirely. Start the API on Tuesday.
4. **Tool descriptions are too vague.** "Gets data" is useless. "Returns CURRENT live metrics; for HISTORICAL data use Database Query" — the LLM reads these to decide what to call.
5. **Not testing with actual numbers.** L3 is graded on numerical accuracy. If the answer should be $16,500 and your system says $15,000, that's wrong.
6. **No Evidence Pack screenshots.** Take screenshots as you build, not on Friday morning.
7. **In-memory conversation state only.** Fine for demo, but document the limitation in Evidence Pack.
