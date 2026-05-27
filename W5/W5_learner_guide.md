# Week 5 — The Network Fortress: Harden What You Built

## What You Will Learn This Week

By now your team has a working application — whatever stack you chose in W1-W4. W5 is the week you make it production-ready. That means making the network observable, enforcing security at the VPC boundary, giving your application tier shared storage that survives scaling, protecting every stateful resource you depend on with a verified backup, and putting a proper API surface in front of Lambda. These are the gaps between "it works in a demo" and "it works under real conditions." Every one of them maps directly to what cloud operations engineers do on day one of a job.

The application you have been evolving since W1 is the substrate. W5 adds a hardened shell around it. How your app is built internally — what stack, what AI integrations, what downstream services — remains your team's design. W5 prescribes the hardening, not the application.

---

## Focus Areas

### Monday — Networking Foundations + Network Security

**Courses this day:**
- Configuring and Deploying VPCs with Multiple Subnets (1h, Digital Course) — Essential
- Introduction to Amazon Virtual Private Cloud (VPC) (1h, Lab) — Essential
- AWS Network Connectivity Options (2h 30m, Digital Course) — Essential (VPC Peering and Transit Gateway sections); Self-study (Direct Connect section)
- AWS SimuLearn: Connecting VPCs (1h, Lab) — Essential
- AWS Network – Monitoring and Troubleshooting (1h, Digital Course) — Essential
- AWS Network Firewall Getting Started (1h, Digital Course) — Essential

**Main topics**: VPC subnet design, CIDR planning, VPC Peering vs Transit Gateway, Site-to-Site VPN, VPC Flow Logs, Reachability Analyzer, AWS Network Firewall stateful rules and IDS/IPS

**What to pay attention to:**

- The connectivity decision for MH1 comes down to two questions: "How many VPCs do I have?" and "Do I need transitive routing?" Two or three VPCs with non-overlapping CIDRs and no transitive routing needed → VPC Peering. Three or more VPCs, or you need hub-and-spoke, or you plan to add a VPN later → Transit Gateway. If you genuinely have one well-designed VPC, you can justify staying single-VPC — but that requires a written justification specific to your architecture, not a generic statement.

- VPC Peering is NOT transitive. If VPC A peers with VPC B, and VPC B peers with VPC C, VPC A cannot reach VPC C. Each connection must be direct. This surprises almost every student the first time.

- Network Firewall is the newest course in the entire W5 syllabus. Most students arrive Monday with zero prior exposure to it. Pay close attention and ask questions during the afternoon trainer Q&A buffer — your Monday checkpoint will include Network Firewall questions, and your Friday QnA likely will too. The key concept: Network Firewall intercepts traffic only if your route tables actually route traffic through the firewall endpoint. Without the route table change, the firewall is deployed but sees nothing.

- VPC Flow Logs are non-negotiable for MH1 — regardless of which connectivity path you take. Enable them on all VPCs and publish to CloudWatch Logs or S3. Sample log entries must appear in your Evidence Pack.

**Hands-on tips:**
- In the Connecting VPCs lab, after accepting a peering connection, immediately check the route tables on both sides — accepting the connection is not enough. Route tables on both VPCs must have entries pointing to the peering connection. Test connectivity with a curl or ping before calling it done.
- In the Network Firewall course, draw the route path on paper: private subnet → firewall subnet (firewall endpoint) → NAT Gateway → internet. If you skip drawing it, the route table configuration step will not make sense.

---

### Tuesday — File Storage & Backup

**Courses this day:**
- AWS File Storage Services Getting Started (2h, Digital Course) — Essential
- Amazon EFS Primer (30m, Digital Course) — Essential
- AWS SimuLearn: File Systems in the Cloud (1h, Lab) — Essential
- AWS Backup Getting Started (1h, Digital Course) — Essential

**Main topics**: S3 vs EFS vs FSx decision framework (Windows, Lustre, NetApp ONTAP, OpenZFS), EFS configuration (NFSv4, Standard vs One Zone, Elastic/Bursting/Provisioned throughput, lifecycle to IA), AWS Backup plans and vaults, Vault Lock, cross-region copy, restore testing

**What to pay attention to:**

- The file storage decision is not arbitrary — it depends on your OS and access pattern. EFS uses NFSv4 and works on Linux and macOS only. If your app tier is Windows, EFS will not mount. Use FSx for Windows File Server instead. For high-performance parallel workloads (HPC, ML training), FSx for Lustre is the right choice. Most groups in this program will use EFS.

- EFS encryption at rest can only be enabled when the file system is created — you cannot enable it retroactively. If your group created a test EFS without encryption, create a new one with encryption before Thursday.

- The restore test is the single most important step of MH3 and the one students skip most often. Creating a backup plan and seeing a recovery point in the vault is not enough. You must restore from a recovery point into a new resource, verify the restore job shows Completed, and verify that real data is readable from the restored resource. Start the restore job on Tuesday afternoon — restore jobs take time and you want Completed status before Thursday spot-checks.

**Hands-on tips:**
- In the File Systems lab, before running any mount command, check two things: (1) your instance is Linux, not Windows, and (2) the mount target's security group allows TCP port 2049 from your instance's security group. If either is wrong, the mount command will hang silently.
- For AWS Backup: after creating your backup plan and seeing "Completed" on the first backup job, immediately trigger a restore. Select the recovery point, choose a new destination resource (a new EFS file system, a new RDS instance), and start the restore job. Do not wait until Thursday.
- EFS lifecycle policy: set it to transition files to Infrequent Access (IA) after 30 days. This is a one-click setting in the EFS console and cuts storage costs for files that are rarely accessed after initial creation — without any code changes.

---

### Wednesday — Serverless & API Gateway

**Courses this day:**
- Introduction to Amazon API Gateway (1h, Lab) — Essential
- Architecting Serverless Applications (2h, Digital Course) — Essential
- Scaling Serverless Architectures (1h 30m, Digital Course) — Essential
- Serverless Analytics (25m, Digital Course) — Recommended

**Main topics**: API Gateway types (REST, HTTP, WebSocket), Lambda proxy integration, throttling and usage plans, authorizers, event-driven architecture patterns, choreography vs orchestration, cold starts, idempotency, reserved concurrency, provisioned concurrency, DLQ for async retry, S3-event-triggered analytics

**What to pay attention to:**

- REST API vs HTTP API: HTTP APIs are up to 71% cheaper and have lower latency. REST APIs support usage plans with API keys and per-method throttling, which most MH4 implementations will use. Either is acceptable for MH4 — but justify the choice in your Evidence Pack.

- The Lambda proxy integration response format matters for MH4: Lambda must return a JSON object with statusCode, headers, and body. If your Lambda returns anything else (a raw string, XML, an object without statusCode), API Gateway returns 502 to the client — not a Lambda error, a Gateway formatting error.

- Throttle and quota are independent settings on a usage plan. Throttle = requests per second (rate + burst). Quota = total requests per day or month. Running out of quota while the function is idle (zero Lambda invocations in CloudWatch) means the quota is exhausted at the API Gateway layer — the request never reaches Lambda.

- Reserved concurrency and provisioned concurrency are not the same thing. Reserved concurrency = a hard cap on concurrent invocations for one function (protect other functions from being starved). Provisioned concurrency = pre-initialized execution environments (eliminate cold starts). A function can have both. Reserved concurrency = 0 means the function cannot be invoked at all — even accidentally.

**Hands-on tips:**
- In the API Gateway lab, after deploying your REST or HTTP API, run two curl commands: one with the correct API key or authorization header (expect 200), and one without (expect 403). Screenshot both. These are your MH4 Evidence Pack screenshots.
- For MH5, pick the scaling pattern before Thursday: reserved concurrency (cap the function + show the CloudWatch Throttles metric), provisioned concurrency (compare Init Duration before and after in CloudWatch), async invocation + DLQ (trigger a failure and show the event landing in the DLQ), or S3-event-triggered analytics pipeline (PutObject → Lambda → DynamoDB or Athena, end-to-end). Apply it to a real existing function — not a new function created for the exercise.
- For the Serverless Analytics course (25m): if your team has a batch pipeline (Glue / Kinesis / etc.), this course shows you how to add a near-real-time layer with S3 events and Lambda — one of the four valid MH5 patterns. If your app doesn't have a batch pipeline, the same S3-event-Lambda pattern works as a standalone MH5 demo.

---

### Thursday — Review and Prep Day

Use Thursday to consolidate Mon-Wed learning and finalize your five must-haves before Friday.

**Morning**: Trainers will review the top misconceptions from checkpoint games. Pay close attention if these come up: VPC Peering non-transitive behavior, Network Firewall route table wiring, EFS Linux-only restriction, reserved vs provisioned concurrency, or the quota vs throttle distinction in API Gateway.

**Group activity — W5 Architecture Hardening:**

Work through your five must-haves in order:

1. **MH1**: Confirm your connectivity choice is documented with a rationale and Flow Logs are enabled on all VPCs. Show a sample log entry with ACCEPT or REJECT in your Evidence Pack.
2. **MH2**: Confirm your firewall path. If deploying Network Firewall, show the firewall endpoint in a dedicated subnet and the route table routing private subnet traffic through it before NAT Gateway. If taking the hardened SG+NACL path, show the explicit NACL DENY rule and the negative test screenshot. Note: if any EC2 or Lambda in your stack reaches the internet via NAT Gateway, you must take the Network Firewall path.
3. **MH3**: Confirm EFS or FSx is mounted on an app-tier instance in a private subnet and a meaningful file has been written and read. Confirm the backup plan covers the file system + your W3 database + your W2 EBS volumes. Confirm the restore test job shows Completed and data is readable from the restored resource.
4. **MH4**: Run the authenticated (200) and unauthenticated (403) API Gateway test and add both screenshots to your Evidence Pack. Confirm the old direct Lambda invocation path is replaced in your application code.
5. **MH5**: Confirm the scaling pattern is applied to a real existing function with CloudWatch evidence. Add the pattern rationale and evidence screenshots to your Evidence Pack.

Submit your updated architecture diagram and Evidence Pack link to the trainer Slack channel before 17:00 Thursday.

---

### Friday — Show What You Know

Each group presents in four parts (~10-12 minutes total):

1. **Part 1 — Application Recap & Reflection (~1.5 min)**: show your current application architecture diagram, name one specific piece of trainer feedback from a prior presentation, and show concretely how W5 addresses it. Also run 1-2 representative actions on the live deployment that prove your app works end-to-end (you choose what's most representative — a request through your API, a downstream call returning data, an admin operation, etc.). If your app isn't deployed or doesn't work end-to-end on Friday, that caps Criterion II at 3.

2. **Part 2 — W5 Architecture (~3 min)**: show your updated diagram with all five must-haves added. Walk through each: connectivity decision + Flow Log sample entry, firewall path with justification, EFS/FSx mount + backup plan + restore test result, API Gateway with throttling and auth, scaling pattern applied to a real function.

3. **Part 3 — Individual QnA (~3 min)**: 2-3 team members called by name. Every team member can be picked — the whole team owns these decisions.

4. **Part 4 — Deployment / Live Demo (~3-4 min)**: show a blocked request in the Alert Log or the NACL deny test, show a file written and read from the EFS/FSx mount, show the API Gateway 200/403 test, and show the scaling pattern evidence in CloudWatch. If a live action breaks, the Evidence Pack screenshot of that same action serves as substitute evidence — no penalty. Missing both live AND screenshot caps Criterion IV at 2.

Make sure your diagram matches what is deployed, and your Evidence Pack matches what you present. Before Friday, post your `docs/W5_evidence.md` commit link in the trainer Slack channel. Slides without a link to the Evidence Pack cap Criterion IV at 3.

---

## This Week's Deliverables

Your group must deliver by Friday:

1. **MH1 — Multi-VPC Connectivity**: documented connectivity decision (VPC Peering with route tables updated on both sides + connectivity test, Transit Gateway with attachments + TGW route table + connectivity test, or justified single-VPC with multi-AZ subnets + written rationale); VPC Flow Logs enabled on all VPCs with sample log entries in the Evidence Pack. Redeploy with the same VPC topology your team designed in prior weeks — same CIDR plan, same subnet tiers — and add the connectivity layer on top.

2. **MH2 — Network Firewall Hardening**: deploy AWS Network Firewall (dedicated firewall subnet, stateful rule group with domain allowlist or IPS rule, Alert Logs enabled, route tables updated, one blocked request visible in Alert Logs) OR implement hardened SG+NACL (written justification, no 0.0.0.0/0 on port 22/3389, explicit NACL DENY rule, negative test screenshot). If any Lambda or EC2 reaches the internet via NAT Gateway, the SG+NACL path is not available.

3. **MH3 — File Storage Layer + Backup Plan**: EFS or FSx mounted on at least one app-tier instance in a private subnet serving real application content, mount target SG restricted to app-tier SG only; AWS Backup plan covering the file system + your W3 database + your W2 EBS volumes, at least one completed recovery point in a vault, restore test completed with data verified readable from the restored resource.

4. **MH4 — API Gateway + Auth + Throttling**: at least one existing Lambda endpoint replaced by API Gateway (REST or HTTP API) with Lambda proxy integration, usage plan with rate and burst throttling, and authentication (API Key, Lambda Authorizer, or Cognito); authenticated request returns 200, unauthenticated request returns 403; old direct invocation path replaced in application code.

5. **MH5 — Serverless Scaling Pattern**: one real scaling pattern applied to an existing function — reserved concurrency (cap + throttle evidence in CloudWatch), provisioned concurrency (cold-start vs warm-start Init Duration comparison), async invocation + DLQ (failed event landing in DLQ demonstrated), or S3-event-triggered analytics pipeline (PutObject → Lambda → DynamoDB or Athena, end-to-end); applied to a real existing function, not a new test function.

6. **Evidence Pack** (`docs/W5_evidence.md`): nine sections — Cover, MH1, MH2, MH3, MH4, MH5, Application Carry-Forward Verification, Negative Security Test, Bonus (optional). Each section has screenshots with 1-2 line configuration notes. Your Friday slides are derived from this file — copy screenshots into slides, link back to the commit. W5 adds a hardened shell to your application — same architecture, same business domain as prior weeks, redeployed on the workshop account with the W5 additions.

---

## How You Will Be Evaluated

- **Group (Criterion II, 20%)**: Were all five must-haves correctly implemented and placed in the right architecture position? Can your team defend the choices (why Peering vs TGW, why Firewall vs SG+NACL, why EFS vs FSx, why the chosen scaling pattern)?
- **Individual QnA (Criterion III, 30%)**: Your ability to explain topology decisions, firewall rationale, and Lambda concurrency behavior when called on — accuracy, reasoning, and connection to your specific project. Every team member can be picked.
- **Deployment and Evidence (Criterion IV, 40%)**: This is the biggest slice. Graded against your Evidence Pack markdown, section by section. No Evidence Pack = cap at 2. Screenshots without configuration notes = cap at 3. All five MH sections with screenshots + notes + application carry-forward verification + negative test = 4. All of that plus restore test data integrity proof and concurrency metric evidence = 5. Slides must link to the Evidence Pack commit — no link = cap at 3.
- **Recap and Reflection (Criterion I, 10%)**: Did you cite specific feedback from a prior presentation and show how W5 responds to it? Did you run an end-to-end action proving your application works on the live deployment?
- **Daily checkpoints**: Kahoot games Monday through Wednesday count toward your score.
- **Peer evaluation**: Your teammates evaluate your contribution each week.

---

## Pro Tips

- **Start the restore test on Tuesday afternoon.** Restore jobs take time. If you wait until Thursday morning, the job may still be In Progress during spot-checks and you will not have the Completed screenshot for your Evidence Pack.
- **Draw the Network Firewall traffic path on paper before touching the console.** The route table configuration is the most commonly missed step. Traffic must route through the firewall endpoint in the firewall subnet before it reaches the NAT Gateway. If the route table sends traffic directly to NAT Gateway, the firewall sees nothing.
- **Run the API Gateway auth test early.** A 200 with an API key and a 403 without one takes 2 minutes to test and produces two of the most important Evidence Pack screenshots for MH4. Do it Wednesday after the lab, not Thursday night.
- **Apply MH5 to a function that already does real work.** The scaling pattern must be on an existing function in your application. If you create a new hello-world function for MH5, it does not qualify. Good candidates: the Lambda behind your MH4 API Gateway endpoint, an S3-event handler in your stack, or any function that does real backend work for your app.
- **EFS and Windows do not mix.** If any app-tier instance is Windows, use FSx for Windows File Server (SMB) instead of EFS (NFSv4). Mixing them silently fails and wastes debugging time.

---

## Key AWS Services This Week

| Service | What it does | Why it matters for your project |
|---------|-------------|-------------------------------|
| Amazon VPC | Your private network in AWS with subnets, route tables, and gateways | Every service in your architecture lives here; W5 makes the topology deliberate and observable |
| VPC Peering | Direct, private connection between two VPCs with non-overlapping CIDRs | One of two paths for MH1 multi-VPC connectivity — point-to-point, non-transitive |
| AWS Transit Gateway | Hub-and-spoke gateway connecting many VPCs through a central exchange | The other MH1 path — required when you have 3+ VPCs or need transitive routing |
| VPC Flow Logs | Capture IP traffic flow information for each ENI in your VPC | Non-negotiable for MH1: proves traffic is flowing (or blocked) on the expected paths |
| AWS Network Firewall | Managed stateful firewall and IDS/IPS at the VPC boundary (Suricata engine) | MH2 path A: intercepts and inspects traffic before NAT Gateway; Alert Logs prove enforcement |
| Amazon EFS | Elastic shared file system using NFSv4, mountable by multiple Linux EC2 instances simultaneously | MH3 file storage: replaces per-instance EBS for shared application content across the app tier |
| Amazon FSx | Family of managed file systems: Windows (SMB+AD), Lustre (HPC+S3), NetApp ONTAP (multi-protocol), OpenZFS | MH3 alternative to EFS when OS, protocol, or throughput requirements differ |
| AWS Backup | Centralized policy-driven backup service covering EFS, EBS, RDS, DynamoDB, EC2, S3 | MH3 backup plan: one plan covering all stateful resources since W2; Vault Lock prevents deletion |
| Amazon API Gateway | Managed API layer (REST, HTTP, WebSocket) with throttling, auth, and Lambda integration | MH4: replaces direct Lambda invocations with a proper API surface that enforces throttling and auth |
| AWS Lambda | Event-driven serverless compute, triggered by API Gateway, S3, and other sources | MH4 backend; MH5 scaling patterns applied to existing functions |
| Reachability Analyzer | Static configuration analysis tool to test connectivity between two resources without live packets | Troubleshooting tool: use when connectivity is broken and you need to find the blocking rule without guessing |
