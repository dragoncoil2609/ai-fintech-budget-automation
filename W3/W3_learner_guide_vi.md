# Tuần 3 — Database, AI Agents & Network: Xây Bộ Não Cho App Của Bạn

## Tuần này các bạn sẽ học gì

App W2 của các bạn đã có storage và identity. Tuần này các bạn thêm "bộ não" cho nó. Các bạn sẽ thêm database layer thật sự (chọn giữa SQL và NoSQL dựa trên data của mình), kết nối Amazon Bedrock Knowledge Bases để app có AI, và xây dựng nền tảng network gắn kết mọi thứ một cách an toàn. Các bạn cũng sẽ viết Lambda function đầu tiên và CloudFormation template đầu tiên — hai kỹ năng xuất hiện trong mọi job description của Cloud Engineer.

Đến thứ Sáu, kiến trúc của các bạn sẽ có RDS database, DynamoDB table, Bedrock Knowledge Base kết nối với S3 data của W2, và Lambda function làm cầu nối giữa app tier và AI layer. Đây chính là hình dáng của một production application thật sự.

**Tuần này trọng tâm dịch chuyển khỏi W2 ở đâu — và cái gì từ W2 phải fix:**

Tuần này củng cố và đào sâu 3 mảng mà W2 đã chạm qua rồi: database layer (engine thực sự — RDS + DynamoDB — không còn dùng S3 như flat storage), AI integration layer (Bedrock Knowledge Base kết nối tới S3 bucket, vượt qua one-shot prompt), và serverless compute layer (Lambda làm glue giữa các service). Cả tuần xoay quanh 3 thứ này — không phải concept hoàn toàn mới, mà là những thứ các bạn sẽ hardening thành production-grade component.

W2 cũng để lại 3 gap phổ biến mà diagram W3 phải sửa. Trước khi đào sâu 3 layer này, hãy fix những điểm này trên diagram hiện tại:
- **Thiếu encryption labels** — diagram bây giờ phải show encryption at rest trên RDS, DynamoDB, và bất kỳ S3 bucket hoặc EBS volume nào chưa được label ở W2
- **IAM policies quá rộng** — siết chặt mọi wildcard permission trên Lambda hoặc EC2 role về least-privilege, chỉ định cụ thể resource ARN
- **S3 traffic đi qua NAT Gateway** — thêm VPC Gateway Endpoint cho S3 vào private subnet để S3 calls ở trên AWS backbone và không mất phí per-GB NAT processing

Ba điểm fix này trainer sẽ kiểm tra vào thứ Năm và trong QnA thứ Sáu.

---

## Focus Areas

### Thứ Hai — Generative AI Foundations + Database Survey

**Courses trong ngày** (từ syllabus):
- Multi-Agent Collaboration with Amazon Bedrock Agents (1 hr, Digital Course) — Essential
- Build with Amazon S3 Vectors and Amazon Bedrock Knowledge Bases (1 hr, Digital Course) — Essential
- AWS SimuLearn: Explore the Amazon Bedrock Playgrounds (1 hr, Lab) — Recommended
- AWS Database Offerings (4 hrs, Digital Course) — Essential (tập trung vào RDS, DynamoDB, ElastiCache; các service khác chỉ cần ở mức tổng quan)

**Chủ đề chính**: Bedrock Agents (multi-agent patterns, action groups, knowledge bases) — S3 Vectors và RAG pipelines — AWS Database Offerings survey (RDS, DynamoDB, ElastiCache, Neptune, Timestream)

**Những gì cần chú ý:**
- **Cấu tạo của một Bedrock Agent.** Có 4 bộ phận chuyển động: Foundation Model (bộ não), Instructions (nó nên làm gì), Action Groups (nó làm được gì — được hỗ trợ bởi Lambda functions), và Knowledge Bases (nó biết những gì — được hỗ trợ bởi documents trong S3 của bạn). Hãy vẽ ra giấy trước khi đi tiếp.
- **Khác biệt giữa Retrieve và RetrieveAndGenerate.** Retrieve trả về các đoạn text liên quan. RetrieveAndGenerate gọi FM và trả về một câu trả lời đã được tổng hợp. Phần lớn application dùng RetrieveAndGenerate.
- **Decision table cho database type.** Các bạn không cần nhớ cả 8 loại database — các bạn cần biết khi nào dùng RDS/Aurora (relational, joins, transactions) vs DynamoDB (scale, flexible schema, low-latency key lookups) vs ElastiCache (microsecond in-memory cache cho hot data) vs DocumentDB (document store, aggregation pipelines) vs Neptune (graph traversals). Quyết định này sẽ được hỏi trong QnA thứ Sáu.

**Lựa chọn project là mở.** Thứ Hai dạy RDS như ví dụ canonical của relational engine, nhưng lựa chọn database cho project của team là open-ended. Các bạn có thể dùng bất kỳ AWS-managed database nào (RDS, Aurora, DynamoDB, DocumentDB, Neptune) HOẶC self-host một engine trên EC2 (Postgres, MySQL, MongoDB, v.v.) — miễn là lựa chọn khớp paradigm của data (relational, key-value, document, hoặc graph) và các bạn document được lý do. RDS không phải là lựa chọn project duy nhất hợp lệ; nó chỉ là cái mà thứ Hai dạy.

**Hands-on tips:**
- Trong Bedrock Playground SimuLearn, thử Chat Playground và test system prompts. Gán cho model một persona ("You are a cloud cost optimization advisor") và xem response thay đổi thế nào. Đây là cách gần nhất để cấu hình một Bedrock Agent mà Playground cho phép.
- Khi đi qua Database Offerings course, dừng lại ở mỗi database type và tự hỏi: "Cái này có thể fit vào đâu trong 3-tier project của team mình?" Đừng chỉ xem — hãy annotate vào notes.

---

### Thứ Ba — DynamoDB và RDS Chuyên Sâu + VPC Architecture

**Courses trong ngày** (từ syllabus):
- Amazon DynamoDB Getting Started (1 hr, Digital Course) — Essential
- Amazon RDS Service Primer (20 min, Digital Course) — Essential
- AWS SimuLearn: Databases in Practice (1 hr, Lab) — Essential
- AWS SimuLearn: First NoSQL Database (1 hr, Lab) — Essential
- AWS Networking Basics (2 hrs, Digital Course) — Essential
- Subnets, Gateways, and Route Tables Explained (17 min, Digital Course) — Essential
- Understanding AWS Networking Gateways (30 min, Digital Course) — Essential
- Introduction to Amazon API Gateway (10 min, Digital Course) — Recommended (sẽ đi sâu hơn ở W5)

**Chủ đề chính**: DynamoDB (partition keys, GSIs, Query vs Scan, DAX) — RDS (Multi-AZ, Read Replicas, RDS Proxy) — VPC subnets, route tables, Internet Gateway, NAT Gateway, Transit Gateway — API Gateway types và integration với Lambda

**Những gì cần chú ý:**
- **Thiết kế DynamoDB partition key.** Partition key là cách DynamoDB quyết định item nằm ở physical storage partition nào. Nếu quá nhiều item dùng chung 1 partition key value, writes sẽ dồn vào 1 partition và bị throttle. Chọn attribute có nhiều distinct values — user IDs, order IDs, session tokens là lựa chọn tốt. Status codes ("active"/"inactive") là lựa chọn xấu.
- **RDS Multi-AZ vs Read Replicas.** Hai thứ này giải quyết hai vấn đề khác nhau. Multi-AZ cho high availability — synchronous standby instance tự động take over khi primary fail, **nhưng nó không phục vụ reads**. Read Replicas là asynchronous copies phục vụ read traffic; chúng **không giúp failover**. Các bạn có thể dùng cả hai cùng lúc.
- **VPC routing.** Một subnet là "public" khi và chỉ khi route table của nó có route gửi traffic `0.0.0.0/0` tới một Internet Gateway. Subnet là "private" khi route đó đi tới một NAT Gateway. Subnet "isolated" không có internet route nào cả (đúng cho database tier của các bạn).

**Lựa chọn project là mở (tiếp).** Thứ Ba dạy DynamoDB như ví dụ canonical của key-value engine. Các bạn học 2 paradigm relational và key-value qua RDS + DynamoDB vào thứ Hai/thứ Ba — rồi áp dụng tư duy paradigm vào lựa chọn engine của team. Nếu data fit với document hoặc graph paradigm, DocumentDB hoặc Neptune là project picks hợp lệ. Nếu áp lực cost đẩy team đi self-host trên EC2, điều đó cũng hợp lệ — với backup + HA plan đã document.

**Hands-on tips:**
- Trong lab DynamoDB First NoSQL Database, sau khi viết vài items, thử chạy cả Query (cần partition key) và Scan (đọc hết). Để ý sự khác biệt ở "Items examined" — đây là thứ quyết định cost.
- Trong lab RDS Databases in Practice, check Multi-AZ setting khi provision instance. Bật nó lên và xem có gì thay đổi. Nếu lab cho phép simulated failover, trigger nó và quan sát endpoint behavior.

---

### Thứ Tư — VPC Labs, Security Groups vs NACLs, Lambda, CloudFormation

**Courses trong ngày** (từ syllabus):
- AWS SimuLearn: Networking Concepts (1 hr, Lab) — Essential
- Differences Between Security Groups and NACLs (10 min, Digital Course) — Essential
- AWS Lambda Foundations (2 hrs, Digital Course) — Essential
- Introduction to AWS Lambda (1 hr, Lab) — Essential
- Getting Started with AWS CloudFormation (1 hr, Digital Course) — Essential

**Chủ đề chính**: Multi-tier VPC lab (public/private/database tiers) — Security Groups vs NACLs — Lambda (execution model, S3 triggers, cold starts, CloudWatch Logs) — CloudFormation (template structure, intrinsic functions, change sets)

**Những gì cần chú ý:**
- **Security Groups vs NACLs.** Security Groups là **stateful** — khi traffic đi vào, return traffic tự động được cho phép (SG nhớ connection). NACLs là **stateless** — phải explicit allow cả inbound và outbound cho mỗi flow. Security Groups chỉ có Allow rules. NACLs có cả Allow và Deny. Security Groups áp dụng cho từng instance; NACLs áp dụng cho cả subnet.
- **Lambda invocation types.** S3 trigger Lambda là **asynchronous** — S3 fire event rồi đi, Lambda xử lý ở background. Nếu function fail, Lambda tự động retry. API Gateway trigger Lambda là **synchronous** — caller đợi response. Invocation type quyết định retry behavior.
- **CloudFormation intrinsic functions.** `!Ref` trả về primary identifier của resource (ví dụ: tên của bucket). `!GetAtt` trả về attribute cụ thể (ví dụ: `!GetAtt MyBucket.Arn` trả về ARN). Lỗi mọi người đều mắc: dùng `!Ref` mà nghĩ nó trả ARN.

**Hands-on tips:**
- Trong VPC networking lab, sau khi build 3-tier VPC, thử gửi test request từ public subnet sang private app subnet. Nếu fail, check security group rules — tier nào là source, tier nào là destination?
- **W2 fix cần làm trong lab này**: thêm VPC Gateway Endpoint cho S3 vào route table của private subnet. Cái này route S3 traffic trực tiếp qua AWS network thay vì qua NAT Gateway. Free, và loại bỏ khoản phí per-GB mà phần lớn W2 architectures đang âm thầm tính tiền.
- Trong Lambda lab, sau khi tạo function và setup S3 trigger, upload 1 test file lên S3, rồi vào ngay CloudWatch Logs tìm log group của function. Nhìn function của chính mình phản ứng với event thật là khoảnh khắc Lambda "click" trong đầu.
- CloudFormation: bắt đầu đơn giản. Tạo YAML template với đúng 1 resource — 1 S3 bucket. Deploy như một stack. Rồi thêm resource thứ 2 và update stack bằng change set trước. Build confidence trước khi thêm complexity.

---

### Thứ Năm — Review & Prep Day

Dùng thứ Năm để consolidate những gì đã học từ thứ Hai đến thứ Tư.

**Buổi sáng**: Trainer sẽ review các misconception hàng đầu từ checkpoint games tuần này. Chú ý kỹ nếu thảo luận về DynamoDB partition key design, khác biệt RDS Multi-AZ vs Read Replica, hoặc Lambda cold starts — đây là 3 chủ đề hay bị hiểu sai nhất tuần này.

**Group activity**: Update W2 architecture với database và AI layers của W3. Làm theo thứ tự:

**Step 0 — Fix W2 gaps trước (làm cái này trước khi thêm bất cứ cái gì mới):**
- Thêm encryption labels cho các storage component còn thiếu: S3 (SSE), EBS, và bây giờ RDS (storage encryption) và DynamoDB (SSE). Trainer sẽ check.
- Siết IAM policies: thay mọi wildcard permission trên Lambda hoặc EC2 role bằng least-privilege statements chỉ định action cụ thể và resource ARN cụ thể.
- Thêm VPC Gateway Endpoint cho S3 vào route table của private subnet (nếu còn thiếu ở W2).

**Step 1 — Chọn database đúng cho YOUR data và deploy:**

Rule tuần này: lựa chọn database cho project là **mở**. Chọn engine + paradigm khớp với pattern data thật của team. Các option:

- **AWS-managed relational** — RDS (Postgres, MySQL, MariaDB, SQL Server), Aurora (Postgres/MySQL)
- **AWS-managed key-value** — DynamoDB
- **AWS-managed document** — DocumentDB (MongoDB-compatible)
- **AWS-managed graph** — Neptune
- **Self-hosted trên EC2** — Postgres, MySQL, MongoDB, hoặc tương tự, kèm ops plan đã document

Một nhóm chọn 1 engine tốt và biện hộ chắc chắn sẽ có điểm cao hơn nhóm bolt-on 2 engine mà không biện hộ được.

Decision shortcut (4 paradigms):
- Data có relationships (users → orders → items) và cần JOINs, hoặc cần all-or-nothing transactions (payments, inventory) → **relational paradigm** (RDS/Aurora, hoặc self-hosted Postgres/MySQL).
- Data được lookup theo known key ở scale lớn (session, event, device reading), HOẶC cần >1,000 writes/sec với predictable single-key access → **key-value paradigm** (DynamoDB).
- Data là semi-structured, nested documents (product catalog với attributes biến động, user profiles với flexible fields, content CMS) và query bằng aggregation pipelines / indexed fields → **document paradigm** (DocumentDB, hoặc self-hosted MongoDB).
- Data nặng về relationship (social graph, recommendation network, fraud ring detection) và cần traverse nhiều hops → **graph paradigm** (Neptune).

Rồi deploy thứ đã chọn. Rules chung cho mọi engine: private subnet (không public), SG khóa về app tier (không `0.0.0.0/0`), encryption at rest, và HA/backup plan.

- **Nếu relational (RDS/Aurora):** private DB subnet, DB subnet group trải qua 2 AZs, encryption at rest, automated backups 7+ ngày, SG inbound chỉ từ app-tier SG. Schema có ít nhất 2 related tables với foreign key. Label engine + Multi-AZ decision.
- **Nếu key-value (DynamoDB):** high-cardinality partition key (user_id, order_id, device_id — **không bao giờ** `status` hay `active`), on-demand HOẶC provisioned-with-auto-scaling, encryption on, primary access pattern dùng **Query** (không phải Scan). Nếu có access pattern thứ 2, thêm composite sort key hoặc GSI.
- **Nếu document (DocumentDB / self-hosted MongoDB):** private subnet, encryption at rest, có ít nhất 1 indexed field cover primary lookup pattern (không full-collection scan), replica set hoặc Multi-AZ. **Cost note**: DocumentDB minimum instance ~$200/tháng — include monthly cost estimate và confirm budget. Self-hosted MongoDB: document backup + replica strategy.
- **Nếu graph (Neptune):** private subnet, encryption at rest, node + edge schema rõ ràng (cái gì là vertex, cái gì là relationship), Multi-AZ hoặc read replica. **Cost note**: Neptune minimum instance ~$200/tháng — include monthly cost estimate.
- **Nếu self-hosted trên EC2:** private subnet, SG khóa, EBS encryption on. Phải document: (1) backup plan (snapshot cadence, đã test restore chưa?), (2) HA plan (standby EC2 + replication? Multi-AZ snapshot? cold restore chấp nhận được?), (3) lý do trade-off (tại sao self-host thay vì managed — cost, engine version cụ thể, license, v.v.). Trainer cần review sớm hơn các nhóm dùng managed service — loop trainer vào early review trước Wednesday EOD.
- **Nếu nhiều engine:** đáp ứng requirement của từng engine và sẵn sàng show query nào đi vào paradigm nào. Chọn nhiều mà không có data-pattern justification sẽ điểm thấp hơn 1 lựa chọn được biện hộ tốt.

**Step 2 — Thêm AI integration layer:**
- Thêm Bedrock Knowledge Base kết nối với S3 bucket từ W2. Vẽ mũi tên từ app tier → qua Lambda function → tới Knowledge Base → tới FM.
- Label Lambda function's IAM execution role và đặt tên cụ thể các permission nó cần.

**Step 3 — Viết Data Access Pattern Log** (tối đa 1 trang, slides cũng được — bắt buộc; thiếu cái này MH1 không quá được 3 điểm). Ba phần:
- **Part A**: List 3 access pattern phổ biến nhất trong app của team (mỗi cái 1 câu + frequency ước lượng, ví dụ: "Lấy tất cả orders của một user, sort theo ngày — ~50 calls/phút lúc peak"). Đây là query thật từ user flow W1/W2.
- **Part B**: Với mỗi pattern, đặt tên engine + paradigm phục vụ nó và mechanism cụ thể — index / partition key + sort key / GSI / aggregation pipeline với indexed field / graph traversal — nào làm query hiệu quả **không cần full scan**. Nếu chọn DocumentDB/Neptune/self-hosted, kèm 1 dòng cost estimate (~$/tháng) hoặc ops note (backup/HA plan). "Scan toàn bộ" không bao giờ là câu trả lời đúng cho một frequent query.
- **Part C — "wrong-paradigm" test**: chọn 1 pattern và giải thích trong 2-3 câu cái gì sẽ break hoặc cost quá cao nếu một paradigm KHÁC phục vụ nó. Ví dụ: "Một relational engine ở 10k writes/sec cần sharding"; "Một key-value store không trả lời được join này nếu không duplicate data vào mọi item"; "Eventual consistency trên DDB GSI có thể show stale balance"; "Ép graph query vào document paradigm cần N+1 lookup mỗi hop"; "Một document store không có indexed field trên `user_id` sẽ scan toàn collection." Đây là cách các bạn chứng minh đã thật sự hiểu lựa chọn — nhóm skip Part C sẽ cap MH1 ở 3.

Sáu ví dụ mẫu để neo vào (cover cả 4 paradigms):
1. **E-commerce** (users/products/orders có FKs, "place an order = 1 transaction") → **relational** (RDS/Aurora SQL transaction all-or-nothing; một key-value store cần TransactWriteItems + GSI cho order history).
2. **IoT telemetry** (10k devices × 1 event/sec, "events for device X trong giờ qua") → **key-value** (DynamoDB PK=device_id, SK=timestamp; một relational engine ở write rate này cần sharding + queue).
3. **Chat/messaging** ("load 50 messages gần nhất trong conversation X") → **key-value single-table** (DynamoDB PK=CONV#id, SK=MSG#timestamp; một relational engine cũng được nhưng messages table sẽ phình lên hàng tỷ rows và pagination đắt).
4. **Banking ledger** ("transfer $100 từ A sang B, atomically hoặc không gì cả") → **relational** ACID transaction (key-value eventual consistency có thể show stale balance giữa debit và credit — không chấp nhận cho tiền).
5. **Content CMS với flexible product attributes** ("lấy tất cả products trong category X với `discounted=true` và `region=APAC`") → **document** (DocumentDB với compound index trên `category + flags`; ép vào relational schema có nghĩa là sparse columns cho mọi attribute khả dĩ hoặc bảng EAV, cả hai đều cồng kềnh).
6. **Social recommendation** ("tìm friends-of-friends của user X đã like product Y") → **graph** (Neptune 2-hop traversal; relational engine cần recursive self-joins; key-value store cần N+1 round trips mỗi hop).

Log của các bạn không cần copy một trong số này, nhưng phải đạt mức specificity tương đương — và phải đặt tên paradigm rõ ràng, không chỉ tên engine.

Submit diagram đã update và Data Access Pattern Log vào trainer Slack channel trước 17:00 thứ Năm.

---

### Thứ Sáu — Show What You Know

Mỗi nhóm present 4 phần (~10-12 phút tổng):

1. **Part 1 — W2 Recap & Reflection (~1.5 phút)**: show diagram W2, kể tên một feedback cụ thể của trainer, và show cụ thể cách W3 addresses nó. Cụ thể > chung chung.
2. **Part 2 — W3 Architecture (~3 phút)**: show diagram đã update. Phải bao gồm: database engine đã chọn + paradigm placed đúng chỗ cho paradigm đã pick — relational (RDS/Aurora/self-hosted) trong private DB subnet với Multi-AZ hoặc equivalent HA labeled và 2 related tables + FK; HOẶC key-value (DynamoDB) với high-cardinality partition key và sort key/GSI nếu cần; HOẶC document (DocumentDB/self-hosted MongoDB) với indexed collection schema và replica/HA plan; HOẶC graph (Neptune) với node + edge schema; HOẶC nhiều engine với phân chia rõ. Self-hosted engine show backup + HA plan trên diagram hoặc slide bên cạnh. Walk qua Data Access Pattern Log: 3 patterns, engine + paradigm + mechanism cho mỗi cái, và wrong-paradigm test. Cũng show Bedrock Knowledge Base RAG flow và Lambda function với named execution role.
3. **Part 3 — Individual QnA (~3 phút)**: 2-3 thành viên được gọi tên. Mọi người đều có thể bị pick — cả team sở hữu design.
4. **Part 4 — Deployment / Live Demo (~3-4 phút)**: show engine đã chọn chạy live với 1 operation thật sự exercise paradigm của team:
   - **Relational** (RDS/Aurora/self-hosted Postgres/MySQL): chạy 1 JOIN query qua 2 related tables, trả về rows thật.
   - **Key-value** (DynamoDB): chạy 1 Query call (không phải Scan) dùng partition key và show items trả về trong <10ms.
   - **Document** (DocumentDB/self-hosted MongoDB): chạy 1 aggregation hoặc `find()` trên indexed field (show `explain()` xác nhận index được dùng, không phải full COLLSCAN).
   - **Graph** (Neptune): chạy 1 traversal query (Gremlin/SPARQL) đi qua ít nhất 1 edge và trả về vertices.

   Trigger Lambda function qua S3 upload và show CloudWatch Logs. Kết thúc bằng 1 negative security test (denied access attempt). Nếu team các bạn làm CloudFormation bonus, có thể show thêm `aws cloudformation validate-template` output ở đây. **Mọi slide trong Part 4 đều derive từ Evidence Pack markdown của các bạn** — mở file markdown ở đầu Part 4 và link slides về latest commit để trainer có thể re-verify sau khi rời phòng. Nếu live action break trong demo, screenshot trong Evidence Pack của action đó thay thế được (không phạt) — nhưng thiếu CẢ live VÀ screenshot = Criterion IV cap ở 2.

Đảm bảo demo khớp với diagram VÀ Evidence Pack. Những gì vẽ trên architecture nhưng chưa deploy phải xóa khỏi diagram trước thứ Sáu. Những gì trong Evidence Pack nhưng thiếu trên diagram cũng là vấn đề tương đương.

---

## Deliverables Tuần Này

Team của các bạn phải nộp vào thứ Sáu:

1. **Architecture diagram đã update** — show các W3 additions: database engine đã chọn placed đúng chỗ cho paradigm đã pick (relational trong private DB subnet với Multi-AZ decision labeled; key-value với partition key có tên và sort key/GSI nếu dùng; document với indexed collection + replica/HA plan; graph với node + edge schema; self-hosted engine với backup + HA plan annotated), Bedrock Knowledge Base + RAG flow vẽ với Lambda làm connector, 3-tier VPC đầy đủ với VPC Gateway Endpoint cho S3; cộng với W2 gap fixes: encryption at rest labeled trên mọi storage, IAM policies siết về least-privilege.

2. **Evidence Pack — `docs/W3_evidence.md` trong repo của team** (bắt buộc, được chấm điểm — đây là deliverable quan trọng nhất tuần). Một file markdown duy nhất đóng vai trò source of truth. Slides thứ Sáu của các bạn **derive từ file này** — copy 8-12 screenshots + captions từ markdown vào slides, present slides, và link ngược lại commit của markdown. Đừng viết slides trước rồi viết markdown sau. Required sections:
   - **(1) Cover** — group, members, engine + paradigm choice
   - **(2) Data Access Pattern Log** Parts A/B/C
   - **(3) Deployment Evidence** — mỗi acceptance criterion 1 entry với console screenshot hoặc CLI output CỘNG 1-2 dòng notes ("we configured X this way because Y", không phải chỉ "encryption enabled")
   - **(4) Working Query Evidence** — 1 operation phù hợp paradigm (relational JOIN / key-value Query / document aggregation với `explain()` show index được dùng / graph traversal)
   - **(5) Lambda + Bedrock Evidence** (CloudWatch log + Bedrock API response từ Lambda/CLI — không phải Playground)
   - **(6) VPC + Networking Evidence** (route table show S3 Gateway Endpoint + DB SG inbound rule)
   - **(7) Negative Security Test** (denied access screenshot)
   - **(8) Bonus** (tùy chọn — nếu các bạn làm CloudFormation bonus, để `validate-template` output + intrinsic function snippet + git commit link ở đây)

   Các nhóm self-hosted và DocumentDB/Neptune cần kèm thêm cost-or-ops note (monthly estimate cho managed premium engine; backup + HA plan cho self-hosted).

3. **Live demo readiness** — engine đã chọn chạy live với 1 operation phù hợp paradigm (relational: JOIN qua 2 related tables; key-value: Query — không phải Scan — trả về items qua partition key; document: 1 aggregation hoặc `find()` hit indexed field; graph: 1 traversal đi qua ít nhất 1 edge), Lambda function tạo CloudWatch Logs khi bị trigger bởi S3 upload. Mỗi live action phải có screenshot tương ứng trong Evidence Pack để trainer có thể re-verify sau thứ Sáu.

---

## Các Bạn Sẽ Được Đánh Giá Thế Nào

- **Rubric weights thay đổi tuần này**: W2 Recap & Reflection (10%), AWS Architecture (20%), Individual QnA (30%), **Deployment & Evidence (40%)**. Chất lượng diagram ít quan trọng hơn những gì thật sự được deploy và document — Criterion IV giờ là phần lớn nhất trong điểm, và được chấm gần như hoàn toàn dựa vào Evidence Pack markdown.
- **Criterion IV (40%) được chấm thế nào**: Không có Evidence Pack → cap ở 2. Chỉ screenshots, không notes → cap ở 3. Tất cả acceptance criteria được cover với screenshot + notes có ý nghĩa + working query evidence → 4. Tất cả cái trên CỘNG một bonus scenario chạy được với measurements và reflection → 5. Slides không có linked markdown commit cũng cap ở 3 — trainer cần một file có thể re-verify sau thứ Sáu.
- **Những thứ cụ thể W3 sẽ bị check**: Các bạn đã fix W2 encryption và IAM gaps chưa? Đã chọn đúng paradigm cho data và chứng minh bằng wrong-paradigm test chưa? Nếu relational: có nằm trong private subnet không, 2 related tables với FK, Multi-AZ (hoặc equivalent HA) decision đã stated? Nếu key-value: partition key có high-cardinality không, primary access pattern có dùng Query (không phải Scan)? Nếu document: lookup field có được index không (không COLLSCAN), replica/HA plan đã có chưa? Nếu graph: node + edge schema đã document chưa? Nếu self-hosted: backup + HA đã document và trainer đã review trước Wednesday EOD chưa? Lambda có named execution role đàng hoàng không? Mỗi acceptance criterion có screenshot + note trong Evidence Pack không?
- **Individual QnA**: Khả năng giải thích database design decisions, Lambda invocation model, VPC structure, và W2 gap corrections khi bị gọi tên — accuracy, reasoning, và confidence đều quan trọng. Mọi thành viên đều có thể bị pick — cả team phải sở hữu các decision.
- **Daily checkpoints**: Kahoot, Blooket, và Quizlet Live games từ thứ Hai đến thứ Tư đều tính điểm.
- **Peer evaluation**: Đồng đội đánh giá contribution của bạn mỗi tuần.

---

## Pro Tips

- **DynamoDB: nghĩ access patterns trước.** Trước khi chọn partition key, list tất cả query app sẽ chạy. Partition key phải làm cho query phổ biến nhất trở thành một `Query` operation có target, không phải `Scan` đắt đỏ.
- **Biết khác biệt Multi-AZ vs Read Replica thuộc lòng.** Khác biệt này xuất hiện trong hầu hết interview AWS. Multi-AZ = high availability (automatic failover, standby không serve reads). Read Replica = read scaling (asynchronous copy, serve reads, có thể promote nếu cần).
- **Lambda và IAM roles đi đôi.** Mỗi Lambda function cần IAM execution role. Role đó là thứ cho phép function gọi các AWS services khác. Không bao giờ hard-code credentials — assign role thay vì.
- **CloudFormation là IaC tool các bạn sẽ dùng bắt đầu từ W5** cho VPC peering và các tuần sau. Tuần này hãy practice bằng cách viết partial template cho 1 resource của W3 — đây là bonus +0.25 nếu các bạn include `validate-template` output + snippet + commit link vào Evidence Pack section 8. Học syntax bây giờ sẽ tiết kiệm thời gian khi nó trở thành bắt buộc sau này.
- **RAG không phải fine-tuning.** Bedrock Knowledge Base không retrain model. Nó gắn relevant text vào prompt tại thời điểm inference. Nếu answers kém, check chunking strategy và S3 data quality — đừng đổ lỗi cho model.

---

## Key AWS Services Tuần Này

| Service | Làm gì | Tại sao quan trọng cho project |
|---------|--------|--------------------------------|
| Amazon Bedrock Agents | Orchestrate AI tasks dùng Foundation Model, action groups, knowledge bases | Cung cấp AI-driven features cho app mà không cần build ML pipeline |
| Bedrock Knowledge Bases | Quản lý RAG pipeline: S3 data → embeddings → vector store → FM retrieval | Kết nối data của app (S3 từ W2) tới một AI answer engine |
| Amazon RDS | Managed relational database (Postgres, MySQL, MariaDB, SQL Server) với Multi-AZ, Read Replicas, automated backups | **Relational paradigm** — structured data với joins + transactions (orders, users, transactions). Ví dụ canonical của Monday. Pick khi data có relationships rõ và cần ACID. |
| Amazon Aurora | Cloud-native MySQL/Postgres-compatible relational engine với auto-scaling storage, failover nhanh hơn, và Aurora Serverless v2 | **Relational paradigm** — drop-in upgrade từ RDS khi cần performance tốt hơn hoặc feature riêng của Aurora (fast failover, Global Database). Cost cao hơn RDS một chút. |
| Amazon DynamoDB | Fully managed NoSQL key-value store với predictable single-digit millisecond performance | **Key-value paradigm** — high-velocity, flexible-schema data (sessions, events, app state). Ví dụ canonical của Tuesday. Pick khi lookup theo known key ở scale lớn. |
| Amazon DocumentDB | MongoDB-compatible managed document store với replica sets qua các AZ | **Document paradigm** — nested JSON documents với flexible attributes, aggregation pipelines, indexed-field lookups. Pick thay vì DynamoDB khi documents nested sâu hoặc cần MongoDB operators. Min instance ~$200/tháng — kèm cost estimate. |
| Amazon Neptune | Managed graph database (Gremlin, openCypher, SPARQL) | **Graph paradigm** — data nặng về relationship (social networks, fraud rings, recommendations) với multi-hop traversals. Min instance ~$200/tháng — kèm cost estimate. |
| Self-hosted DB trên EC2 | Chạy Postgres, MySQL, MongoDB, hoặc bất kỳ engine nào tự host trên EC2 instance | Bất kỳ paradigm — khi constraint cost/license/version làm managed service không phù hợp. Team tự lo backup, HA, patching, upgrades. Document ops plan và loop trainer vào trước Wednesday EOD. |
| DynamoDB DAX | In-memory cache cho DynamoDB, microsecond read latency | Optional: tăng tốc read-heavy DynamoDB workloads |
| ElastiCache for Redis | In-memory data store cho session caching và real-time leaderboards | Optional: khi cần sub-millisecond lookups từ app tier |
| Amazon VPC | Private network trong AWS với subnets, route tables, và gateways | Isolate 3 tiers; databases phải ở private subnets |
| AWS Lambda | Event-driven serverless compute trigger bởi S3, API Gateway, DynamoDB Streams | Connect app tier tới Bedrock, handle asynchronous data events |
| AWS CloudFormation | Infrastructure as Code — define tất cả AWS resources trong YAML/JSON template | Deploy toàn bộ stack lặp lại được; không còn manual console clicks |
| Amazon API Gateway | Managed API layer với throttling, auth, và integration với Lambda | Entry point cho REST API của app; connect frontend tới backend Lambda |
