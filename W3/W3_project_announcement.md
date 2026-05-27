---
week: 3
title: "W3: The Database Backbone"
audience: students
release: "Monday 2026-04-20 morning"
deadline: "Friday 2026-04-24, group presentation"
---

# W3: The Database Backbone

> Apr 20-24, 2026

---

## The Challenge

W2 already had real deployment — S3 buckets locked down with IAM, EBS volumes attached to compute, your first real AWS infrastructure running. Nothing about that changes in W3. The 3-tier app keeps running where it is.

What changes this week is **what gets added and how you prove it works**. The services you layer on — RDS, DynamoDB, Bedrock, Lambda, CloudFormation — are deeper than S3 buckets. A misconfigured database can exist in the console but not be reachable from your app. A Lambda can be deployed but never actually invoked. A Bedrock Knowledge Base can sync but return garbage. "It was deployed" is not the same as "it works." So W3 shifts the grading discipline: the rubric weight moves from diagram (II: 50 → 20) to deployment-with-evidence (IV: 10 → 40), and every acceptance criterion this week must be backed by a screenshot + configuration note in a markdown Evidence Pack.

There are four things you must deliver by Friday plus the Evidence Pack. Not five suggestions — five requirements. Each one maps directly to what you are learning this week: databases on Monday and Tuesday, networking and Lambda on Wednesday. Build as you learn, document as you build.

---

## What Carries Forward from W2 (Mandatory)

Every week is a continuation, not a restart. Before you add W3 content, the following W2 outputs must still be in place — trainers will verify these on Friday alongside the new W3 must-haves:

- [ ] **S3 buckets from W2** remain with Block Public Access ON, default encryption enabled, and versioning turned on. The Bedrock Knowledge Base in MH2 must connect to one of these existing buckets — not a new one.
- [ ] **IAM baseline from W2**: MFA on root, an admin group, named IAM users (no console access via root). Any IAM feedback from W2 must be resolved — if you were flagged for wildcard policies, fix them before W3 is evaluated.
- [ ] **VPC diagram from W2** gets extended in MH4 — do not start a new VPC. Label the existing tiers and add the private database tier on top.
- [ ] **W2 trainer feedback cited in Part 1 recap** — name one specific item and show how W3 addresses it.

If any W2 item is missing or broken when Friday arrives, it counts against W3 Criterion II (AWS Architecture).

---

## What You Must Deliver (The Four Core Must-Haves)

These are your required deliverables for W3. All four must be demonstrable on Friday.

### 1. Database Layer — Pick the Right Database for YOUR Data

**The rule changed this week.** You do **not** need both RDS and DynamoDB — and you are **not limited** to them. Your job is to look at your own application's data, pick the engine + paradigm that fits, and prove the choice is correct with a scenario.

You can use any AWS-managed database (RDS, Aurora, DynamoDB, DocumentDB, Neptune) OR self-host an engine on EC2 (Postgres, MySQL, MongoDB, or similar) — as long as you document the trade-off. Monday and Tuesday still teach RDS and DynamoDB as the canonical relational and key-value paradigms; apply those paradigms to whichever engine fits your data.

Groups that pick one engine well will score higher than groups that deploy multiple but cannot justify either.

**Step 1 — Match your data pattern to a paradigm, then to an engine.**

There are four paradigms. Pick the one that fits your data, then pick an engine within it.

| Paradigm | What the data looks like | Example engines |
|----------|--------------------------|-----------------|
| **Relational** | Rows/columns, foreign keys, JOINs, ACID transactions | RDS (Postgres/MySQL/MariaDB/SQL Server), Aurora, self-hosted Postgres/MySQL on EC2 |
| **Key-Value** | Lookup by known key at huge scale, predictable access patterns, flexible per-item schema | DynamoDB |
| **Document** | Per-user/per-tenant fields that vary, nested documents, aggregation pipelines | DocumentDB, self-hosted MongoDB on EC2 |
| **Graph** | Relationships are the data — N-hop traversals, friend-of-friend, recommendation | Neptune |

| What your data looks like | Right paradigm | Example engine choice |
|---------------------------|----------------|-----------------------|
| Users → orders → items with foreign keys, you need JOINs | **Relational** | RDS Postgres, Aurora, self-hosted Postgres |
| Payments, inventory decrement, bank transfer (must be all-or-nothing) | **Relational** | RDS/Aurora (ACID transactions) |
| Complex ad-hoc queries, reports, BI-style aggregations | **Relational** | RDS/Aurora |
| Lookup by a known key at huge scale (session, device event, profile) | **Key-Value** | DynamoDB |
| >1,000 writes/sec sustained | **Key-Value** | DynamoDB |
| Flexible per-tenant schema, nested documents, aggregation pipelines | **Document** | DocumentDB, self-hosted MongoDB |
| N-hop relationship traversal (social graph, recommendations) | **Graph** | Neptune |
| Operational data + high-volume events in the SAME app | **Two paradigms** | Each engine does what it does best |

**Step 2 — Meet the checklist for YOUR engine + paradigm:**

Every chosen engine, regardless of paradigm, must satisfy:
- [ ] Deployed in a **private subnet** (no public internet access) — reachable only from your application tier via security group
- [ ] Encryption at rest enabled
- [ ] HA plan: **Multi-AZ enabled** (managed engines) OR **replica + snapshot plan documented** (self-hosted) OR **acknowledged single-point-of-failure** for this week with written reasoning (self-hosted only)
- [ ] At least one record written and read via your application or CLI — not just created in the console

Then add the paradigm-specific operations to prove your engine serves your access patterns. Your demo must show **2 representative operations**:

- **Relational (RDS / Aurora / self-hosted SQL):**
  - [ ] Schema has **at least 2 related tables with a foreign key**, demo shows **one JOIN query** returning real rows
  - [ ] **One indexed lookup** (named index supporting WHERE / JOIN)
  - [ ] Automated backups configured (managed: 7+ day retention; self-hosted: pg_dump / mysqldump cron or equivalent)

- **Key-Value (DynamoDB):**
  - [ ] Partition key is **high-cardinality** (user_id, order_id, device_id — NOT `status`, `active`, or any field with fewer than 20 distinct values)
  - [ ] Capacity mode is on-demand OR provisioned with **auto scaling enabled** (provisioned without auto-scaling = fail)
  - [ ] **One Query** by partition key + **one GSI query** (no Scans for frequent access patterns)

- **Document (DocumentDB / self-hosted MongoDB):**
  - [ ] **One aggregation pipeline** returning shaped/grouped results
  - [ ] **One indexed-field lookup** (named secondary index supporting the query)

- **Graph (Neptune):**
  - [ ] **One traversal query** (N-hop, e.g., friend-of-friend)
  - [ ] **One property / node lookup** by indexed attribute

Additional gates:
- [ ] **If self-hosted on EC2** (any engine): backup strategy (AMI snapshot, `pg_dump` cron, or acknowledged SPOF) + HA plan + trade-off reasoning documented in Evidence Pack section 2 Part B
- [ ] **If high-cost managed engine** (DocumentDB, Aurora, Neptune — minimum instance ~$200+/mo): rough monthly cost estimate in Part B. Do not pick a fancy engine for simple flat data when RDS or DynamoDB would fit

If you pick **more than one engine**, meet the checklist for each paradigm AND show in the Data Access Pattern Log which queries go to which engine and why. "Both" is not a cheat code — each one needs its own justification.

**Step 3 — Submit a Data Access Pattern Log (required, 1 page max).** Without this log, MH1 cannot score above 3 no matter how polished your deployment looks. Three parts:

- **Part A — 3 real access patterns from your own app.** One sentence each + rough frequency. Example: "Get all orders for a user, sorted by date — ~50 calls/min at peak."
- **Part B — For each pattern: engine + paradigm and why it is efficient.** Name the index (relational) or the partition key + sort key / GSI (key-value) or the aggregation / indexed field (document) or the traversal (graph) that serves the query without a full Scan. If self-hosted: include backup/HA plan + trade-off reasoning (why self-host vs managed). If high-cost managed: include rough monthly cost estimate.
- **Part C — The "wrong-paradigm" test.** Pick ONE pattern. In 2-3 sentences, explain what would break or cost too much if a paradigm from a DIFFERENT category served it. Example: "This 10k writes/sec session pattern on a relational engine would need sharding + a connection pool + a queue in front; a single table would grow unboundedly without partitioning." This part is how you prove you actually understand WHY your paradigm fits the data — not just that it works.

**Step 4 — Five worked examples (pick the one closest to your app):**

| App type | Data shape | Engine + paradigm | "Wrong-paradigm" test |
|----------|-----------|-------------------|-----------------------|
| **E-commerce** | Users, products, orders, order_items with FKs; placing an order = decrement inventory + insert order + insert items in ONE transaction | **RDS/Aurora (relational)** | Key-value would need TransactWriteItems across 3 items + a GSI for order history; schema changes require rewriting consuming code |
| **IoT telemetry** | 10k devices × 1 event/sec, queried as "events for device X in last hour" | **DynamoDB (key-value)** (PK=device_id, SK=timestamp) | Relational at 10k writes/sec needs sharding + connection pooling + a queue in front |
| **Multi-tenant SaaS** | Each tenant adds custom fields; nested config objects per tenant | **DocumentDB or self-hosted MongoDB (document)** | Relational would force rigid schemas to add columns for every tenant, or a sparse EAV table that kills query performance |
| **Social feed** | "Friends of friends who liked posts tagged X" — 3-4 hop traversal | **Neptune (graph)** | Relational `users JOIN edges JOIN edges JOIN edges` explodes — at depth 4 the query plan is intractable |
| **Cost-sensitive Postgres** | Small team, need specific Postgres extensions, managed RDS cost is prohibitive | **Self-hosted Postgres on EC2 (relational)** | Managed alternative would cost more or hide the protocol-level control we need (custom extensions, specific version); we accept the ops burden in exchange — backup via `pg_dump` cron + replica on 2nd EC2 |

Your Data Access Pattern Log should look like one of these five. You do not have to use one of them — but if your log is vaguer than these examples, it is not specific enough.

> **Where this lives:** The Data Access Pattern Log is section 2 of the **Evidence Pack** (see below — mandatory markdown file). It is NOT a standalone document.

### 2. AI/Bedrock Layer — Knowledge Base + Retrieval

Create a Bedrock Knowledge Base connected to your existing W2 S3 bucket. Ingest documents into it. Make a Retrieve or RetrieveAndGenerate call that returns a real result.

Acceptance criteria:
- [ ] Bedrock Knowledge Base created and connected to your W2 S3 bucket
- [ ] At least 3 documents ingested (sync job status: Complete)
- [ ] You can name the **embedding model** you chose (e.g., Amazon Titan Embeddings G1 - Text)
- [ ] You can name the **vector store** you selected (OpenSearch Serverless, Aurora PostgreSQL, or S3 Vectors)
- [ ] A Retrieve or RetrieveAndGenerate API call is demonstrated outside the Bedrock console — via Lambda, CLI, or your application code

The Bedrock Playground is for learning and experimentation. The deliverable is a real API call from your application flow.

### 3. Lambda Layer — Serverless Glue

Build at least one Lambda function that connects your application tier to the AI layer (Bedrock) or the database layer. This is the serverless glue between your components.

Acceptance criteria:
- [ ] Lambda execution role policy has **no `Action: "*"`** statement
- [ ] Lambda execution role policy has **no `Resource: "*"`** statement — permissions are scoped to specific resources
- [ ] At least one trigger is demonstrated live: an **S3 event trigger** (function fires on object upload) OR an **API Gateway integration** (HTTP call invokes the function)
- [ ] Function output is visible: CloudWatch log, a DynamoDB item written, or a Bedrock response returned

Least-privilege IAM is not optional here. A Lambda role with wildcards is a failing acceptance criterion.

### 4. VPC and Networking — Multi-Tier + Gateway Endpoint

Harden your W2 VPC into a proper multi-tier network. This is also where the W2 gap around S3 Gateway Endpoints gets fixed.

Acceptance criteria:
- [ ] VPC diagram shows **three labeled tiers**: public, private application, private database
- [ ] An **S3 Gateway Endpoint** is provisioned and explicitly labeled on your diagram (with its route table entry)
- [ ] Your database Security Group's inbound rule references the **application tier Security Group ID** — not the subnet CIDR block
- [ ] You can explain verbally: one scenario where you would use a NACL instead of a Security Group

If your W2 diagram did not have an S3 Gateway Endpoint, this is the week to add it. It is a Friday acceptance criterion.

### 5. Evidence Pack — The Artifact Your Grade Depends On

> **This is the single most important deliverable of the week.** Criterion IV (Deployment & Evidence) is 40% of your W3 score — up from 10% in W2 — and it is graded almost entirely against this file.

**What it is:** a single markdown file in your group repository at `docs/W3_evidence.md`. It is the source of truth. Your Friday slides are **derived from this markdown** — you copy the best 8-12 screenshots + captions into a slide deck, then present the deck on Friday. Do not write slides first and markdown after.

**Why markdown:** slides get lost, bullets get cut, screenshots get blurred when resized. A markdown file in the repo stays with the code, keeps full-resolution screenshots, and lets trainers re-verify claims after Friday. Groups that skip the markdown and rely on slides alone will cap IV at 3.

**Required structure (every group, every section — trainers check section-by-section):**

1. **Cover** — group number, member names, **database path chosen** (engine + paradigm — e.g., "RDS Postgres / relational", "DynamoDB / key-value", "DocumentDB / document", "self-hosted MongoDB on EC2 / document"), link back to your W2 evidence.
2. **Data Access Pattern Log** — Parts A, B, C (the log from must-have 1, embedded here). Part B must capture engine + paradigm + reasoning; for self-hosted, backup/HA plan + trade-off; for high-cost managed, monthly cost estimate.
3. **Deployment Evidence — one entry per acceptance criterion that applies to your chosen paradigm.** Each entry needs:
   - One screenshot (AWS console) OR CLI output (`aws rds describe-db-instances`, `aws dynamodb describe-table`, `aws docdb describe-db-clusters`, `aws neptune describe-db-clusters`, `aws ec2 describe-security-groups`, or engine-native commands for self-hosted)
   - 1-2 lines of notes: "We configured X this way because Y." Not "encryption enabled" — instead "encryption enabled with AWS-managed KMS key aws/rds. We picked AWS-managed over a customer CMK because we have no compliance mandate yet and we want rotation to be automatic."
4. **Working Query Evidence** — two representative operations matching your paradigm, each with a screenshot + real results returned:
   - Relational: one JOIN across 2 related tables + one indexed lookup
   - Key-Value: one Query by partition key + one GSI query (no Scans)
   - Document: one aggregation pipeline + one indexed-field lookup
   - Graph: one traversal (N-hop) + one property/node lookup
   - Multiple paradigms: one operation from each.
5. **Lambda + Bedrock Evidence** — CloudWatch Logs entry with timestamp after your Lambda trigger, Bedrock Retrieve/RetrieveAndGenerate response from your Lambda or CLI (not the Playground).
6. **VPC + Networking Evidence** — route table showing S3 Gateway Endpoint, DB Security Group inbound rule showing the app-tier SG as source.
7. **Negative Security Test** — screenshot of an unauthorized access attempt being denied.
8. **Bonus** (optional) — if you attempted a real-world ops scenario from the Bonus section below, document it here with pre/post screenshots, timings, and a reflection.

**How trainers grade IV against this file:**
- No Evidence Pack → IV cap at 2.
- Screenshots only, no notes → IV cap at 3.
- All acceptance criteria covered with screenshots + meaningful notes + working query evidence → IV 4.
- All of the above PLUS a working bonus scenario with measurements and reflection → IV 5.

Slides on Friday should link back to the markdown commit. "I'll show you the diagram" without a linked markdown file caps IV at 3 — the trainer needs to be able to verify your claims after you've left the room.

---

## Bonus — Real-World Ops Scenarios (Optional)

Finished all must-haves and the Evidence Pack? Go further. Bonus work earns up to **+0.5 on your W3 score** — and the point of this bonus is to experience what a database engineer actually does once the database is deployed: failovers, restores, migrations, engine swaps, upgrades. Pick one scenario from the menu below OR propose your own (check with a trainer first).

**Every bonus scenario must be documented in section 8 of your Evidence Pack:**
- Pre-state screenshot (what things looked like before)
- Action taken (console step, CLI command, or CFN change)
- Post-state screenshot (what things looked like after)
- Measurement (where applicable — downtime seconds, migration duration, row/item counts before vs after)
- 2-3 sentence reflection: what you learned, what surprised you, what you'd do differently.

### A. Ops Drill Scenarios (closest to real production work)

- **RDS Multi-AZ Failover Drill** — use `Reboot with failover` in the RDS console. Measure how long your app sees connection errors. Document the downtime.
- **Point-in-Time Restore** — restore your managed DB (RDS/Aurora/DynamoDB/DocumentDB) to a timestamp 5-10 minutes ago. Self-hosted equivalent: restore from an AMI snapshot + replay logs. Show the restored data.
- **On-Demand Backup → Restore** — take a manual snapshot (RDS) or on-demand backup (DynamoDB), restore into a new name, verify every row/item made it.
- **Read Replica Promotion** — create an RDS Read Replica, then promote it to standalone and show it accepting writes.
- **Engine Minor Version Upgrade** — upgrade your RDS/Aurora version (or change DynamoDB capacity mode) without losing data.
- **Zero-Downtime Schema Change** — add a column (RDS) or a GSI (DynamoDB) while writes are happening. Show no errors in app logs.

### B. Migration Scenarios (multi-hour effort, high learning value)

- **RDS MySQL → Aurora MySQL** — migrate via snapshot restore or Aurora read replica promotion. Show row counts match.
- **MongoDB → DocumentDB** — export a small MongoDB dataset (local Docker is fine), import into DocumentDB via DMS or mongodump/mongorestore. Show document counts match.
- **Oracle or SQL Server → PostgreSQL** — DMS + SCT for schema conversion. Show the SCT report and one test query working on both sides.
- **DynamoDB Table Redesign** — export an existing DynamoDB table to S3, re-import into a new table with a better partition key design. Show why the redesign matters.
- **DynamoDB ↔ DocumentDB** — genuine engine swap if your access pattern evolved. Requires a paragraph on why the engine change makes sense.

### C. Platform / Tooling Bonuses

- **Partial CloudFormation template** — Write a partial but syntactically valid CFN template provisioning at least one W3 resource of your choice (VPC, RDS DB instance, DynamoDB table, or Lambda function). Template must pass `aws cloudformation validate-template`. Document validate output + snippet + git commit in section 8 of your Evidence Pack. **+0.25**
- **Bedrock Agent with Action Groups** — agent that calls a Lambda action group to query your database in natural language.
- **DynamoDB Streams + Lambda fan-out** — preview of the W4 data pipeline pattern.
- **CI/CD pipeline** — CodePipeline or GitHub Actions that validates + deploys your CFN template on commit. **+0.5**
- **DAX caching** — DAX cluster in front of DynamoDB with latency comparison.
- **Niche database** — Neptune, Timestream, or ElastiCache for a real sub-use-case, with justification.
- **Full CloudFormation coverage** — all W3 infrastructure in one working CFN stack. **+0.5**

### Bonus Scoring

| Evidence quality | Credit |
|------------------|--------|
| Working scenario + pre/post screenshots + measurement + reflection | **+0.5** |
| Working scenario + screenshots but no measurement or reflection | **+0.25** |
| Attempted but not working, or no screenshots | **+0.0** |

Bonus is only scored if all four must-haves AND the Evidence Pack are complete. Multiple bonuses are allowed but total credit is capped at +0.5 — one scenario done well beats three done sloppily.

---

## What "Done" Looks Like on Friday

Before you present, **post your Evidence Pack commit link** (`docs/W3_evidence.md`) in the trainer WhatsApp channel. No link posted = Criterion IV pre-flagged at cap 2 before you even start.

Your group's Friday presentation covers four parts in 10-12 minutes total. **All slides are derived from your Evidence Pack markdown** — open the markdown once at the start and treat the slides as a reading order through it.

**Part 1 — W2 Recap (1.5 min):** Show your W2 diagram. Name one concrete lesson from last week's trainer feedback and show how W3 builds on it.

**Part 2 — W3 Architecture (3 min):** Walk through your updated diagram. Show all four must-have components. Walk your Data Access Pattern Log: your 3 access patterns, which engine serves each and why, and your "wrong-paradigm" test. (Slides for this part are derived from Evidence Pack sections 2 + 6.)

**Part 3 — Individual Q&A (3 min):** Two or three team members will be asked questions about your architecture and decisions. These are questions about what you built and why. If you understand your own work, you will handle them confidently.

**Part 4 — Live Demo (3-4 min):** Show the acceptance criteria live. If any live action breaks, the Evidence Pack screenshot of that same action is an acceptable substitute (no penalty) — but missing both live AND screenshot for a claim caps IV at 2. What to show:
- Data written to and read from your chosen engine, with the 2 representative operations matching your paradigm:
  - Relational: one JOIN across 2 related tables + one indexed lookup
  - Key-Value: one Query by partition key + one GSI query (no Scans)
  - Document: one aggregation pipeline + one indexed-field lookup
  - Graph: one traversal + one property/node lookup
  - backed by Evidence Pack section 4
- Bedrock Knowledge Base returning a retrieval result (not the Playground — a real API call) — backed by Evidence Pack section 5
- Lambda function triggered with output visible in CloudWatch Logs — backed by Evidence Pack section 5
- A negative test: an unauthorized access attempt to your database is denied — backed by Evidence Pack section 7

---

## Why This Week Matters

Every AWS architecture role asks about databases. Which service did you choose? Why? How did you design the data model? How did you secure it?

Every serverless interview asks about Lambda. What triggers your function? How did you scope the IAM role?

After this week, you will have real answers — built by your own hands, running on real AWS infrastructure, and documented thoroughly enough that a reviewer who was not in the room can still verify every claim.

W2 proved you can deploy AWS infrastructure. W3 proves you can deploy deeper services, configure them correctly, and show the evidence — the discipline you will need every week from here on.

---

## Getting Started on Monday

Before you provision anything, open your W2 diagram as a team and answer:

1. What data does your application need to store? List it: users, products, orders, events, whatever applies.
2. For each data type: are there relationships? What are the three most common queries? (These become Part A of your Data Access Pattern Log.)
3. Based on those answers: which paradigm (relational / key-value / document / graph), and then which engine within that paradigm (managed or self-hosted)? Pick the closest worked example above as your anchor.
4. Where in the VPC do they live? What Security Group rules do they need?

Agree on those four points before anyone starts provisioning. A database with the wrong data model costs more time to fix than it took to get wrong.

---

Good luck. By Friday, your application will have a backbone.
