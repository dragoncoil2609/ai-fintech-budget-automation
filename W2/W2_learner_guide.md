# Week 2 — Storage, Identity & Architecture: Making Your App Production-Ready

## What You Will Learn This Week

Last week you proposed a 3-tier application and drew your first AWS architecture diagram. This week you give that architecture real substance. You will learn how to store data correctly using S3, EBS, and EFS, lock down access with IAM roles and policies, and design a secure network using Amazon VPC. By Friday you will have upgraded your W1 diagram into a storage-and-identity layer that a real cloud engineer would review and approve.

These skills are not optional knowledge for cloud jobs — every AWS interview includes storage selection questions and IAM policy reasoning. This week puts that foundation in place.

---

## Focus Areas

### Monday — Storage & IAM Deep Dive

**Main topics**: Amazon S3 (storage classes, lifecycle, replication, encryption) — Amazon EBS and EFS — IAM users, groups, roles, and policies

**What to pay attention to:**
- The S3 storage class table. Know the access speed and minimum storage duration for each class. Glacier Instant retrieval is milliseconds. Glacier Flexible is 3-5 hours. Deep Archive is up to 12 hours. This comparison appears in every cloud interview.
- The difference between IAM users and IAM roles. A role is assumed temporarily and provides short-term credentials via STS. You never hard-code a role. Your EC2 instance "puts on" the role at launch and gets automatic credentials — no keys needed.
- Policy evaluation logic: if there is an explicit Deny anywhere, you are blocked. If there is an explicit Allow and no Deny, you are permitted. If nothing is defined at all, you are implicitly denied by default.

**Hands-on tips:**
- In the IAM lab, after creating your test user and attaching a policy, use the Policy Simulator to test a few scenarios — "Can this user read from S3?" "Can they write?" Running three test scenarios is more valuable than reading ten pages of documentation.
- When reviewing S3 storage classes, try creating a lifecycle rule in the console (even on a test bucket). Moving objects from Standard to Standard-IA after 30 days, then to Glacier after 90 days, is a pattern that comes up in real project work.

---

### Tuesday — EBS Advanced, Bedrock AI & Compute

**Main topics**: EBS volume types and snapshots — Amazon Bedrock and generative AI foundations — AWS compute services (EC2, Lambda, ECS, EKS, Fargate)

**What to pay attention to:**
- The EBS volume type decision tree. gp3 is the modern default — 3,000 IOPS baseline regardless of volume size, cheaper than gp2. Use io2 only when you need more than 16,000 IOPS or sub-millisecond database latency. Use st1 for sequential big-data workloads. sc1 is for cold data that you rarely touch.
- EBS snapshots are incremental — only changed blocks are saved after the first full snapshot. They are stored in S3 and can be copied across regions.
- The compute decision framework: EC2 gives you full control but requires you to manage the server. Lambda runs your code for up to 15 minutes without any server management, billed per millisecond. Fargate runs containers without managing the underlying EC2 fleet. Choose based on control requirements, workload duration, and whether the traffic is predictable.
- For Bedrock: the key concept is that you do not build the AI model — you access a pre-trained Foundation Model via an API. Retrieval-Augmented Generation (RAG) lets you ground the AI's answers in your own data stored in S3.

**Hands-on tips:**
- In the Bedrock console, try the Chat Playground with two different models (e.g., Claude vs. Amazon Titan) on the same prompt. Notice how the responses and token costs differ — this is model evaluation in practice.
- Limit your PartyRock exploration to 15 minutes. It is fun, but the EBS and compute courses are what you will be tested on Friday.

---

### Wednesday — Architecture & Security

**Main topics**: AWS Solutions Architect Fundamentals (13 modules covering Well-Architected Framework, VPC, Compute, Storage, Databases, Monitoring, Serverless, Edge Services, and Backup) — AWS Security Fundamentals (KMS, WAF, Shield, CloudTrail, GuardDuty)

**What to pay attention to:**
- The 6 pillars of the AWS Well-Architected Framework. Memorize them: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability. Every architectural decision you make in this program maps to one of these pillars.
- VPC networking is the topic most students find hardest. A public subnet has a route to an Internet Gateway — that is what makes it "public." A private subnet does not have that direct route but can use a NAT Gateway to initiate outbound connections. Security Groups are stateful (return traffic is automatic). NACLs are stateless (you need inbound AND outbound rules).
- For security: Shield Standard is free and automatic for all AWS customers. Shield Advanced is a paid upgrade that adds Layer 7 protection and the DDoS Response Team. WAF sits in front of your CloudFront or ALB and inspects HTTP requests for SQL injection, XSS, and bad IP patterns.

**Hands-on tips:**
- When watching Module 3 (Networking), pause and draw the VPC diagram yourself on paper before continuing. VPC clicks better when you sketch it than when you just watch it.
- In the security course, note which services overlap with each other: CloudTrail records who made API calls (audit trail). CloudWatch monitors metrics and sends alarms. GuardDuty uses ML to detect unusual behavior. AWS Config tracks whether your resources comply with rules. These four are often confused in interviews — keep a quick cheat sheet.

---

### Thursday — Review & Prep Day

Use Thursday to consolidate everything from Monday through Wednesday.

**Morning**: Your trainers will run a focused review covering the top misconceptions from this week's Kahoot results. Pay special attention if VPC, IAM policy logic, or EBS volume types come up — those are the most common gaps.

**Group activity**: Update your W1 architecture diagram with the W2 storage and identity layer:
- Add S3 buckets labeled by purpose (at least two: one for static assets, one for user uploads)
- Attach an EBS volume to your DB-tier EC2 and note the volume type with a one-sentence justification
- Add IAM roles for each compute resource (EC2, Lambda if applicable)
- Draw your VPC with a public subnet for the web tier and private subnets for the app and DB tiers

**Security Decision Log**: Write one paragraph that answers three questions:
1. Why did you choose each storage type for each component?
2. Which IAM pattern did you use and why?
3. What encryption is applied and with which key type?

Submit the updated diagram and Security Decision Log to the trainer Slack channel before 17:00 Thursday.

---

### Friday — Show What You Know

Each group presents their updated architecture diagram and Security Decision Log (5 minutes). After the presentation, one or two team members will be called by name for individual QnA (3 minutes).

**The QnA is individual** — every team member can be selected. You will be asked to explain a specific decision your group made, troubleshoot a scenario, or compare two AWS services. Your group presentation score and your personal QnA score are separate.

Prepare by making sure every person on your team can answer:
- Why did we choose gp3 (or whichever EBS type) for the database?
- What happens if someone puts AWS access keys directly in the application code?
- What is the difference between a Security Group and a NACL?
- How does an EC2 instance in a private subnet get internet access?

---

## This Week's Deliverables

Your group must deliver by Friday:

1. **Updated architecture diagram** — shows all W2 additions: labeled S3 buckets, EBS volume with type specified, IAM roles for all compute components, VPC with public/private subnet segmentation
2. **Security Decision Log** — one paragraph minimum explaining storage choices, IAM patterns, and encryption configuration
3. **Encryption confirmation** — state whether you are using SSE-S3 or SSE-KMS for your S3 buckets and EBS volumes

---

## How You Will Be Evaluated

- **Group presentation**: Quality of your architecture additions, completeness of all three deliverables, security best practices applied, and clarity of your Friday presentation. AWS Architecture carries the most weight.
- **Individual QnA**: Your ability to explain your group's architectural decisions when called on during QnA — accuracy, reasoning, and confidence all matter. Every team member can be picked.
- **Daily checkpoints**: Kahoot/Blooket/Quizlet games Monday through Wednesday are tracked — take them seriously.
- **Peer evaluation and participation**: Your teammates evaluate your contribution, and classroom participation is tracked daily.

---

## Pro Tips

- **IAM roles, not access keys**: If your architecture shows AWS access keys stored anywhere in code or on an EC2 instance, that is an automatic flag in the evaluation. Always attach a role to the compute resource and let AWS manage the temporary credentials.
- **Draw the VPC first**: Before adding any other service to your architecture this week, draw the VPC boundary, the subnets, and the route tables. Everything else goes inside that structure.
- **Use the storage comparison table**: Before choosing S3 vs EBS vs EFS for any component, run through three questions — Does it need to be shared across multiple EC2 instances at once? (Yes = EFS.) Does one EC2 instance need fast block-level access? (Yes = EBS.) Is it accessible over HTTP or needed by many users/services? (Yes = S3.)
- **Know your six pillars cold**: The Well-Architected Framework pillars will be referenced in every week going forward. Write them on a sticky note next to your laptop now.

---

## Key AWS Services This Week

| Service | What it does | Why it matters for your project |
|---|---|---|
| Amazon S3 | Object storage — buckets, objects, storage classes, lifecycle policies | Stores your front-end static files, user uploads, and backups |
| Amazon EBS | Block storage volumes that attach to a single EC2 instance | Provides the fast, persistent disk for your database server |
| Amazon EFS | Shared file system mountable by multiple EC2 instances simultaneously | Useful if multiple app-tier EC2s need access to the same files |
| AWS IAM | Controls who can access what in your AWS account | Defines which EC2 instances and Lambda functions can read/write which resources |
| Amazon VPC | Your private virtual network in AWS | Isolates your web, app, and database tiers into public and private subnets |
| AWS KMS | Manages encryption keys for data at rest | Encrypts your S3 objects and EBS volumes without managing keys yourself |
| Amazon Bedrock | Fully managed generative AI service with access to 100+ foundation models | Enables AI-powered features without training your own model |
| AWS WAF | Web Application Firewall — filters HTTP requests | Protects your ALB or CloudFront distribution from SQL injection and XSS |
| AWS Shield | DDoS protection — Standard (free) and Advanced (paid) | Automatically absorbs volumetric attacks against your infrastructure |
| Amazon CloudFront | Global CDN — caches content at edge locations worldwide | Delivers your S3-hosted static assets faster to users globally |
