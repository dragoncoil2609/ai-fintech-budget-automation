# Week 3 — Databases, AI Agents & Your Network: Building the Brain of Your App

## What You Will Learn This Week

Your W2 app has storage and identity. This week you give it a brain. You will add a proper database layer (choosing between SQL and NoSQL based on your data), connect Amazon Bedrock Knowledge Bases to make your app AI-powered, and build the network foundation that ties everything together securely. You will also write your first Lambda function and your first CloudFormation template — two skills that appear in every cloud engineering job description.

By Friday, your architecture will have an RDS database, a DynamoDB table, a Bedrock Knowledge Base connected to your S3 data, and a Lambda function that bridges your app tier to the AI layer. This is what a real production application looks like.

**Where the focus shifts from W2 — and what you must fix from W2:**

This week consolidates and deepens three areas your W2 app already touched: the database layer (proper engines — RDS + DynamoDB — instead of treating S3 as flat storage), the AI integration layer (Bedrock Knowledge Base wired to your S3 bucket, moving beyond one-shot prompts), and the serverless compute layer (Lambda as the glue between services). The whole week revolves around these three — not as brand-new concepts, but as the things you will harden into production-grade components.

W2 also left three common gaps that W3 diagrams must correct. Before you start deepening these three layers, fix these on your existing diagram:
- Missing encryption labels — your diagram must now show encryption at rest on RDS, DynamoDB, and any S3 buckets or EBS volumes that were unlabeled in W2
- Overly broad IAM policies — tighten any wildcard permissions on Lambda or EC2 roles to least-privilege, scoped to specific resource ARNs
- S3 traffic routed through the NAT Gateway — add a VPC Gateway Endpoint for S3 to your private subnet so that S3 calls stay on the AWS backbone and do not cost you per-GB NAT processing fees

These three fixes will be checked by trainers on Thursday and during Friday's QnA.

---

## Focus Areas

### Monday — Generative AI Foundations + Database Survey

**Courses this day** (from syllabus):
- Multi-Agent Collaboration with Amazon Bedrock Agents (1 hr, Digital Course) — Essential
- Build with Amazon S3 Vectors and Amazon Bedrock Knowledge Bases (1 hr, Digital Course) — Essential
- AWS SimuLearn: Explore the Amazon Bedrock Playgrounds (1 hr, Lab) — Recommended
- AWS Database Offerings (4 hrs, Digital Course) — Essential (focus on RDS, DynamoDB, ElastiCache; others are survey-level)

**Main topics**: Bedrock Agents (multi-agent patterns, action groups, knowledge bases) — S3 Vectors and RAG pipelines — AWS Database Offerings survey (RDS, DynamoDB, ElastiCache, Neptune, Timestream)

**What to pay attention to:**
- The anatomy of a Bedrock Agent. There are four moving parts: the Foundation Model (the brain), Instructions (what it should do), Action Groups (what it can do, backed by Lambda functions), and Knowledge Bases (what it knows, backed by your documents in S3). Draw this on paper before moving on.
- The difference between Retrieve and RetrieveAndGenerate. Retrieve gives you chunks of relevant text. RetrieveAndGenerate calls the FM and returns a synthesized answer. Most applications use RetrieveAndGenerate.
- The database type decision table. You do not need to memorize all eight database types — you need to know when RDS/Aurora (relational, joins, transactions) vs DynamoDB (scale, flexible schema, low-latency key lookups) vs ElastiCache (microsecond in-memory cache for hot data) vs DocumentDB (document store, aggregation pipelines) vs Neptune (graph traversals) is the right choice. That decision will come up in Friday's QnA.

**Project choice is open.** Monday teaches RDS as the canonical example of a relational engine, but your project database choice is open-ended. You may use any AWS-managed database (RDS, Aurora, DynamoDB, DocumentDB, Neptune) OR self-host an engine on EC2 (Postgres, MySQL, MongoDB, etc.) — as long as your choice matches your data's paradigm (relational, key-value, document, or graph) and you document the reasoning. RDS is not the only valid project choice; it is simply what Monday teaches.

**Hands-on tips:**
- In the Bedrock Playground SimuLearn, try the Chat Playground and test system prompts. Give the model a persona ("You are a cloud cost optimization advisor") and see how it changes responses. This is the closest thing to configuring a Bedrock Agent that the Playground supports.
- When going through the Database Offerings course, stop at each database type and ask yourself: "Where could this fit in our 3-tier project?" Don't just watch — annotate your notes.

---

### Tuesday — DynamoDB and RDS in Depth + VPC Architecture

**Courses this day** (from syllabus):
- Amazon DynamoDB Getting Started (1 hr, Digital Course) — Essential
- Amazon RDS Service Primer (20 min, Digital Course) — Essential
- AWS SimuLearn: Databases in Practice (1 hr, Lab) — Essential
- AWS SimuLearn: First NoSQL Database (1 hr, Lab) — Essential
- AWS Networking Basics (2 hrs, Digital Course) — Essential
- Subnets, Gateways, and Route Tables Explained (17 min, Digital Course) — Essential
- Understanding AWS Networking Gateways (30 min, Digital Course) — Essential
- Introduction to Amazon API Gateway (10 min, Digital Course) — Recommended (covered more deeply in W5)

**Main topics**: DynamoDB (partition keys, GSIs, Query vs Scan, DAX) — RDS (Multi-AZ, Read Replicas, RDS Proxy) — VPC subnets, route tables, Internet Gateway, NAT Gateway, Transit Gateway — API Gateway types and integration with Lambda

**What to pay attention to:**
- DynamoDB partition key design. The partition key is how DynamoDB decides which physical storage partition to place an item on. If too many items share the same partition key value, writes pile up on one partition and get throttled. Choose an attribute with many distinct values — user IDs, order IDs, session tokens are good choices. Status codes ("active"/"inactive") are bad choices.
- RDS Multi-AZ vs Read Replicas. These solve different problems. Multi-AZ provides high availability — a synchronous standby instance takes over automatically if the primary fails, but it cannot serve reads. Read Replicas are asynchronous copies that serve read traffic; they do not help with failover. You can use both together.
- VPC routing: a subnet is "public" if and only if its route table has a route sending 0.0.0.0/0 traffic to an Internet Gateway. A subnet is "private" if that route goes to a NAT Gateway instead. An "isolated" subnet has no internet route at all (right for your database tier).

**Project choice is open (continued).** Tuesday teaches DynamoDB as the canonical example of a key-value engine. You learn relational and key-value paradigms through RDS + DynamoDB on Monday/Tuesday — then apply the paradigm-thinking to your own engine choice. If your data fits a document or graph paradigm, DocumentDB or Neptune are valid project picks. If cost pressure drives you to self-host on EC2, that is also valid — with a documented backup + HA plan.

**Hands-on tips:**
- In the DynamoDB First NoSQL Database lab, after writing a few items, try running both a Query (requires partition key) and a Scan (reads everything). Notice the difference in "Items examined" — this is the cost driver.
- In the RDS Databases in Practice lab, check the Multi-AZ setting when you provision the instance. Toggle it on and see what changes. If the lab allows a simulated failover, trigger it and observe the endpoint behavior.

---

### Wednesday — VPC Labs, Security Groups vs NACLs, Lambda, CloudFormation

**Courses this day** (from syllabus):
- AWS SimuLearn: Networking Concepts (1 hr, Lab) — Essential
- Differences Between Security Groups and NACLs (10 min, Digital Course) — Essential
- AWS Lambda Foundations (2 hrs, Digital Course) — Essential
- Introduction to AWS Lambda (1 hr, Lab) — Essential
- Getting Started with AWS CloudFormation (1 hr, Digital Course) — Essential

**Main topics**: Multi-tier VPC lab (public/private/database tiers) — Security Groups vs NACLs — Lambda (execution model, S3 triggers, cold starts, CloudWatch Logs) — CloudFormation (template structure, intrinsic functions, change sets)

**What to pay attention to:**
- Security Groups vs NACLs. Security Groups are stateful — when traffic comes in, the return traffic is automatically allowed (the SG remembers the connection). NACLs are stateless — you must explicitly allow both inbound and outbound for every flow. Security Groups can only have Allow rules. NACLs can have both Allow and Deny. Security Groups apply to individual instances; NACLs apply to entire subnets.
- Lambda invocation types. S3 triggering Lambda is asynchronous — S3 fires the event and moves on, Lambda handles it in the background. If the function fails, Lambda retries automatically. API Gateway triggering Lambda is synchronous — the caller waits for the response. The invocation type determines retry behavior.
- CloudFormation intrinsic functions: `!Ref` returns the primary identifier of a resource (e.g., a bucket's name). `!GetAtt` returns a specific attribute (e.g., `!GetAtt MyBucket.Arn` returns the ARN). The mistake everyone makes is using `!Ref` and expecting an ARN.

**Hands-on tips:**
- In the networking VPC lab, after building your three-tier VPC, try sending a test request from the public subnet to the private app subnet. If it fails, check your security group rules — which tier is the source and which is the destination?
- **W2 fix to apply in this lab**: add a VPC Gateway Endpoint for S3 to your private subnet's route table. This routes S3 traffic directly over the AWS network instead of through the NAT Gateway. It costs nothing and removes a per-GB charge that most W2 architectures were silently accumulating.
- In the Lambda lab, after creating your function and setting up the S3 trigger, upload a test file to S3, then immediately go to CloudWatch Logs and find the log group for your function. Watching your own function respond to a real event is the moment Lambda "clicks."
- For CloudFormation: start simple. Create a YAML template with just one resource — an S3 bucket. Deploy it as a stack. Then add a second resource and update the stack using a change set first. Build confidence before adding complexity.

---

### Thursday — Review and Prep Day

Use Thursday to consolidate what you learned Monday through Wednesday.

**Morning**: Trainers will review the top misconceptions from this week's checkpoint games. Pay close attention if DynamoDB partition key design, the RDS Multi-AZ vs Read Replica distinction, or Lambda cold starts are discussed — these are the three most commonly misunderstood topics this week.

**Group activity**: Update your W2 architecture with the W3 database and AI layers. Work through these tasks in order:

**Step 0 — Fix W2 gaps first (do this before adding anything new):**
- Add encryption labels to any storage components that were missing them: S3 (SSE), EBS, and now RDS (storage encryption) and DynamoDB (SSE). Trainers will check for this.
- Tighten IAM policies: replace any wildcard permissions on Lambda or EC2 roles with least-privilege statements that name specific actions and specific resource ARNs.
- Add a VPC Gateway Endpoint for S3 to your private subnet route table (if it was missing in W2).

**Step 1 — Pick the right database for YOUR data and deploy it:**

The rule this week: the project database choice is **open**. Pick the engine + paradigm that matches your actual data pattern. Your options:

- **AWS-managed relational** — RDS (Postgres, MySQL, MariaDB, SQL Server), Aurora (Postgres/MySQL)
- **AWS-managed key-value** — DynamoDB
- **AWS-managed document** — DocumentDB (MongoDB-compatible)
- **AWS-managed graph** — Neptune
- **Self-hosted on EC2** — Postgres, MySQL, MongoDB, or similar, with a documented ops plan

A group that picks one engine well and justifies it scores higher than a group that bolts on two engines and justifies neither.

Use this decision shortcut (4 paradigms):
- Your data has relationships (users → orders → items) and needs JOINs, or you need all-or-nothing transactions (payments, inventory) → **relational paradigm** (RDS/Aurora, or self-hosted Postgres/MySQL).
- Your data is looked up by a known key at scale (session, event, device reading), OR you need >1,000 writes/sec with predictable single-key access → **key-value paradigm** (DynamoDB).
- Your data is semi-structured, nested documents (product catalog with variable attributes, user profiles with flexible fields, content CMS) and you query by aggregation pipelines / indexed fields → **document paradigm** (DocumentDB, or self-hosted MongoDB).
- Your data is heavily relationship-driven (social graph, recommendation network, fraud ring detection) and you traverse multiple hops → **graph paradigm** (Neptune).

Then deploy what you picked. Common rules for any engine: private subnet (not public), SG locked to app tier (no 0.0.0.0/0), encryption at rest, and an HA or backup plan.

- **If relational (RDS/Aurora):** private DB subnet, DB subnet group spanning 2 AZs, encryption at rest, automated backups 7+ days, SG inbound from app-tier SG. Schema has at least 2 related tables with a foreign key. Label engine + Multi-AZ decision.
- **If key-value (DynamoDB):** high-cardinality partition key (user_id, order_id, device_id — never `status` or `active`), on-demand OR provisioned-with-auto-scaling, encryption on, primary access pattern served by **Query** (not Scan). If you have a second access pattern, add a composite sort key or GSI.
- **If document (DocumentDB / self-hosted MongoDB):** private subnet, encryption at rest, at least one indexed field covering your primary lookup pattern (not a full-collection scan), replica set or Multi-AZ. **Cost note**: DocumentDB minimum instance is ~$200/mo — include a monthly cost estimate and confirm your budget. Self-hosted MongoDB: document your backup + replica strategy.
- **If graph (Neptune):** private subnet, encryption at rest, a clear node + edge schema (what is a vertex, what is a relationship), Multi-AZ or read replica. **Cost note**: Neptune minimum instance is ~$200/mo — include a monthly cost estimate.
- **If self-hosted on EC2:** private subnet, SG locked, EBS encryption on. You must document: (1) backup plan (snapshot cadence, restore-tested?), (2) HA plan (standby EC2 + replication? Multi-AZ snapshot? cold restore accepted?), (3) trade-off reasoning (why self-host vs managed — cost, specific engine version, license, etc.). Trainers need to see this earlier than the managed-service groups — loop in a trainer for an early review by Wednesday EOD.
- **If multiple engines:** meet the requirements for each engine and be ready to show which queries go to which paradigm. Picking multiple without data-pattern justification will score lower than one well-justified choice.

**Step 2 — Add the AI integration layer:**
- Add your Bedrock Knowledge Base connected to your W2 S3 bucket. Draw an arrow from your app tier through a Lambda function to the Knowledge Base to the FM.
- Label the Lambda function's IAM execution role and name the specific permissions it needs.

**Step 3 — Write a Data Access Pattern Log** (1 page max, slides are fine — required; without it MH1 cannot score above 3). Three parts:
- **Part A**: List the 3 most common access patterns in your app (one sentence each + rough frequency, e.g., "Get all orders for a user, sorted by date — ~50 calls/min at peak"). These are real queries from your W1/W2 user flow.
- **Part B**: For each pattern, name the engine + paradigm that serves it and the specific mechanism — index / partition key + sort key / GSI / aggregation pipeline with indexed field / graph traversal — that makes it efficient **without a full scan**. If you picked DocumentDB/Neptune/self-hosted, also include a 1-line cost estimate (~$/mo) or ops note (backup/HA plan). "Scan the whole thing" is never the right answer for a frequent query.
- **Part C — the "wrong-paradigm" test**: pick ONE pattern and explain in 2-3 sentences what would break or cost too much if a DIFFERENT paradigm served it. Examples: "A relational engine at 10k writes/sec needs sharding"; "A key-value store cannot answer this join without duplicating data into every item"; "Eventual consistency on a DDB GSI could show a stale balance"; "Forcing a graph query into a document paradigm requires N+1 lookups per hop"; "A document store with no indexed field on `user_id` scans the whole collection." This is how you prove you actually understood the choice — groups that skip Part C cap MH1 at 3.

Six worked examples you can anchor to (covering all 4 paradigms):
1. **E-commerce** (users/products/orders with FKs, "place an order = one transaction") → **relational** (RDS/Aurora SQL transaction all-or-nothing; a key-value store would need TransactWriteItems + GSI for order history).
2. **IoT telemetry** (10k devices × 1 event/sec, "events for device X in last hour") → **key-value** (DynamoDB PK=device_id, SK=timestamp; a relational engine at this write rate needs sharding + a queue).
3. **Chat/messaging** ("load last 50 messages in conversation X") → **key-value single-table** (DynamoDB PK=CONV#id, SK=MSG#timestamp; a relational engine works but the messages table grows into billions of rows and pagination becomes expensive).
4. **Banking ledger** ("transfer $100 from A to B, atomically or not at all") → **relational** ACID transaction (key-value eventual consistency could show a stale balance between debit and credit — not acceptable for money).
5. **Content CMS with flexible product attributes** ("get all products in category X with `discounted=true` and `region=APAC`") → **document** (DocumentDB with compound index on `category + flags`; forcing this into a relational schema means either sparse columns for every possible attribute or an EAV table, both of which become unwieldy).
6. **Social recommendation** ("find friends-of-friends of user X who liked product Y") → **graph** (Neptune 2-hop traversal; a relational engine needs recursive self-joins; a key-value store needs N+1 round trips per hop).

Your log does not need to copy one of these, but it should be at least as specific as they are — and it should name the paradigm explicitly, not just the engine.

Submit your updated diagram and Data Access Pattern Log to the trainer Slack channel before 17:00 Thursday.

---

### Friday — Show What You Know

Each group presents in four parts (~10-12 minutes total):

1. **Part 1 — W2 Recap & Reflection (~1.5 min)**: show your W2 diagram, name one specific piece of trainer feedback, and show concretely how W3 addresses it. Specificity scores higher than generality.
2. **Part 2 — W3 Architecture (~3 min)**: show your updated diagram. Must include: your chosen database engine(s) + paradigm placed correctly for the paradigm you picked — relational (RDS/Aurora/self-hosted) in a private DB subnet with Multi-AZ or equivalent HA labeled and 2 related tables + FK; OR key-value (DynamoDB) with high-cardinality partition key and sort key/GSI if needed; OR document (DocumentDB/self-hosted MongoDB) with indexed collection schema and replica/HA plan; OR graph (Neptune) with node + edge schema; OR multiple engines with a clear split. Self-hosted engines show the backup + HA plan on the diagram or adjacent slide. Walk your Data Access Pattern Log: 3 patterns, engine + paradigm + mechanism for each, and the wrong-paradigm test. Also show Bedrock Knowledge Base RAG flow and Lambda function with named execution role.
3. **Part 3 — Individual QnA (~3 min)**: 2-3 team members called by name. Every member can be picked — the entire team owns the design.
4. **Part 4 — Deployment / Live Demo (~3-4 min)**: show your chosen engine working live with one operation that actually exercises your paradigm:
   - **Relational** (RDS/Aurora/self-hosted Postgres/MySQL): run one JOIN query across 2 related tables, returning real rows.
   - **Key-value** (DynamoDB): run one Query call (not Scan) using your partition key and show items returned in <10ms.
   - **Document** (DocumentDB/self-hosted MongoDB): run one aggregation or `find()` against an indexed field (show `explain()` confirms the index is used, not a full COLLSCAN).
   - **Graph** (Neptune): run one traversal query (Gremlin/SPARQL) that walks at least one edge and returns vertices.

   Trigger the Lambda function via an S3 upload and show the CloudWatch Logs. Close with a negative security test (denied access attempt). If your group attempted the CloudFormation bonus, you may also show `aws cloudformation validate-template` output here. **Every slide in Part 4 is derived from your Evidence Pack markdown** — open the markdown file once at the start of Part 4 and link the slides to the latest commit so trainers can re-verify after the room clears. If a live action breaks during the demo, the Evidence Pack screenshot of that same action serves as substitute evidence (no penalty) — but missing both live AND screenshot = Criterion IV cap at 2.

Make sure the demo matches the diagram AND the Evidence Pack. Anything drawn on your architecture that is not deployed should be removed from the diagram before Friday. Anything in the Evidence Pack but missing from the diagram is equally a problem.

---

## This Week's Deliverables

Your group must deliver by Friday:

1. **Updated architecture diagram** — shows W3 additions: your chosen database engine(s) placed correctly for the paradigm you picked (relational in a private DB subnet with Multi-AZ decision labeled; key-value with partition key named and sort key/GSI if used; document with indexed collection + replica/HA plan; graph with node + edge schema; self-hosted engines with backup + HA plan annotated), Bedrock Knowledge Base + RAG flow drawn with Lambda as the connector, complete 3-tier VPC with VPC Gateway Endpoint for S3; plus W2 gap fixes: encryption at rest labeled on all storage, IAM policies tightened to least-privilege
2. **Evidence Pack — `docs/W3_evidence.md` in your group repo** (required, graded — this is the single most important deliverable of the week). A single markdown file that is the source of truth. Your Friday slides are **derived from this file** — copy 8-12 screenshots + captions from the markdown into slides, present the slides, and link back to the markdown commit. Do not write slides first and markdown after. Required sections: (1) Cover with group, members, engine + paradigm choice; (2) Data Access Pattern Log Parts A/B/C; (3) Deployment Evidence — one entry per acceptance criterion with console screenshot or CLI output PLUS 1-2 lines of notes ("we configured X this way because Y", not "encryption enabled"); (4) Working Query Evidence — one operation appropriate to your paradigm (relational JOIN / key-value Query / document aggregation with `explain()` showing index used / graph traversal); (5) Lambda + Bedrock Evidence (CloudWatch log + Bedrock API response from Lambda/CLI — not Playground); (6) VPC + Networking Evidence (route table showing S3 Gateway Endpoint + DB SG inbound rule); (7) Negative Security Test (denied access screenshot); (8) Bonus (optional — if you attempted the CloudFormation bonus, include `validate-template` output + intrinsic function snippet + git commit link here). Self-hosted and DocumentDB/Neptune groups must also include a cost-or-ops note (monthly estimate for managed premium engines; backup + HA plan for self-hosted).
3. **Live demo readiness** — your chosen engine working live with a paradigm-appropriate operation (relational: a JOIN across 2 related tables; key-value: a Query — not Scan — returning items via the partition key; document: an aggregation or `find()` hitting an indexed field; graph: a traversal walking at least one edge), Lambda function that produces CloudWatch Logs when triggered by an S3 upload. Each live action should have a corresponding screenshot in the Evidence Pack so trainers can re-verify after Friday.

---

## How You Will Be Evaluated

- **Rubric weights changed this week**: W2 Recap & Reflection (10%), AWS Architecture (20%), Individual QnA (30%), **Deployment & Evidence (40%)**. Diagram quality matters less than what is actually deployed and documented — Criterion IV is now the biggest slice of your score, and it is graded almost entirely against your Evidence Pack markdown.
- **How Criterion IV (40%) is graded**: No Evidence Pack → cap at 2. Screenshots only, no notes → cap at 3. All acceptance criteria covered with screenshots + meaningful notes + working query evidence → 4. All of the above PLUS a working bonus scenario with measurements and reflection → 5. Slides with no linked markdown commit also cap at 3 — the trainer needs a file they can re-verify after Friday.
- **W3-specific things that will be checked**: Did you fix the W2 encryption and IAM gaps? Did you pick the right paradigm for your data and prove it with a wrong-paradigm test? If relational: is it in a private subnet, 2 related tables with FK, Multi-AZ (or equivalent HA) decision stated? If key-value: is the partition key high-cardinality, does your primary access pattern use Query (not Scan)? If document: is the lookup field indexed (no COLLSCAN), is a replica/HA plan in place? If graph: is the node + edge schema documented? If self-hosted: is backup + HA documented and reviewed by a trainer by Wednesday EOD? Does your Lambda have a proper named execution role? Does every acceptance criterion have a screenshot + note in the Evidence Pack?
- **Individual QnA**: Your ability to explain database design decisions, Lambda invocation model, VPC structure, and the W2 gap corrections when called on — accuracy, reasoning, and confidence matter. Every team member can be picked — the whole team must own these decisions.
- **Daily checkpoints**: Kahoot, Blooket, and Quizlet Live games Monday through Wednesday count toward your score
- **Peer evaluation**: Your teammates evaluate your contribution each week

---

## Pro Tips

- **DynamoDB: think access patterns first.** Before choosing a partition key, list all the queries your application will run. The partition key should make the most frequent query a targeted `Query` operation rather than an expensive `Scan`.
- **Know the Multi-AZ vs Read Replica difference cold.** This distinction appears in almost every AWS interview. Multi-AZ = high availability (automatic failover, standby does not serve reads). Read Replica = read scaling (asynchronous copy, serves reads, can be promoted if needed).
- **Lambda and IAM roles go together.** Every Lambda function needs an IAM execution role. That role is what allows the function to call other AWS services. Never hard-code credentials — assign the role instead.
- **CloudFormation is the IaC tool you will use starting W5** for VPC peering and beyond. Practice this week by writing a partial template for one W3 resource — it is a +0.25 bonus if you include `validate-template` output + a snippet + commit link in Evidence Pack section 8. Learning the syntax now saves you time when it becomes required later.
- **RAG is not fine-tuning.** Your Bedrock Knowledge Base does not retrain the model. It attaches relevant text to the prompt at inference time. If the answers are poor, check your chunking strategy and your S3 data quality — not the model.

---

## Key AWS Services This Week

| Service | What it does | Why it matters for your project |
|---------|-------------|-------------------------------|
| Amazon Bedrock Agents | Orchestrates AI tasks using a Foundation Model, action groups, and knowledge bases | Powers AI-driven features in your app without building an ML pipeline |
| Bedrock Knowledge Bases | Manages a RAG pipeline: S3 data → embeddings → vector store → FM retrieval | Connects your app's data (S3 from W2) to an AI answer engine |
| Amazon RDS | Managed relational database (Postgres, MySQL, MariaDB, SQL Server) with Multi-AZ, Read Replicas, automated backups | **Relational paradigm** — structured data with joins + transactions (orders, users, transactions). Canonical Monday teaching example. Pick when data has clear relationships and you need ACID. |
| Amazon Aurora | Cloud-native MySQL/Postgres-compatible relational engine with auto-scaling storage, faster failover, and Aurora Serverless v2 | **Relational paradigm** — a drop-in upgrade from RDS when you need better performance or Aurora-specific features (fast failover, Global Database). Costs slightly more than RDS. |
| Amazon DynamoDB | Fully managed NoSQL key-value store with predictable single-digit millisecond performance | **Key-value paradigm** — high-velocity, flexible-schema data (sessions, events, app state). Canonical Tuesday teaching example. Pick when you look up by a known key at scale. |
| Amazon DocumentDB | MongoDB-compatible managed document store with replica sets across AZs | **Document paradigm** — nested JSON documents with flexible attributes, aggregation pipelines, indexed-field lookups. Pick over DynamoDB when your documents are deeply nested or you need MongoDB operators. Min instance ~$200/mo — include a cost estimate. |
| Amazon Neptune | Managed graph database (Gremlin, openCypher, SPARQL) | **Graph paradigm** — heavily relationship-driven data (social networks, fraud rings, recommendations) with multi-hop traversals. Min instance ~$200/mo — include a cost estimate. |
| Self-hosted DB on EC2 | Run Postgres, MySQL, MongoDB, or any engine yourself on an EC2 instance | Any paradigm — when cost/license/version constraints make managed services unsuitable. You own backup, HA, patching, upgrades. Document the ops plan and loop in a trainer by Wednesday EOD. |
| DynamoDB DAX | In-memory cache for DynamoDB, microsecond read latency | Optional: accelerates read-heavy DynamoDB workloads |
| ElastiCache for Redis | In-memory data store for session caching and real-time leaderboards | Optional: when you need sub-millisecond lookups from the app tier |
| Amazon VPC | Your private network in AWS with subnets, route tables, and gateways | Isolates your 3 tiers; databases must be in private subnets |
| AWS Lambda | Event-driven serverless compute triggered by S3, API Gateway, DynamoDB Streams | Connects your app tier to Bedrock, handles asynchronous data events |
| AWS CloudFormation | Infrastructure as Code — define all AWS resources in a YAML/JSON template | Deploy your entire stack reproducibly; no more manual console clicks |
| Amazon API Gateway | Managed API layer with throttling, auth, and integration with Lambda | Entry point for your app's REST API; connects frontend to backend Lambda |
