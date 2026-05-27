# Week 6 — Make It Operational: Optimize, Govern, and Secure Your Architecture

## What You'll Learn This Week

This is the final hardening week before the W7 capstone. You take the application you built through W1-W5 and make it production-ready: auto-healing infrastructure, cost-optimized storage, real cost visibility with tagging and FinOps tools, and automated security enforcement that fixes misconfigurations without human intervention. The heavy emphasis this week is on **Cost and Optimization** — two of the four Must-Haves are dedicated to proving you not only know where your money goes, but that you actually did something about waste. Everything you build this week feeds directly into your W7 demo and your cloud operations interview story.

**What carries forward from W1-W5:** Your architecture diagram, your business domain, your design decisions, and your code repository. The workshop account is fresh — redeploy whatever you need for W6. You do not have to re-prove every prior-week feature; you have already done that. What trainer expects on Friday Part 1 is a short project recap: what the application is, its business domain, and the key design decisions you carried forward from W1-W5 — enough to set context for the W6 work. No live app action and no diagram update are required in Part 1. Then W6 grading focuses on the 4 Must-Haves below.

This week is organized around **4 Must-Haves (MHs)** — and two of them are about cost:
- **MH-COST-V** — Cost Visibility & Attribution (tagging strategy + cost allocation tags activated + a cost tool + baseline breakdown)
- **MH-COST-A** — Cost Control & Action (the Automated Cost Guard: a scheduled Lambda that actually stops untagged billable compute, plus Budgets → SNS → Lambda and a latency ADR)
- **MH-OBS** — Monitoring and Observability (CloudWatch dashboards, alarms, Log Insights)
- **MH-SEC** — Self-Healing Security Guard (a Lambda + EventBridge that detects one security misconfiguration and auto-fixes it, plus one supporting preventive control)

> **Optional bonus — Optimization Actions:** Want to go further? gp2→gp3 migration, config-based Trusted Advisor remediation (≥2 findings), an RI/SP break-even analysis, and a short "wasteful → changed" reflection are all worth bonus credit. They are no longer required Must-Haves — but they are exactly the kind of optimization story that strengthens your W7 demo and interview.

> **⚠️ HARD COST CAP — USD $150 for the week.** Your group's total AWS account spend for W6 must stay at or under $150. If your account total exceeds $150, the **entire W6 assignment fails** for your group — no exceptions, even if all four Must-Haves are done perfectly. Last week a group left resources idle and burned over a thousand dollars; that is why this cap exists now. A complete 3-tier workshop stack never needs anywhere near $150. Read the **W6 Cost Discipline Memo** (shared with the project announcement) before you deploy anything — it shows exactly how to stay under: Single-AZ, smallest instance that works, serverless where possible, shut down overnight, and no Bedrock Provisioned Throughput / OpenSearch multi-node / EKS. Staying ≤ $150 and proving you actively chose cheaper resources **is** part of MH-COST-V — it is not extra work on top of the assignment.

![Actual W5 AWS cost — a workshop-only account that burned over a thousand dollars on idle resources, which is why the $150 cap now exists](../assets/cost-w5.png)

---

## Focus Areas

### Monday — High Availability, Auto Scaling & Cost/Performance Optimization

**Main topics**: EC2 Auto Scaling Groups (ASG), ALB health checks, S3 storage class optimization, EBS cost and performance tuning, Cloud Economics

**Must-do hands-on**: Both SimuLearn labs (Auto-Healing and Highly Available Web Applications) and both EBS courses. For the EBS courses, apply the learning directly — look at your actual RDS and EC2 volume types and consider migrating from gp2 to gp3. This migration is **optional bonus** this week, not a required Must-Have: if you do it, document the volume ID, old type, new IOPS setting, new throughput setting, and the cost comparison for bonus credit.

**Must-know concepts (read + discuss)**: Cloud Economics SimuLearn — this is an analytical exercise, not a deploy-something lab. Work through the RI vs Savings Plans vs Spot analysis as a group; an RI/SP break-even decision rationale is **optional bonus** this week.

**What to pay attention to**:
- Set the ALB health check type to "ELB" on your ASG, not just "EC2." EC2 type only catches hypervisor failures. ELB type catches application-layer failures — if your app crashes but the VM is still running, only ELB health check replaces the instance.
- gp3 IOPS are configurable independently of volume size — a 100 GB gp3 volume gets 3,000 IOPS guaranteed and can be pushed to 10,000 IOPS by changing a setting, with no downtime. This is not how gp2 works (gp2 ties IOPS to volume size using a burst credit system). For almost every student workload, gp3 is the right choice.

**Hands-on tip**: After the EBS courses, check your actual RDS and EC2 volume types in the AWS console. If you want the bonus, migrate gp2 to gp3 and document: volume ID, old type, new IOPS setting, new throughput setting, cost comparison. Screenshot the before/after — capture the before state while still on gp2. This is your optional gp2→gp3 bonus evidence.

**Homework (Monday evening)**: Read "Optimize Your Cloud Governance: Balance Security and Cost" — focus on Module 3 (Config for Cost) and Module 4 (Tagging). These feed directly into your MH-COST-V deliverables. Module 2 (Organizations/SCPs/RCPs) is context reading — you will NOT be delivering SCP or Tag Policy JSON this week. Module 5 (Security-Cost Balance) helps you write the 1-2 sentence security-cost statement in your MH-SEC section. Tuesday morning there is a quick discussion: "What is one cost-vs-security trade-off your group is considering?"

---

### Tuesday — Cost Audit, Governance & Observability Foundations

**Main topics**: Automated Cost Guard (MH-COST-A — build it today), AWS Systems Manager (reinforcement), Amazon CloudWatch (MH-OBS foundation), cost-aware governance (tagging + FinOps tools), FinOps tooling, AWS Trusted Advisor (optional bonus)

**Must-do hands-on**:
- **Automated Cost Guard (MH-COST-A — required, build it today)**: Build the safety net that would have caught last week's runaway account. Wire an EventBridge Scheduler (or daily cron) → Lambda that finds and STOPS billable compute (EC2/RDS) not tagged `keep=true`. Give the Lambda a least-privilege role (only the EC2/RDS describe + stop actions it needs — no wildcards). Prove it actually turns something off: leave one untagged instance running, let the Lambda fire on its schedule, and capture the CloudTrail `StopInstances`/`StopDBInstance` event with before/after state. Then wire AWS Budgets (daily $150 threshold) → SNS → the same Lambda, and demonstrate that path with a test SNS publish. Write a short latency ADR: AWS cost data lags ~8-24h, so in a 48-hour account the real Budgets cost trigger likely won't fire — that is expected and not penalized; what IS penalized is a missing scheduled mechanism, no demonstrated stop, or a missing ADR. What gets you the score: a resource actually being turned off by your automation — not a notification.
- **CloudWatch (MH-OBS)**: Install the CloudWatch Agent, get a memory metric appearing in the `CWAgent` namespace, and start building your dashboard. Do this today — if you wait until Wednesday, you will have no historical memory data by Thursday walkabout.
- **CFM FinOps courses (MH-COST-V)**: Open Cost Explorer and filter by your CostCenter tag. Identify your top-3 cost drivers and note a baseline cost breakdown observation. Set a Budgets threshold alert. Keep all of this within the $150 cap.
- **Trusted Advisor (optional bonus)**: If you want the bonus, run all checks and remediate **at least 2 configuration-based findings** with before/after evidence (finding description + severity, the action you took, the after screenshot). Target config-based checks — these are the ones that actually fire in a short-lived account: unattached EBS volume, unassociated Elastic IP, missing S3 lifecycle rule, public S3 bucket, security group open to `0.0.0.0/0` on port 22/3389, EBS volume with no snapshot. Utilization-based checks (Low Utilization EC2, Idle RDS, Idle Load Balancer) need ~14 days of CloudWatch history and will NOT fire in this 48-hour account, so do not build bonus evidence around them. "We saw findings" is not enough — the action is what counts.

**SSM Lab — reinforcement (not a graded W6 deliverable)**: You have been using Session Manager and Parameter Store informally since W3-W5 redeployments. This lab deepens those skills (Run Command, Automation runbooks, Patch Manager). Continue applying Session Manager and Parameter Store as good ops hygiene on your redeployed stack — but no artefact is required from this lab for W6 scoring.

**Must-know concepts (read + checkpoint discussion)**: The governance course ("Optimize Your Cloud Governance") is this week's reading assignment — NOT a lab session. Your group uses it to produce your MH-COST-V deliverable:
- A **tagging strategy document** with at least 4 tag keys (Owner, Environment, CostCenter, Application) and agreed-upon values with consistent capitalization — THEN activate those tag keys as cost allocation tags in the Billing console (Settings > Cost allocation tags). Both steps are required for Cost Explorer to group by your tags.

(Optional bonus: a Config rule for cost compliance, e.g. "EBS volumes must be gp3" or "EC2 instance types must be in an approved list", is extra cost-governance credit — not required.)

The Tuesday afternoon checkpoint question is: "What is one cost-vs-security trade-off your group is making?" — bring a real observation from your architecture, not a textbook answer.

**What to pay attention to**:
- **The two-step tagging trap**: Tagging a resource is not enough. You must also activate the tag key as a cost allocation tag in the Billing console (Settings > Cost allocation tags). Until that second step is done, Cost Explorer cannot group by your tag — even if every resource is tagged perfectly. Do this today, not Thursday.
- CloudWatch does NOT collect memory or disk metrics by default — you must install the CloudWatch Agent inside the OS. It pushes data to the `CWAgent` custom namespace. Alarms on CWAgent metrics will stay in INSUFFICIENT_DATA until the Agent sends at least one data point.

**Hands-on tip**: Make sure your Automated Cost Guard (MH-COST-A) is firing before you leave Tuesday — it is the one required build today, and the scheduled trigger needs time to fire and produce a CloudTrail Stop event you can screenshot. If you also go for the Trusted Advisor bonus, use **config-based findings** (unattached EBS, unassociated EIP, missing S3 lifecycle, public S3, open SG on 22/3389, EBS with no snapshot) — these are the only ones that surface in a 48-hour account — and document the finding name, what you changed, and before/after screenshots. Two fully documented findings beat 12 undocumented ones.

---

### Wednesday — Security Monitoring, KMS & Automated Remediation

**Main topics**: AWS security monitoring stack (CloudTrail, GuardDuty, Config, Security Hub, Detective, Inspector), KMS and envelope encryption, event-driven security remediation with Lambda, environment audit

**Must-do hands-on**: Build your **Self-Healing Security Guard (MH-SEC)** — this is the core build of the day. KMS lab (create a customer managed key, separate admin and use roles in the key policy, encrypt at least 2 application resources) feeds your supporting control. Environment Audit lab (IAM Credential Report, S3 public access audit, CloudTrail verification) gives you the misconfiguration to hunt.

**Must-know concepts (read + discuss)**: The Core Security SimuLearn is a concept walkthrough, not a build-something lab — use it to review the security detection chain (IAM least privilege, CloudTrail logging, GuardDuty findings, common misconfigurations). The Security Best Practices course covers how each service connects in the detection chain.

**MH-SEC — Self-Healing Security Guard (required)**: This reuses the exact pattern you already built for the MH-COST-A Cost Guard — a Lambda triggered by EventBridge — but instead of stopping untagged compute, it detects and auto-fixes one security misconfiguration.
- **The auto-fix Lambda (required core)**: A Lambda + EventBridge trigger that detects ONE security misconfiguration and fixes it via boto3 with a least-privilege role. Pick one:
  - A Security Group with an open ingress rule (`0.0.0.0/0` on port 22 or 3389) → the Lambda revokes that rule, OR
  - An S3 bucket that is public → the Lambda enables Block Public Access on it.
- **Prove it heals**: intentionally create the violation (open the SG / make a bucket public), let the Lambda fire, then capture before/after screenshots AND the CloudTrail event for the fix API call (`RevokeSecurityGroupIngress` or `PutPublicAccessBlock`). The CloudTrail event proving your code actually performed the fix is what scores — not just "the Lambda exists."
- **PLUS one supporting preventive control**, pick one:
  - S3 account-level Block Public Access turned on + a bucket policy that denies unencrypted or non-TLS access, OR
  - A KMS Customer Managed Key (CMK) with key rotation enabled, used to encrypt one data store, OR
  - IAM Access Analyzer enabled with at least one finding triaged (reviewed + resolved or justified).
- **PLUS a 1-2 sentence security-cost statement**: explain the security-vs-cost trade-off you made (e.g. why you chose this detection/fix and supporting control given the $150 cap).
- You do NOT need AWS Config (recorder or managed rule), SSM Automation documents, or an AutomationAssumeRole for MH-SEC. (If you'd rather use a Config managed rule purely as the *detection* trigger feeding your Lambda, that's an accepted alternative — but it is optional, not required.)

**What to pay attention to**:
- KMS does NOT directly encrypt your application data. It generates a data key that your code uses to encrypt locally, then stores a copy of that data key encrypted (alongside your ciphertext). When you need to decrypt, you send the encrypted data key to KMS and get the plaintext key back. KMS never sees your actual data. If you delete a KMS key, everything encrypted with it is permanently unrecoverable.
- The difference between the AWS-managed key (`aws/s3`) and a Customer Managed Key (CMK): the AWS-managed key is controlled by AWS — you cannot set a key policy or rotate it on demand. A CMK is one you create, where you decide who the KeyAdministrators and KeyUsers are, and you can turn on automatic rotation. If you use the KMS supporting control, only a CMK with rotation enabled demonstrates that you actually control the encryption.
- Give the auto-fix Lambda a least-privilege role — only the specific describe/revoke or put-public-access-block actions it needs, no wildcards. This is the same discipline as the Cost Guard role.

**Hands-on tip**: Run the heal loop end-to-end — create the violation on purpose, watch the Lambda fire, confirm the misconfiguration is gone, and grab the CloudTrail event for the fix call plus before/after screenshots. That CloudTrail event of your Lambda fixing the problem is what separates a "we detected it" story from a "it self-healed" story.

---

### Thursday — Review and Prep Day

Use Thursday to close gaps from Mon-Wed and finalize all 4 MH deliverables before Friday.

**Morning**: Trainer-led review of top checkpoint misconceptions, then group consolidation work organized around the 4 Must-Haves:

1. **Cost Visibility (MH-COST-V)**: Produce your tagging strategy document (4+ keys, agreed values and capitalization). Confirm cost allocation tags are activated in the Billing console (Settings > Cost allocation tags — screenshot both the strategy doc and the activation confirmation). Open Cost Explorer filtered by your CostCenter tag and identify your top-3 cost drivers. Write a brief baseline cost breakdown observation. Your trainer will check the tagging doc and the Billing console activation during walkabout.

2. **Cost Control & Action (MH-COST-A)**: Confirm your Automated Cost Guard works: show the CloudTrail `StopInstances`/`StopDBInstance` event proving the scheduled Lambda (with its least-privilege role) turned an untagged resource off, plus the Budgets ($150 daily) → SNS → Lambda wiring demonstrated by a test SNS publish, and the latency ADR. Your trainer will look for a resource actually stopped by automation during walkabout — a notification with nothing stopped does not pass.

   **Optional bonus — Optimization Actions**: If you went for the bonus, finalize your config-based TA findings table (at least 2 with before/after evidence), gp2→gp3 migration documentation (volume ID, IOPS setting, throughput setting, cost comparison), RI/SP break-even analysis or justified deferral, and a 100-150 word "wasteful → changed" reflection (what you found, what you changed, the impact).

3. **CloudWatch Observability (MH-OBS)**: Confirm your dashboard has at least 3 meaningful widgets (1 API-layer metric, 1 data-layer metric, 1 CWAgent metric). Confirm at least one alarm is in OK state — if any alarm is in INSUFFICIENT_DATA, investigate and fix now. Save a Log Insights query with a result screenshot.

4. **Self-Healing Security Guard (MH-SEC)**: Confirm your auto-fix Lambda actually healed the violation — show the before state (open SG / public bucket), the after state (rule revoked / Block Public Access on), and the CloudTrail event of the fix API call. Confirm your supporting preventive control is in place (S3 BPA + deny-unencrypted/non-TLS bucket policy, OR a KMS CMK with rotation, OR IAM Access Analyzer with a triaged finding). Write your 1-2 sentence security-cost statement.

**Afternoon**: Finalize your Evidence Pack (`docs/W6_evidence.md`). Every section needs screenshots with 1-2 lines explaining the configuration — raw screenshots without context do not count toward the score-4 threshold. All 4 MH sections must be present.

Submit your updated architecture diagram and Evidence Pack link to the trainer Slack channel before 17:00.

---

### Friday — Show What You Know

Groups 9-15 present W6 content this week. Groups 1-8 present next Friday.

Presentation runs ~10-12 minutes per group in four parts:
1. **Project Recap (~1.5 min)**: give a short verbal/slide recap of the project — what the application is, its business domain, and the key architecture and design decisions carried forward from W1-W5 — to frame the W6 operational work. No diagram update and no live app action are required here. If you addressed any W5 feedback, mention it briefly — optional, not a scored gate.
2. **W6 Architecture (~3 min)**: walk through all 4 MH additions in order:
   - Cost Visibility layer (MH-COST-V): tagging strategy + cost allocation tag activation + Cost Explorer top-3 cost driver view + baseline cost breakdown observation
   - Cost Control layer (MH-COST-A): Automated Cost Guard — scheduled Lambda (least-privilege role) stopping untagged compute, proven via CloudTrail Stop event; Budgets $150 → SNS → Lambda + latency ADR
   - Monitoring layer (MH-OBS): CloudWatch dashboard + alarm in OK state + Log Insights query result
   - Security layer (MH-SEC): Self-Healing Security Guard — Lambda + EventBridge that auto-fixed one misconfiguration (before/after + CloudTrail fix event) + supporting preventive control + 1-2 sentence security-cost statement
   - Optional bonus, if done: config-based TA findings with before/after + gp2→gp3 migration data + RI/SP analysis/deferral + "wasteful → changed" reflection
3. **Individual QnA (~3 min)**: 2-3 team members called by name — any team member can be picked. Prepare the whole team, not just the person who built each piece
4. **Live Demo (~3-4 min)**: ASG auto-healing, the Self-Healing Security Guard fixing a misconfiguration (before/after + CloudTrail fix event), tagging strategy + cost allocation tag activation evidence, Cost Explorer filtered by tag, Automated Cost Guard stopping an untagged resource (CloudTrail Stop event), your supporting preventive control. If you did the bonus: EBS volume settings (type, IOPS, throughput) and config-based TA findings with before/after

Post your `docs/W6_evidence.md` commit link in the trainer Slack channel before your slot. No link = Criterion IV capped at 3.

---

## This Week's Deliverables

Your group must deliver by Friday — and your AWS account total must stay **≤ $150** for the week (exceeding it fails the entire W6 assignment; see the W6 Cost Discipline Memo):

1. **MH-COST-V — Cost Visibility & Attribution**:
   - Tagging strategy document with at least 4 agreed tag keys (Owner, Environment, CostCenter, Application), agreed values, and capitalization convention
   - Cost allocation tags activated in the Billing console (screenshot showing activation in Settings > Cost allocation tags — this is the step most groups miss)
   - At least 1 cost visibility tool used: Cost Explorer filtered by tag showing your top-3 cost drivers, OR Budgets alert configured, OR Cost Anomaly Detection enabled
   - 1-page strategy doc summarizing your cost governance decisions for this deployment
   - Baseline cost breakdown screenshot with top-3 cost driver observation noted
   - Account total kept ≤ $150 with evidence you actively chose cheaper resources (Single-AZ, smallest instance that works, serverless, overnight shutdown) — this is part of MH-COST-V, not extra work

2. **MH-COST-A — Cost Control & Action** (the Automated Cost Guard):
   - An EventBridge Scheduler/daily-cron → Lambda that stops billable compute (EC2/RDS) not tagged `keep=true`, with a least-privilege execution role (only the describe/stop actions it needs)
   - Demonstrably turning a resource off: a resource left running, then stopped by the scheduled Lambda, captured as a CloudTrail `StopInstances`/`StopDBInstance` event with before/after state
   - AWS Budgets (daily $150) → SNS → the same Lambda, demonstrated via a test SNS publish
   - A short latency ADR (cost data lags ~8-24h so the real cost trigger likely won't fire in a 48h account — expected, not penalized; a missing scheduled mechanism, no demonstrated stop, or a missing ADR is not acceptable)
   - Graded on a resource actually being turned off by automation, not a notification

3. **MH-OBS — CloudWatch Observability**:
   - Dashboard with at least 3 meaningful metrics (one API-layer, one data-layer, one CloudWatch Agent metric from `CWAgent` namespace)
   - At least one alarm configured and in OK state
   - Log Insights query saved with result screenshot

4. **MH-SEC — Self-Healing Security Guard**:
   - A Lambda + EventBridge trigger (same pattern as the MH-COST-A Cost Guard) that detects ONE security misconfiguration and auto-fixes it via boto3, with a least-privilege execution role — recommended: a Security Group open to `0.0.0.0/0` on port 22/3389 → revoke that rule, OR a public S3 bucket → enable Block Public Access
   - Demonstrated end-to-end: intentionally create the violation, the Lambda fixes it, captured as before/after screenshots PLUS the CloudTrail event for the fix API call (e.g. `RevokeSecurityGroupIngress` / `PutPublicAccessBlock`)
   - One supporting preventive control: S3 account-level Block Public Access + a deny-unencrypted/non-TLS bucket policy, OR a KMS CMK with rotation enabled on a data store, OR IAM Access Analyzer enabled with at least one finding triaged
   - 1-2 sentence security-cost statement: the security-vs-cost trade-off you made and why it fits your project given the $150 cap
   - GuardDuty and CloudTrail enabled
   - AWS Config recorder / managed rule / SSM Automation / AutomationAssumeRole are NOT required (a Config managed rule may optionally be used only as the detection trigger feeding your Lambda)

5. **Evidence Pack** (`docs/W6_evidence.md`): Cover (group ID, repo link, W5 Evidence Pack link), MH-COST-V, MH-COST-A, MH-OBS, MH-SEC, Project Recap (a short written recap — what the app is, its business domain, and the key design decisions carried forward from W1-W5), Bonus (optional). Screenshots with 1-2 line config notes per item. Slides link to commit hash. No Evidence Pack = score capped at 2. Screenshots without notes = capped at 3.

**Optional bonus — Optimization Actions** (not required; strengthens your W7 demo and interview story):
- Trusted Advisor findings table: at least 2 **config-based** findings actually remediated (before state, action taken, after state — screenshot each stage). Use config-based checks (unattached EBS, unassociated EIP, missing S3 lifecycle, public S3, open SG on 22/3389, EBS with no snapshot) — config-based TA findings fire within 48h; utilization-based ones do not
- gp2→gp3 migration: volume ID, old type, new IOPS setting, new throughput setting, cost comparison (for each migrated volume)
- RI/SP break-even analysis: a documented decision or a written justified deferral
- 100-150 word "wasteful → changed" reflection: what did you find wasteful, what did you change, what was the outcome?

**Bonus (+0.25)**: Extend the Self-Healing Security Guard to detect and auto-fix a SECOND distinct misconfiguration (e.g. it handles both an open Security Group and a public S3 bucket), with before/after + CloudTrail evidence for the second fix too.

---

## How You'll Be Evaluated

- **Group Architecture (20%)**: Were all 4 MH additions correctly configured and placed in your diagram? Can your team defend the choices — how the Automated Cost Guard decides what to stop and why its role is least-privilege, what your tagging strategy enforces, which security misconfiguration your Self-Healing Security Guard fixes and which supporting control you chose and why?
- **Individual QnA (30%)**: Your ability to explain how the Automated Cost Guard works end-to-end (schedule → Lambda → tag check → stop, plus the Budgets → SNS path and why the real cost trigger lags), the two-step tagging + cost allocation tag activation process, how the Self-Healing Security Guard detects and fixes its misconfiguration (and why its role is least-privilege), and KMS envelope encryption — when called on. Every team member can be picked.
- **Deployment and Evidence (40%)**: The biggest slice. Graded against your Evidence Pack section by section.
  - Score of 4 requires: account total ≤ $150; all 4 MH sections with screenshots and notes; tagging strategy with cost allocation tag activation evidence and baseline cost breakdown observation; Automated Cost Guard with a resource actually stopped by the scheduled least-privilege Lambda (CloudTrail Stop event) plus Budgets $150 → SNS → Lambda demonstrated and the latency ADR; CloudWatch dashboard with CWAgent metric; alarm in OK state; Log Insights query saved; Self-Healing Security Guard that auto-fixed one misconfiguration with before/after and the CloudTrail fix event, plus one supporting preventive control; slides linked to Evidence Pack
  - Score of 5 requires all of the above PLUS one of: auto-healing event in CloudWatch Activity Log with timestamps, the Self-Healing Security Guard fixing a SECOND distinct misconfiguration (before/after + CloudTrail fix event), or a completed Optimization Actions bonus (config-based TA finding with before/after remediation, ideally cost impact quantified)
- **Project Recap (10%)**: A crisp, accurate recap of the project — what the application is, its business domain, and the key design decisions carried forward from W1-W5 — that clearly frames the W6 operational work. Scored purely on the clarity and accuracy of the recap; no diagram update or live app action is required. Mentioning W5 feedback specifically is a bonus, not a requirement.
- **Daily checkpoints**: Kahoot games Monday through Wednesday count toward your score

---

## Pro Tips

- **Watch the $150 cap from Day 1.** Set a Budgets alert immediately, default to Single-AZ and the smallest instance that works, prefer serverless, and shut down compute overnight. Exceeding $150 fails the whole W6 assignment regardless of how good your Must-Haves are — read the W6 Cost Discipline Memo before you deploy.
- **Build the Automated Cost Guard early on Tuesday, not late.** The scheduled trigger needs time to actually fire so you can capture a CloudTrail Stop event before Friday. Give the Lambda a least-privilege role (only the EC2/RDS describe/stop actions — no wildcards), and grade yourself on a resource actually turned off, not on a notification. Don't expect the real Budgets cost trigger to fire in 48h — that's why the latency ADR exists.
- **The two-step tagging trap is the most common MH-COST-V failure.** Tag your resources AND activate cost allocation tags in the Billing console in the same session Monday or Tuesday. Do not wait until Thursday to find out Cost Explorer has been blind to your tags all week.
- **MH-SEC is a Self-Healing Security Guard — detection without a fix is not enough.** Build it as a Lambda + EventBridge, the same pattern as your Cost Guard. The most common failure this week is groups who detect the misconfiguration but never capture the CloudTrail event proving their Lambda actually fixed it. Create the violation on purpose so you have a clean before/after.
- **Install the CloudWatch Agent Monday or Tuesday.** If you wait until Wednesday, you will have no historical memory or disk metrics in your dashboard by Thursday walkabout — and alarms on `CWAgent` metrics will be stuck in INSUFFICIENT_DATA.
- **Everyone needs to understand the Automated Cost Guard and the Self-Healing Security Guard.** These are the two most likely topics in individual QnA, and they share the same Lambda + EventBridge pattern. Practice explaining: (1) how the schedule triggers the Cost Guard Lambda, how it decides what to stop from the `keep=true` tag, why the role is least-privilege, and why the real cost trigger lags; (2) how the Security Guard's EventBridge trigger fires the Lambda, how the Lambda detects the misconfiguration and fixes it via boto3, and why its role is least-privilege.
- **Going for the Optimization bonus? Capture the before state on Monday.** Documenting a gp2→gp3 before state requires your volume to still be on gp2 (volume ID, size, IOPS baseline, cost per GB-month). Config-based TA findings fire within 48h; utilization-based ones do not — two fully documented remediations beat 12 undocumented findings.

---

## Key AWS Services This Week

| Service | What it does | Why it matters for your project |
|---------|-------------|-------------------------------|
| EC2 Auto Scaling (ASG) | Automatically adds/removes instances based on demand; replaces unhealthy instances | Keeps your app running under load and after failures — the compute backbone for W7 load testing |
| Application Load Balancer | Distributes traffic across AZs; runs health checks | HA traffic layer — health check type must be "ELB" for application-aware replacement |
| Amazon EBS gp3 | Block storage with independently configurable IOPS (up to 16,000) and throughput | Right-size your database and app storage for real performance at lower cost than gp2 — gp2→gp3 migration is an optional bonus this week |
| AWS Trusted Advisor | Automated best-practice checks across 5 pillars (cost, performance, security, fault tolerance, service limits) | Optional bonus tool. In a 48h account, target **config-based** findings (unattached EBS, unassociated EIP, missing S3 lifecycle, public S3, open SG on 22/3389, EBS without snapshot) — remediate ≥2 with before/after. Config-based findings fire within 48h; utilization checks need ~14 days and won't. |
| AWS Lambda + EventBridge | Run code on a schedule or in response to events; call AWS APIs via boto3 | Powers BOTH MH-COST-A (the Automated Cost Guard stopping untagged EC2/RDS, proven by a CloudTrail Stop event) and MH-SEC (the Self-Healing Security Guard detecting and fixing one misconfiguration, proven by a CloudTrail fix event) — same pattern, least-privilege role both times |
| Amazon CloudWatch + Agent | Metrics, alarms, dashboards, log queries; Agent adds memory and disk from inside the OS | MH-OBS foundation — without the Agent, memory and disk are invisible to CloudWatch |
| AWS Cost Explorer | Visualizes costs by service, account, and tag over time | MH-COST-V core tool — requires cost allocation tag activation in Billing console before it can group by your tags |
| AWS Budgets | Cost and usage threshold alerts | MH-COST-V threshold alert + MH-COST-A trigger (daily $150 → SNS → Cost Guard Lambda) |
| Amazon S3 Block Public Access | Account- and bucket-level switch that blocks public access; pair with a deny-unencrypted/non-TLS bucket policy | MH-SEC — the recommended auto-fix target (public bucket → Lambda turns BPA on) and a supporting preventive control option |
| AWS KMS (CMK) | Manages encryption keys you create and control; key policy separates admin from use; supports automatic rotation | MH-SEC supporting preventive control option — a CMK with rotation enabled on a data store. Only a CMK (not the AWS-managed key) demonstrates you control the encryption. |
| AWS IAM Access Analyzer | Identifies resources shared outside your account/zone of trust | MH-SEC supporting preventive control option — enable it and triage at least one finding |
| AWS Config (optional) | Records resource configuration history; evaluates compliance rules | NOT required for MH-SEC. Optional only as a detection trigger feeding your Self-Healing Security Guard Lambda — not the deliverable itself. |
