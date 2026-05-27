# W2 Mission Brief: Lock It Down

**Week of April 13-17, 2026 | Presentation: Friday, April 17**

---

## What You Built Last Week

In Week 1, you did something most people applying for cloud jobs cannot do on day one: you designed a real 3-tier application, mapped it to AWS services, and produced an architecture diagram. You thought like an architect, not just a user of a tutorial. That diagram is your project's foundation.

Every week from here builds a new layer on top of it.

This week, you add the layer that separates production systems from toy demos.

---

## This Week's Mission

**Storage and identity.**

Your application has data. User files. Application logs. Backups. Maybe media assets or ML training data. Right now, in your W1 diagram, that data is floating in a cloud with no real home and no real protection.

This week, you fix that.

You will decide where every piece of data in your application lives — which S3 bucket, which storage class, which EBS volume — and you will design the rules that control who and what is allowed to touch it. IAM roles, scoped policies, and security boundaries for every tier of your architecture.

By Friday, your upgraded architecture should be able to answer one simple question that every interviewer, every auditor, and every senior engineer on a team you want to join will eventually ask:

**"Who can access what — and why?"**

---

## What Done Looks Like on Friday

Your group presents an upgraded version of the W1 architecture diagram plus a live demonstration. The presentation covers four areas:

**1. Your Storage Design**

Where does each category of data live in your application? Show your S3 buckets labeled by function, the EBS volumes attached to your EC2 instances, and explain why each storage service was chosen for its specific role. Walk through your storage class choice: why Standard, Standard-IA, Glacier, or something else — and what lifecycle policy automates the transitions. Show that all stored data is encrypted at rest.

**2. Your Identity Model**

Show the IAM roles you defined — one per compute resource, not one shared role for everything. Show the policies attached to each role and explain what each role is specifically allowed to do and, equally importantly, what it is not allowed to do. Demonstrate that your EC2 instances access AWS services through their IAM role only — no access keys stored anywhere on the server, in your code, or in environment variables.

**3. Your Security Boundaries**

Show the Security Groups protecting each tier of the application with specific port rules and source restrictions. Explain where encryption in transit applies to your application. Describe how you would detect if any S3 bucket accidentally became publicly accessible.

**4. A Live Demonstration**

From an EC2 instance, show that the application can access its S3 bucket using only its IAM role — no credentials file present on the instance. Then show that an identity without the appropriate policy is denied access to the same bucket. This does not need to be a complex demo — two AWS CLI commands and their output is sufficient.

---

## Why This Week Matters Beyond the Classroom

Storage and identity misconfiguration are the leading cause of data breaches in cloud environments. A publicly accessible S3 bucket. An EC2 instance with a wildcard IAM policy. Credentials accidentally committed to a repository. These are not hypothetical scenarios — they are the incidents that make news and end careers.

When you walk into a technical interview and describe an AWS architecture you built, the second question after "walk me through your design" is almost always: "How did you secure it?" This week gives you a specific, defensible, technically correct answer to that question.

Every cloud engineer on every team you will ever join has had to build this layer. By Friday, you will have built it too.

---

## How to Have a Strong Week

**Divide the work by ownership, not by task list.** Storage, IAM, Security Groups, the architecture diagram, and presentation delivery are five distinct workstreams. Assign an owner to each. The groups that struggle on Friday are the ones where one person built everything the night before.

**Justify every decision.** "We used S3" is a description. "We used S3 Standard-IA for our backup bucket because backups are accessed less than once a month, Standard-IA saves 45% on storage cost versus Standard, and the 30-day minimum duration fits our retention requirements" is an argument. Justifications are what separate a good presentation from a great one.

**Draw before you build.** Update the architecture diagram first. If you cannot draw the storage and identity layer coherently, you have not designed it — you have just listed services. The diagram reveals gaps before Friday does.

**Test your own understanding before Friday.** Before presentation day, have every group member spend five minutes explaining the full architecture to someone else without looking at the slides. Where they get stuck is where the QnA question will land. Fix the gap now.

**Address W1 feedback explicitly.** If your trainer flagged a gap last week, fix it and call it out in your presentation: "In W1, we had X problem — here is what we changed." That kind of intellectual honesty is exactly what senior engineers do after a code review or a post-incident review.

---

## How This Connects to Week 7

By the final week of the program, your application will be fully running on AWS. Trainers will log in, trigger scale events, simulate failures, and verify security. Everything depends on getting these fundamentals right now.

The IAM roles you define this week are the roles your application will use in production. The encryption you configure this week protects real user data. The Security Groups you design this week are the firewall that keeps your application safe under load.

You have five weeks of features, pipelines, networking, and operations ahead of you. All of it is built on what you lock down this week.

**Good luck. See you Friday.**
