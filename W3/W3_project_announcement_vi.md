---
week: 3
title: "W3: Xương Sống Database"
audience: students
release: "Sáng thứ Hai 2026-04-20"
deadline: "Thứ Sáu 2026-04-24, group presentation"
---

# W3: Xương Sống Database

> 20-24/4/2026

---

## Thử Thách

W2 đã có deployment thật rồi — S3 buckets đã được lock down với IAM, EBS volumes gắn vào compute, hạ tầng AWS thật đầu tiên của các bạn đang chạy. Không có gì thay đổi về điều đó ở W3. App 3-tier vẫn tiếp tục chạy ở nơi nó đang chạy.

Cái thay đổi tuần này là **những gì được thêm vào và cách các bạn chứng minh nó hoạt động**. Các service xếp chồng lên — RDS, DynamoDB, Bedrock, Lambda, CloudFormation — sâu hơn so với S3 buckets. Một database cấu hình sai có thể tồn tại trong console nhưng không reach được từ app. Một Lambda có thể deployed nhưng không bao giờ được invoke. Một Bedrock Knowledge Base có thể sync xong nhưng trả về rác. "It was deployed" không đồng nghĩa với "it works." Vì thế W3 siết chặt grading discipline: rubric weight dịch chuyển từ diagram (II: 50 → 20) sang deployment-with-evidence (IV: 10 → 40), và mỗi acceptance criterion tuần này phải được chống lưng bởi screenshot + configuration note trong một Evidence Pack markdown.

Có 4 thứ phải nộp vào thứ Sáu cộng với Evidence Pack. Không phải 5 đề xuất — 5 yêu cầu. Mỗi cái map trực tiếp với thứ các bạn đang học tuần này: databases vào thứ Hai và thứ Ba, networking và Lambda vào thứ Tư. Build trong khi học, document trong khi build.

---

## Những Gì Phải Kế Thừa Từ W2 (Bắt Buộc)

Mỗi tuần là một sự nối tiếp, không phải restart. Trước khi thêm W3 content, các W2 outputs sau phải vẫn còn tại chỗ — trainer sẽ verify những cái này vào thứ Sáu cùng với W3 must-haves mới:

- [ ] **S3 buckets từ W2** vẫn có Block Public Access ON, default encryption enabled, và versioning bật. Bedrock Knowledge Base trong MH2 phải connect tới một trong những bucket đang có — không phải bucket mới.
- [ ] **IAM baseline từ W2**: MFA trên root, một admin group, named IAM users (không dùng root console access). Mọi IAM feedback từ W2 phải được resolve — nếu team bị flag vì wildcard policies, fix trước khi W3 được evaluate.
- [ ] **VPC diagram từ W2** được mở rộng trong MH4 — không tạo VPC mới. Label các tier đã có và thêm private database tier ở trên.
- [ ] **W2 trainer feedback được cite trong Part 1 recap** — kể tên 1 item cụ thể và show cách W3 addresses nó.

Nếu bất kỳ W2 item nào missing hoặc broken khi thứ Sáu đến, nó tính vào W3 Criterion II (AWS Architecture).

---

## Những Gì Các Bạn Phải Nộp (4 Core Must-Haves)

Đây là các deliverable bắt buộc cho W3. Cả 4 đều phải demo được vào thứ Sáu.

### 1. Database Layer — Chọn Đúng Database Cho Data Của MÌNH

**Rule thay đổi tuần này.** Các bạn **không** cần cả RDS và DynamoDB — và cũng **không bị giới hạn** ở 2 cái đó. Việc của các bạn là nhìn data thật của app mình, chọn engine + paradigm fit, và chứng minh lựa chọn đúng với một scenario.

Các bạn có thể dùng bất kỳ AWS-managed database nào (RDS, Aurora, DynamoDB, DocumentDB, Neptune) HOẶC self-host engine trên EC2 (Postgres, MySQL, MongoDB, hoặc tương tự) — miễn là document trade-off. Thứ Hai và thứ Ba vẫn dạy RDS và DynamoDB như 2 paradigm chuẩn cho relational và key-value; áp dụng những paradigm đó vào bất kỳ engine nào fit với data.

Nhóm chọn 1 engine tốt sẽ có điểm cao hơn nhóm deploy nhiều engine mà không biện hộ được cái nào.

**Step 1 — Match data pattern với paradigm, rồi chọn engine.**

Có 4 paradigm. Chọn cái fit với data, rồi chọn engine bên trong paradigm đó.

| Paradigm | Data trông như thế nào | Engine ví dụ |
|----------|------------------------|--------------|
| **Relational** | Rows/columns, foreign keys, JOIN, ACID transactions | RDS (Postgres/MySQL/MariaDB/SQL Server), Aurora, self-hosted Postgres/MySQL trên EC2 |
| **Key-Value** | Lookup theo known key ở scale lớn, access pattern predictable, schema flexible per-item | DynamoDB |
| **Document** | Fields thay đổi per-user/per-tenant, nested documents, aggregation pipeline | DocumentDB, self-hosted MongoDB trên EC2 |
| **Graph** | Relationship chính là data — N-hop traversal, friend-of-friend, recommendation | Neptune |

| Data của bạn trông như thế nào | Paradigm đúng | Engine ví dụ |
|--------------------------------|---------------|--------------|
| Users → orders → items với foreign keys, cần JOINs | **Relational** | RDS Postgres, Aurora, self-hosted Postgres |
| Payments, inventory decrement, bank transfer (phải all-or-nothing) | **Relational** | RDS/Aurora (ACID transactions) |
| Complex ad-hoc queries, reports, BI-style aggregations | **Relational** | RDS/Aurora |
| Lookup theo known key ở scale rất lớn (session, device event, profile) | **Key-Value** | DynamoDB |
| >1,000 writes/sec sustained | **Key-Value** | DynamoDB |
| Schema per-tenant thay đổi thường xuyên, nested documents, aggregation pipeline | **Document** | DocumentDB, self-hosted MongoDB |
| N-hop relationship traversal (social graph, recommendations) | **Graph** | Neptune |
| Operational data + high-volume events trong CÙNG app | **Nhiều paradigm** | Mỗi engine làm tốt việc của mình |

**Step 2 — Đáp ứng checklist cho engine + paradigm CỦA BẠN:**

Mọi engine đã chọn, bất kể paradigm nào, phải đáp ứng:
- [ ] Deploy trong **private subnet** (không có public internet access) — chỉ reach được từ application tier qua security group
- [ ] Encryption at rest enabled
- [ ] HA plan: **Multi-AZ enabled** (managed engine) HOẶC **replica + snapshot plan documented** (self-hosted) HOẶC **acknowledged single-point-of-failure (SPOF)** cho tuần này với written reasoning (chỉ self-hosted)
- [ ] Ít nhất 1 record được write và read qua application hoặc CLI — không chỉ tạo trong console

Rồi thêm paradigm-specific operations để prove engine phục vụ access patterns. Demo phải show **2 representative operations**:

- **Relational (RDS / Aurora / self-hosted SQL):**
  - [ ] Schema có **ít nhất 2 related tables với foreign key**, demo show **1 JOIN query** trả về rows thật
  - [ ] **1 indexed lookup** (đặt tên index hỗ trợ WHERE / JOIN)
  - [ ] Automated backups configured (managed: 7+ ngày retention; self-hosted: pg_dump / mysqldump cron hoặc tương đương)

- **Key-Value (DynamoDB):**
  - [ ] Partition key là **high-cardinality** (user_id, order_id, device_id — KHÔNG phải `status`, `active`, hoặc bất kỳ field nào có <20 distinct values)
  - [ ] Capacity mode là on-demand HOẶC provisioned với **auto scaling enabled** (provisioned không auto-scaling = fail)
  - [ ] **1 Query** theo partition key + **1 GSI query** (không Scan cho access pattern thường xuyên)

- **Document (DocumentDB / self-hosted MongoDB):**
  - [ ] **1 aggregation pipeline** trả về kết quả shaped/grouped
  - [ ] **1 indexed-field lookup** (đặt tên secondary index hỗ trợ query)

- **Graph (Neptune):**
  - [ ] **1 traversal query** (N-hop, ví dụ friend-of-friend)
  - [ ] **1 property / node lookup** theo indexed attribute

Thêm gates:
- [ ] **Nếu self-hosted trên EC2** (bất kỳ engine nào): backup strategy (AMI snapshot, `pg_dump` cron, hoặc acknowledged SPOF) + HA plan + trade-off reasoning document trong Evidence Pack section 2 Part B
- [ ] **Nếu high-cost managed engine** (DocumentDB, Aurora, Neptune — minimum instance ~$200+/tháng): rough monthly cost estimate trong Part B. Đừng chọn engine "fancy" cho data flat đơn giản khi RDS hoặc DynamoDB fit

Nếu chọn **nhiều engine**, đáp ứng checklist cho mỗi paradigm VÀ show trong Data Access Pattern Log query nào đi vào engine nào và tại sao. "Cả hai" không phải cheat code — mỗi engine cần justification riêng.

**Step 3 — Submit Data Access Pattern Log (bắt buộc, tối đa 1 trang).** Không có log này, MH1 không thể được điểm trên 3 dù deployment có polished đến đâu. Ba phần:

- **Part A — 3 access pattern thật từ app của các bạn.** Mỗi cái 1 câu + frequency ước lượng. Ví dụ: "Get all orders for a user, sorted by date — ~50 calls/phút lúc peak."
- **Part B — Cho mỗi pattern: engine + paradigm và tại sao hiệu quả.** Đặt tên index (relational) hoặc partition key + sort key / GSI (key-value) hoặc aggregation / indexed field (document) hoặc traversal (graph) phục vụ query không cần full Scan. Nếu self-hosted: include backup/HA plan + trade-off reasoning (tại sao self-host thay vì managed). Nếu high-cost managed: include rough monthly cost estimate.
- **Part C — "Wrong-paradigm" test.** Chọn 1 pattern. Trong 2-3 câu, giải thích cái gì sẽ break hoặc cost quá cao nếu paradigm từ CATEGORY KHÁC phục vụ nó. Ví dụ: "Pattern 10k writes/sec session trên relational engine sẽ cần sharding + connection pool + queue phía trước; single table sẽ grow unboundedly nếu không partitioning." Đây là phần các bạn chứng minh đã thật sự hiểu TẠI SAO paradigm của mình fit với data — không chỉ là nó chạy được.

**Step 4 — Năm ví dụ mẫu (chọn cái gần app của bạn nhất):**

| App type | Data shape | Engine + paradigm | "Wrong-paradigm" test |
|----------|-----------|-------------------|-----------------------|
| **E-commerce** | Users, products, orders, order_items với FKs; đặt order = decrement inventory + insert order + insert items trong 1 transaction | **RDS/Aurora (relational)** | Key-value sẽ cần TransactWriteItems qua 3 items + GSI cho order history; schema changes yêu cầu rewrite consuming code |
| **IoT telemetry** | 10k devices × 1 event/sec, query "events cho device X trong giờ qua" | **DynamoDB (key-value)** (PK=device_id, SK=timestamp) | Relational ở 10k writes/sec cần sharding + connection pooling + queue phía trước |
| **Multi-tenant SaaS** | Mỗi tenant thêm custom fields; nested config objects per tenant | **DocumentDB hoặc self-hosted MongoDB (document)** | Relational sẽ ép schemas rigid thêm columns cho mỗi tenant, hoặc sparse EAV table giết query performance |
| **Social feed** | "Friends of friends like posts tag X" — 3-4 hop traversal | **Neptune (graph)** | Relational `users JOIN edges JOIN edges JOIN edges` explode — ở depth 4 query plan intractable |
| **Cost-sensitive Postgres** | Team nhỏ, cần Postgres extensions cụ thể, managed RDS cost quá cao | **Self-hosted Postgres trên EC2 (relational)** | Managed alternative sẽ cost more hoặc hide protocol-level control cần có (custom extensions, specific version); chấp nhận ops burden đổi lại — backup qua `pg_dump` cron + replica trên EC2 thứ 2 |

Data Access Pattern Log của các bạn nên nhìn giống một trong 5 cái trên. Các bạn không bắt buộc dùng một trong số đó — nhưng nếu log vague hơn những ví dụ này, nó không đủ specific.

> **Log này ở đâu:** Data Access Pattern Log là section 2 của **Evidence Pack** (xem bên dưới — file markdown bắt buộc). Nó KHÔNG phải document standalone.

### 2. AI/Bedrock Layer — Knowledge Base + Retrieval

Tạo Bedrock Knowledge Base kết nối với S3 bucket đã có từ W2. Ingest documents vào đó. Make 1 Retrieve hoặc RetrieveAndGenerate call trả về kết quả thật.

Acceptance criteria:
- [ ] Bedrock Knowledge Base tạo xong và connect với S3 bucket từ W2
- [ ] Ít nhất 3 documents được ingest (sync job status: Complete)
- [ ] Các bạn đọc được tên **embedding model** đã chọn (ví dụ: Amazon Titan Embeddings G1 - Text)
- [ ] Các bạn đọc được tên **vector store** đã chọn (OpenSearch Serverless, Aurora PostgreSQL, hoặc S3 Vectors)
- [ ] 1 Retrieve hoặc RetrieveAndGenerate API call được demo **ngoài** Bedrock console — qua Lambda, CLI, hoặc application code

Bedrock Playground dành cho học và thử nghiệm. Deliverable là API call thật từ application flow.

### 3. Lambda Layer — Serverless Glue

Build ít nhất 1 Lambda function kết nối application tier với AI layer (Bedrock) hoặc database layer. Đây là serverless glue giữa các component.

Acceptance criteria:
- [ ] Lambda execution role policy **không có statement** `Action: "*"`
- [ ] Lambda execution role policy **không có statement** `Resource: "*"` — permissions scope về specific resources
- [ ] Ít nhất 1 trigger được demo live: **S3 event trigger** (function fire khi upload object) HOẶC **API Gateway integration** (HTTP call invoke function)
- [ ] Function output thấy được: CloudWatch log, 1 DynamoDB item được write, hoặc Bedrock response trả về

Least-privilege IAM không phải tùy chọn ở đây. Lambda role có wildcards = failing acceptance criterion.

### 4. VPC và Networking — Multi-Tier + Gateway Endpoint

Hardening VPC của W2 thành proper multi-tier network. Đây cũng là nơi W2 gap về S3 Gateway Endpoint được fix.

Acceptance criteria:
- [ ] VPC diagram show **3 tiers có label**: public, private application, private database
- [ ] **S3 Gateway Endpoint** được provision và explicit labeled trên diagram (với route table entry của nó)
- [ ] Database Security Group's inbound rule reference **application tier Security Group ID** — không phải subnet CIDR block
- [ ] Các bạn giải thích được verbally: 1 scenario khi dùng NACL thay vì Security Group

Nếu W2 diagram không có S3 Gateway Endpoint, tuần này là lúc thêm vào. Đây là Friday acceptance criterion.

### 5. Evidence Pack — Artifact Quyết Định Điểm Của Các Bạn

> **Đây là deliverable quan trọng nhất của tuần.** Criterion IV (Deployment & Evidence) là 40% điểm W3 — tăng từ 10% ở W2 — và được chấm gần như hoàn toàn dựa vào file này.

**Cái gì:** một file markdown duy nhất trong group repository tại `docs/W3_evidence.md`. Đây là source of truth. Slides thứ Sáu **derive từ markdown này** — copy 8-12 screenshots + captions tốt nhất từ markdown vào slide deck, rồi present deck vào thứ Sáu. Đừng viết slides trước và markdown sau.

**Tại sao markdown:** slides bị lạc, bullets bị cắt, screenshots bị mờ khi resize. Một file markdown trong repo ở lại cùng code, giữ full-resolution screenshots, và cho phép trainer re-verify claims sau thứ Sáu. Nhóm skip markdown và chỉ dựa vào slides sẽ cap IV ở 3.

**Required structure (mỗi nhóm, mỗi section — trainer check section-by-section):**

1. **Cover** — group number, member names, **database path đã chọn** (engine + paradigm — ví dụ: "RDS Postgres / relational", "DynamoDB / key-value", "DocumentDB / document", "self-hosted MongoDB trên EC2 / document"), link ngược lại W2 evidence.
2. **Data Access Pattern Log** — Parts A, B, C (log từ must-have 1, embedded ở đây). Part B phải capture engine + paradigm + reasoning; nếu self-hosted, backup/HA plan + trade-off; nếu high-cost managed, monthly cost estimate.
3. **Deployment Evidence — mỗi acceptance criterion 1 entry cho paradigm đã chọn.** Mỗi entry cần:
   - 1 screenshot (AWS console) HOẶC CLI output (`aws rds describe-db-instances`, `aws dynamodb describe-table`, `aws docdb describe-db-clusters`, `aws neptune describe-db-clusters`, `aws ec2 describe-security-groups`, hoặc engine-native commands cho self-hosted)
   - 1-2 dòng notes: "We configured X this way because Y." Không phải "encryption enabled" — thay vì "encryption enabled với AWS-managed KMS key aws/rds. We chose AWS-managed over customer CMK vì chưa có compliance mandate và muốn rotation tự động."
4. **Working Query Evidence** — 2 representative operations match với paradigm, mỗi cái có screenshot + real results:
   - Relational: 1 JOIN qua 2 related tables + 1 indexed lookup
   - Key-Value: 1 Query theo partition key + 1 GSI query (không Scan)
   - Document: 1 aggregation pipeline + 1 indexed-field lookup
   - Graph: 1 traversal (N-hop) + 1 property/node lookup
   - Nhiều paradigm: 1 operation cho mỗi paradigm.
5. **Lambda + Bedrock Evidence** — CloudWatch Logs entry với timestamp sau Lambda trigger, Bedrock Retrieve/RetrieveAndGenerate response từ Lambda hoặc CLI (không phải Playground).
6. **VPC + Networking Evidence** — route table show S3 Gateway Endpoint, DB Security Group inbound rule show app-tier SG làm source.
7. **Negative Security Test** — screenshot 1 unauthorized access attempt bị denied.
8. **Bonus** (tùy chọn) — nếu các bạn thử 1 real-world ops scenario từ Bonus section bên dưới, document ở đây với pre/post screenshots, timings, và reflection.

**Trainer chấm IV theo file này như thế nào:**
- Không có Evidence Pack → IV cap 2.
- Chỉ screenshots, không notes → IV cap 3.
- Tất cả acceptance criteria có screenshots + notes có ý nghĩa + working query evidence → IV 4.
- Tất cả cái trên CỘNG 1 bonus scenario chạy được với measurements và reflection → IV 5.

Slides thứ Sáu phải link ngược lại commit của markdown. "Em sẽ show diagram" mà không có linked markdown file sẽ cap IV ở 3 — trainer cần verify được claims của các bạn sau khi rời phòng.

---

## Bonus — Real-World Ops Scenarios (Tùy Chọn)

Hoàn thành tất cả must-haves và Evidence Pack rồi? Đi xa hơn. Bonus work được điểm tối đa **+0.5 vào điểm W3** — và point của bonus này là trải nghiệm những gì một database engineer thật sự làm sau khi database được deploy: failovers, restores, migrations, engine swaps, upgrades. Chọn 1 scenario từ menu bên dưới HOẶC tự propose (check với trainer trước).

**Mọi bonus scenario phải được document trong section 8 của Evidence Pack:**
- Pre-state screenshot (mọi thứ trông thế nào trước)
- Action taken (console step, CLI command, hoặc CFN change)
- Post-state screenshot (mọi thứ trông thế nào sau)
- Measurement (khi applicable — downtime seconds, migration duration, row/item counts trước vs sau)
- 2-3 câu reflection: các bạn học được gì, cái gì bất ngờ, lần sau sẽ làm khác gì.

### A. Ops Drill Scenarios (gần production work thật nhất)

- **RDS Multi-AZ Failover Drill** — dùng `Reboot with failover` trong RDS console. Đo xem app thấy connection errors bao lâu. Document downtime.
- **Point-in-Time Restore** — restore managed DB của bạn (RDS/Aurora/DynamoDB/DocumentDB) về timestamp 5-10 phút trước. Self-hosted equivalent: restore từ AMI snapshot + replay logs. Show restored data.
- **On-Demand Backup → Restore** — take manual snapshot (RDS) hoặc on-demand backup (DynamoDB), restore vào name mới, verify từng row/item đến nơi.
- **Read Replica Promotion** — tạo RDS Read Replica, rồi promote nó thành standalone và show accept writes.
- **Engine Minor Version Upgrade** — upgrade RDS/Aurora version (hoặc đổi DynamoDB capacity mode) không mất data.
- **Zero-Downtime Schema Change** — add column (RDS) hoặc GSI (DynamoDB) trong khi writes đang xảy ra. Show không có errors trong app logs.

### B. Migration Scenarios (multi-hour effort, high learning value)

- **RDS MySQL → Aurora MySQL** — migrate qua snapshot restore hoặc Aurora read replica promotion. Show row counts match.
- **MongoDB → DocumentDB** — export small MongoDB dataset (local Docker OK), import vào DocumentDB qua DMS hoặc mongodump/mongorestore. Show document counts match.
- **Oracle hoặc SQL Server → PostgreSQL** — DMS + SCT cho schema conversion. Show SCT report và 1 test query chạy cả 2 bên.
- **DynamoDB Table Redesign** — export DynamoDB table đang có ra S3, re-import vào table mới với partition key design tốt hơn. Show tại sao redesign quan trọng.
- **DynamoDB ↔ DocumentDB** — engine swap thật sự nếu access pattern đã evolved. Yêu cầu 1 đoạn giải thích tại sao engine change hợp lý.

### C. Platform / Tooling Bonuses

- **Partial CloudFormation template** — Viết partial CFN template hợp lệ syntax, provision ít nhất 1 W3 resource tùy chọn (VPC, RDS DB instance, DynamoDB table, hoặc Lambda function). Template phải pass `aws cloudformation validate-template`. Document validate output + snippet + git commit vào section 8 của Evidence Pack. **+0.25**
- **Bedrock Agent với Action Groups** — agent gọi Lambda action group để query database bằng natural language.
- **DynamoDB Streams + Lambda fan-out** — preview cho W4 data pipeline pattern.
- **CI/CD pipeline** — CodePipeline hoặc GitHub Actions validate + deploy CFN template khi commit. **+0.5**
- **DAX caching** — DAX cluster trước DynamoDB với latency comparison.
- **Niche database** — Neptune, Timestream, hoặc ElastiCache cho 1 real sub-use-case, với justification.
- **Full CloudFormation coverage** — tất cả W3 infrastructure trong 1 working CFN stack. **+0.5**

### Bonus Scoring

| Chất lượng evidence | Điểm |
|---------------------|------|
| Working scenario + pre/post screenshots + measurement + reflection | **+0.5** |
| Working scenario + screenshots nhưng không có measurement hoặc reflection | **+0.25** |
| Attempted nhưng không working, hoặc không có screenshots | **+0.0** |

Bonus chỉ được chấm nếu cả 4 must-haves VÀ Evidence Pack complete. Được làm nhiều bonus nhưng tổng điểm cap ở +0.5 — 1 scenario làm tốt ăn 3 scenarios làm sloppy.

---

## "Done" Trông Thế Nào Vào Thứ Sáu

Trước khi present, **post commit link Evidence Pack** (`docs/W3_evidence.md`) vào trainer Slack channel. Không post link = Criterion IV pre-flagged ở cap 2 trước cả khi bắt đầu.

Nhóm của các bạn present thứ Sáu trong 4 phần, tổng 10-12 phút. **Tất cả slides derive từ Evidence Pack markdown** — mở markdown 1 lần ở đầu và treat slides như reading order qua nó.

**Part 1 — W2 Recap (1.5 phút):** Show diagram W2. Kể tên 1 lesson cụ thể từ feedback trainer tuần trước và show cách W3 build lên trên đó.

**Part 2 — W3 Architecture (3 phút):** Walk qua diagram đã update. Show cả 4 must-have components. Walk Data Access Pattern Log: 3 access patterns, engine nào phục vụ cái nào và tại sao, và "wrong-paradigm" test. (Slides cho part này derive từ Evidence Pack sections 2 + 6.)

**Part 3 — Individual Q&A (3 phút):** 2-3 thành viên trong team sẽ được hỏi câu hỏi về architecture và decisions. Đây là câu hỏi về những gì các bạn build và tại sao. Nếu các bạn hiểu việc của chính mình, sẽ handle được tự tin.

**Part 4 — Live Demo (3-4 phút):** Show acceptance criteria live. Nếu bất kỳ live action nào break, Evidence Pack screenshot của cùng action đó thay thế được (không phạt) — nhưng thiếu CẢ live VÀ screenshot cho cùng 1 claim cap IV ở 2. Những gì cần show:
- Data được write và read từ engine đã chọn, với 2 representative operations match với paradigm:
  - Relational: 1 JOIN qua 2 related tables + 1 indexed lookup
  - Key-Value: 1 Query theo partition key + 1 GSI query (không Scan)
  - Document: 1 aggregation pipeline + 1 indexed-field lookup
  - Graph: 1 traversal + 1 property/node lookup
  - backed by Evidence Pack section 4
- Bedrock Knowledge Base trả về retrieval result (không phải Playground — API call thật) — backed by Evidence Pack section 5
- Lambda function được trigger với output thấy được trong CloudWatch Logs — backed by Evidence Pack section 5
- 1 negative test: unauthorized access attempt tới database bị denied — backed by Evidence Pack section 7

---

## Tại Sao Tuần Này Quan Trọng

Mọi role AWS architecture đều hỏi về databases. Các bạn chọn service nào? Tại sao? Thiết kế data model thế nào? Secure ra sao?

Mọi interview serverless đều hỏi về Lambda. Function của bạn trigger bởi gì? Scope IAM role thế nào?

Sau tuần này, các bạn sẽ có câu trả lời thật — built bởi chính tay mình, chạy trên AWS infrastructure thật, và documented đủ kỹ để một reviewer không có mặt trong phòng vẫn verify được từng claim.

W2 đã chứng minh các bạn deploy được AWS infrastructure. W3 chứng minh các bạn deploy được deeper services, configure chúng đúng, và show evidence — discipline các bạn sẽ cần mỗi tuần từ đây trở đi.

---

## Bắt Đầu Vào Thứ Hai

Trước khi provision gì, mở diagram W2 cùng team và trả lời:

1. App cần lưu data gì? List ra: users, products, orders, events, bất cứ thứ gì applicable.
2. Với mỗi loại data: có relationships không? 3 query phổ biến nhất là gì? (Đây trở thành Part A của Data Access Pattern Log.)
3. Dựa vào câu trả lời trên: paradigm nào (relational / key-value / document / graph), và rồi engine nào trong paradigm đó (managed hay self-hosted)? Chọn worked example gần nhất ở trên làm neo.
4. Trong VPC chúng nằm ở đâu? Cần Security Group rules gì?

Thống nhất 4 điểm này trước khi ai đó bắt đầu provision. Một database với data model sai tốn nhiều thời gian hơn để fix hơn là thời gian đã làm sai.

---

Chúc may mắn. Đến thứ Sáu, app của các bạn sẽ có xương sống.
