# Tuần 4 — Xây Hệ Thống AI: Từ Retrieval Đến Reasoning

## Tuần này các bạn sẽ học gì

Tuần này các bạn xây một sản phẩm — hệ thống AI trả lời câu hỏi từ dữ liệu thật của một công ty. Câu hỏi khó dần: từ "tìm một fact trong tài liệu" đến "query dữ liệu live và tính toán" đến "nhớ những gì đã nói trước đó."

Đến thứ Sáu, nhóm phải có hệ thống chạy được và demo live. **Mục tiêu: L1-L3 hoạt động ổn định = 90% điểm.**

Tuần này các bạn ghép nhiều service lại thành một hệ thống hoàn chỉnh — S3 chứa tài liệu, Bedrock KB làm RAG, DynamoDB hoặc RDS chứa dữ liệu có cấu trúc, Lambda chạy tool functions, và Bedrock làm bộ não suy luận.

---

## Kiến thức trọng tâm

Tuần này về mặt AI/ML, các bạn sẽ được học về:

- AI fundamentals: traditional programming vs machine learning, cách model học từ data (training, weights, backpropagation, overfitting)
- Toàn cảnh AI/ML: supervised / unsupervised / reinforcement learning, các kiến trúc deep learning (CNN, RNN, Transformer, GAN), và con đường từ classical ML đến GenAI
- Cách LLM hoạt động: tokenization, embedding, attention mechanism, context window, temperature
- Các giới hạn cốt lõi của LLM và các pattern giải quyết
- Evaluation & trust: cách đánh giá output của AI
- AI safety & responsible AI

### AWS Services trọng tâm tuần này

| Service | Vai trò trong project |
|---------|----------------------|
| **Amazon S3** | Chứa 36 tài liệu knowledge base — data source cho RAG |
| **Bedrock Knowledge Bases** | RAG pipeline: S3 → chunking → embeddings → vector search → retrieval |
| **Amazon Bedrock (Claude)** | LLM sinh câu trả lời từ context + tool results |
| **Bedrock Agents** | (Tùy chọn) Managed tool use — agent quyết định khi nào retrieve vs gọi tool |
| **OpenSearch Serverless** | Vector store phía sau Bedrock KB — lưu embeddings, thực hiện similarity search. Không dùng trực tiếp nhưng là engine đứng sau mỗi lần retrieve |
| **DynamoDB** | Lưu conversation state cho L4 (memory) |
| **Database (RDS/Aurora/SQLite/DynamoDB)** | Chứa dữ liệu có cấu trúc (costs, incidents, SLA targets) cho L3 tool queries |
| **Lambda** | Chạy tool functions khi dùng Bedrock Agents — glue giữa LLM và data |

---

## Bức tranh tổng thể

Hệ thống có 3 nguồn dữ liệu. Hiểu data nằm Ở ĐÂU quyết định mọi thứ:

| Nguồn dữ liệu | Chứa gì | Cách truy cập | Dùng ở |
|----------------|---------|---------------|--------|
| **Knowledge base** (36 markdown docs) | Thông tin công ty, cấu trúc team, policies, postmortems, kiến trúc | RAG retrieval (vector search) | L1, L2 |
| **Database** (4 CSV files, seeded) | Chi phí chính xác, incident records, SLA targets, daily metrics | SQL queries qua tool functions | L3 |
| **Monitoring API** (Python script, chạy local) | Trạng thái live hiện tại, latency, error rate, request volume | HTTP calls qua tool functions | L3 |

**Key insight:** Knowledge base KHÔNG CÓ số tiền, KHÔNG CÓ daily metrics, KHÔNG CÓ trạng thái hệ thống hiện tại. Nếu câu hỏi yêu cầu số liệu hoặc dữ liệu live, tài liệu không trả lời được. Chỉ tools mới trả lời được.

---

## Lịch trình

| Ngày | Việc cần làm | Mục tiêu cuối ngày |
|------|-------------|-------------------|
| **Thứ Ba** | Đọc hết 36 docs. Chạy monitoring API. Seed database. Map data nằm ở đâu. | Nắm rõ data. Sketch kiến trúc. |
| **Thứ Năm 08:30-10:00** | GenAI in practice  | Hiểu lý thuyết |
| **Thứ Năm 13:00-14:30** | Build L1: upload docs lên S3, tạo Bedrock KB, test retrieval | **L1 hoạt động** |
| **Thứ Năm 14:30-16:00** | Build L2: cải thiện prompts, tăng K, xử lý conflicts | **L2 hoạt động** |
| **Thứ Năm 16:00-17:00** | Build L3: seed DB, chạy API, viết 2 tool functions, đăng ký với LLM | **Tool call đầu tiên chạy được** |
| **Thứ Sáu 08:00-10:00** | Polish L3, test tất cả câu hỏi. Thêm L4 memory nếu còn thời gian. | **L3 ổn định** |
| **Thứ Sáu 10:00-12:00** | Viết Evidence Pack, chụp screenshots, chuẩn bị slides | **Evidence Pack committed** |
| **Thứ Sáu 14:00-18:00** | Present | |

---

## Thứ Ba: Khám phá Data (Trước khi viết code)

Đây là ngày chuẩn bị quan trọng nhất. Nhóm nào bỏ qua bước này và nhảy vào code sẽ build sai.

### Bước 1: Đọc knowledge base (1 giờ)

36 tài liệu trong `knowledge_base/`. Đọc hết. Khi đọc, ghi chú:

- **Tài liệu nào cover cùng chủ đề?** (vd: nhiều team docs, nhiều postmortems)
- **Chỗ nào tài liệu mâu thuẫn?** Có 2 API reference docs với rate limits khác nhau — 1 cái archived (500 req/min), 1 cái current (1000 req/min). Hệ thống phải xử lý được.
- **Thông tin nào chỉ là định tính?** Docs nói "costs are rising" nhưng không bao giờ nói số tiền chính xác. Số chính xác nằm trong CSV.

### Bước 2: Chạy monitoring API (15 phút)

```bash
cd data_package/scripts
uv sync
uv run uvicorn monitoring_api:app --port 8000
```

Gọi mọi endpoint:
```bash
curl http://localhost:8000/services
curl http://localhost:8000/status/PaymentGW
curl http://localhost:8000/status/NotificationSvc    # <-- cái này bị degraded!
curl http://localhost:8000/metrics/PaymentGW
curl http://localhost:8000/metrics/NotificationSvc
curl http://localhost:8000/incidents
curl http://localhost:8000/incidents/PaymentGW
```

**Ghi lại:** Data nào CHỈ có từ API? (Trạng thái hiện tại, latency/error/requests hiện tại, active alerts. Không tài liệu nào chứa những thứ này.)

### Bước 3: Seed database (15 phút)

```bash
cd data_package/scripts
uv run python seed_data.py --db-type sqlite
```

Rồi query:
```sql
-- Tổng chi phí PaymentGW trong Q1 2026
SELECT SUM(total_cost) FROM monthly_costs 
WHERE service = 'PaymentGW' AND month IN ('2026-01', '2026-02', '2026-03');
-- Đáp án: 16500

-- Service chi phí cao nhất tháng 3/2026
SELECT service, total_cost FROM monthly_costs 
WHERE month = '2026-03' ORDER BY total_cost DESC LIMIT 1;
-- Đáp án: PaymentGW, 7500

-- SLA target latency của NotificationSvc
SELECT * FROM sla_targets WHERE service = 'NotificationSvc';
-- Đáp án: latency_p99_ms target = 2000
```

**Ghi lại:** Câu hỏi nào database trả lời được mà tài liệu không? (Chi phí chính xác, SLA target numbers, daily metric history.)

### Bước 4: Vẽ kiến trúc (30 phút)

Trên bảng hoặc giấy, sketch:
- Tài liệu đi đâu? (S3 → Bedrock KB)
- LLM nằm ở đâu? (Bedrock API call)
- Tool calls hoạt động thế nào? (LLM yêu cầu → code thực thi → kết quả trả về LLM)
- Conversation state lưu ở đâu? (DynamoDB, local dict, hoặc file)

**Cả nhóm đồng ý trước khi viết code.**

---

## Thứ Năm: Build L1 → L2 → L3

### L1 — Simple RAG

**Xây gì:** Hệ thống nhận câu hỏi, tìm trong knowledge base, trả lời kèm source citation.

**Cách nhanh nhất:**

1. **Upload docs lên S3** — tạo bucket (vd: `geekbrain-kb-{nhom}`) → upload 36 markdown files
2. **Tạo Bedrock Knowledge Base** — Data source: S3 bucket → Embedding: Titan Embeddings v2 → Vector store: OpenSearch Serverless (tự tạo) → Sync
3. **Test retrieval** — search "Team Platform lead" → phải ra chunks từ `team_platform.md` nói về Alex Chen
4. **Kết nối LLM** — gọi Claude qua Bedrock với system prompt yêu cầu trả lời từ context, cite source
5. **Verify** — "Who is the Team Platform lead?" → "Alex Chen" | "What is the deployment freeze window?" → "Friday 18:00 to Monday 08:00" | "What authentication method does PaymentGW use?" → "API key + HMAC-SHA256"

**Cả 3 câu đúng kèm source citation → L1 xong. Chuyển L2.**

### L2 — Advanced RAG

**Thay đổi từ L1:** Xử lý câu hỏi span nhiều tài liệu hoặc có version conflict.

1. **Tăng retrieval K** — lấy 8-10 chunks thay vì 3-5
2. **Cải thiện system prompt** — thêm hướng dẫn xử lý conflict: check archived/superseded, check dates, nếu không rõ thì nói cả hai
3. **Test** — "What is PaymentGW's API rate limit?" → Phải nói 1000 (v2), acknowledge v1 nói 500

**Resolve được rate limit conflict → L2 hoạt động.**

### L3 — Tool-Augmented RAG

**Thay đổi từ L2:** Hệ thống gọi được external tools để lấy data KHÔNG CÓ trong tài liệu.

**Bước 1: Verify data layer** — DB đã seed (`SELECT COUNT(*) FROM monthly_costs;` → 36 rows), API đang chạy

**Bước 2: Viết 2 tool functions:**
- `query_database(sql)` — query SQL read-only. Dùng cho data lịch sử: costs, incidents, SLA targets.
- `get_service_metrics(service_name)` — gọi monitoring API. Dùng cho data live hiện tại.

**Bước 3: Đăng ký tools với LLM** — qua Bedrock Agents, framework (LangChain), hoặc raw API

**Bước 4: Xử lý tool call loop** — LLM trả `tool_use` → parse → execute → gửi kết quả lại → LLM sinh câu trả lời

**Bước 5: Test:**
- "What was PaymentGW's total infrastructure cost in Q1 2026?" → `query_database` → $16,500
- "What is PaymentGW's current p99 latency?" → `get_service_metrics` → ~185ms
- "Is NotificationSvc meeting its SLA targets?" → Gọi CẢ HAI tools → latency 3200ms vs target 2000ms → Không đạt

**Trả về $16,500 từ DB query thật (không phải đoán) → L3 hoạt động.**

---

## Thứ Sáu sáng: Polish + Evidence Pack

### Thêm L4 Memory

L4 là bài toán **context engineering**. Không có memory, LLM xử lý mỗi câu hỏi độc lập. "Why did its costs spike?" vô nghĩa nếu hệ thống không biết "its" = PaymentGW từ turn trước.

**Chọn memory strategy:**
- **Buffer** — lưu tất cả turns, gửi hết. Đơn giản, phù hợp demo <10 turns.
- **Window** — lưu tất cả, chỉ gửi 5 turns gần nhất. Bounded, predictable.
- **Query rewriting** — rewrite câu hỏi thành self-contained trước khi retrieve. Tốt hơn cho follow-ups.

**Test conversation:**
- Turn 1: "Which service had the highest cost in March?" → DB query → "PaymentGW at $7,500"
- Turn 2: "Why did its costs spike?" → phải resolve "its" = PaymentGW → retrieves postmortem
- Turn 3: "Which team is responsible?" → vẫn biết đang nói về PaymentGW → "Team Platform, led by Alex Chen"

### Viết Evidence Pack

Với mỗi level, cần: screenshot câu trả lời đúng + screenshot/log chứng minh hệ thống thật sự làm gì (tool call log cho L3, conversation state cho L4) + 1-2 dòng notes. **Chụp screenshots khi build, không phải sáng thứ Sáu.**

---

## Các bạn sẽ được đánh giá thế nào

### Thang điểm /10

| Level | Điểm | Yêu cầu |
|-------|------|---------|
| L1 — Retrieval | 2.0 | Trả lời đúng kèm source citation |
| L2 — Multi-Source | 3.0 | Tổng hợp nhiều docs, xử lý conflict |
| L3 — Tools | 4.0 | Trả lời đúng số liệu từ DB/API |
| L4 — Memory | 1.0 | Hội thoại nhiều turn hoạt động |
| **Tổng** | **10.0** | |
| L5 — Bonus | +0.5 | Investigation với structured output |

**L1-L3 = 90% điểm. Tập trung ở đây.**

### Phân bổ điểm presentation

| Phần | Tỷ trọng |
|------|----------|
| Live Demo (L1-L4) | 50% |
| Individual QnA | 30% |
| Architecture & Evidence Pack | 20% |

---

## Sai lầm thường gặp

1. **Build mà không đọc docs trước.** Sẽ xây conflict resolution cho L2 mà không biết docs nào conflict.
2. **Nhảy qua L5 khi L1 chưa chạy.** Nếu retrieval hỏng, tools và agents vô dụng. L1 trước.
3. **Không chạy monitoring API.** Nhóm chỉ build document retrieval sẽ fail toàn bộ L3. Chạy API từ thứ Ba.
4. **Tool descriptions quá mơ hồ.** "Gets data" vô dụng. "Returns CURRENT live metrics; for HISTORICAL data use Database Query" — LLM đọc description để quyết định gọi tool nào.
5. **Không test với số thật.** L3 chấm trên numerical accuracy. $16,500 mà hệ thống nói $15,000 là sai.
6. **Không chụp Evidence Pack screenshots.** Chụp khi build, không phải sáng thứ Sáu.
7. **Chỉ lưu conversation state trong memory.** Đủ cho demo, nhưng phải document limitation trong Evidence Pack.
