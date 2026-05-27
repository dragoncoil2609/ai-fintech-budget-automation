---
week: 4
title: "W4: Xây dựng AI thực sự trả lời được câu hỏi"
audience: students
release: "Thứ Hai 2026-05-03 sáng"
deadline: "Thứ Sáu 2026-05-08, thuyết trình nhóm"
---

# W4: Xây dựng AI thực sự trả lời được câu hỏi

> 3 tháng 5 — 8 tháng 5, 2026

---

## Thử thách tuần này

Các bạn sẽ xây dựng một AI system trả lời câu hỏi về **GeekBrain** — một fintech startup đang vận hành sáu production service. Các bạn sẽ nhận được một data package gồm: các file markdown mô tả cách công ty hoạt động, CSV files chứa lịch sử cost và performance, một seed script để load CSV vào database, và một monitoring API trả về live system state.

**System của bạn phải trả lời câu hỏi ở bốn cấp độ tăng dần.** Mỗi cấp độ đòi hỏi một khả năng mà cấp trước chưa có. Các cấp độ được định nghĩa bởi những gì câu hỏi yêu cầu — không phải bởi architecture phải xây dựng như thế nào.

**System của bạn phải trả lời câu hỏi ở bốn cấp độ tăng dần.** Chúng tôi cung cấp data. Bạn thiết kế architecture.

---

## Bốn cấp độ

Các cấp độ có tính tích lũy. Mỗi cấp xây dựng trên cấp trước. Không thể bỏ qua cấp — L3 yêu cầu nền tảng L1-L2 đang hoạt động, và L4 yêu cầu tools từ L3 phải hoạt động được.

Bạn có thể tự build từng layer — retrieval, tool routing, orchestration, memory — sử dụng framework như LangChain, LlamaIndex, hoặc gọi API trực tiếp. Hoặc bạn có thể dùng managed service như **Amazon Bedrock AgentCore**, xử lý orchestration, tool routing, KB sync, và session memory cho bạn. Dù chọn cách nào, bạn vẫn phải tự viết tool functions, agent instructions, và setup knowledge base. Yêu cầu từng level và tiêu chí đạt đều giống nhau.

---

### L1 — Retrieval (Simple RAG)

**Câu hỏi yêu cầu gì:** Một fact đơn giản có trong một document.

*Ví dụ: "What is GeekBrain's API rate limit for PaymentGW?"*

*Ví dụ: "Who is the Team Platform lead?"*

**Điều kiện pass:** System trả về đúng fact và nêu tên source document.

**Architecture hint — chọn một trong ba:**

| Approach | Trông như thế nào | Pros / Cons |
|----------|-------------------|-------------|
| **Bedrock Knowledge Bases** | Upload docs lên S3 → Tạo Bedrock KB → Gọi `RetrieveAndGenerate` API | Set up nhanh nhất. AWS lo chunking, embedding, vector store. Ít kiểm soát retrieval quality. |
| **Custom RAG pipeline** | Tự chunk docs → Embed bằng Titan/OpenAI → Lưu vào OpenSearch hoặc ChromaDB/FAISS → Retrieve top-K → Gửi cho LLM | Kiểm soát hoàn toàn chunking, embedding model, retrieval parameters. Tốn thời gian setup hơn. |
| **Bedrock KB + custom prompt** | Dùng Bedrock KB `Retrieve` API (trả về raw chunks) → Tự build prompt với chunks → Gọi LLM | Tốt nhất của cả hai: managed retrieval + kiểm soát hoàn toàn prompt. Điểm khởi đầu được khuyến nghị. |

**Các bước để chạy được L1:**

1. Upload 36 knowledge base markdown file lên S3 bucket
2. Tạo Bedrock Knowledge Base trỏ vào S3 bucket đó
3. Chọn embedding model (Amazon Titan Embeddings v2 là mặc định)
4. Sync knowledge base (chờ sync hoàn tất)
5. Test với `Retrieve` API — có trả về đúng chunk cho câu hỏi đơn giản không?
6. Gửi retrieved chunks + câu hỏi cho LLM (Claude Sonnet qua Bedrock) kèm system prompt: "Answer the question using only the provided context. Cite the source document."
7. Kiểm tra: hỏi "Who is the Team Platform lead?" — câu trả lời phải là "Alex Chen" từ `team_platform.md`

**Nếu L1 chạy được, bạn đã có nền tảng. Mọi thứ khác đều xây trên đó.**

---

### L2 — Multi-Source Retrieval (Advanced RAG)

**Câu hỏi yêu cầu gì:** Thông tin đến từ hai hay nhiều document, hoặc câu trả lời mà hai document mâu thuẫn nhau và system phải xác định cái nào đúng.

*Ví dụ: "If Team Commerce has a P1 bug in OrderSvc on Friday night, can they deploy a fix? What approvals do they need?"*

*Ví dụ: "What is GeekBrain's API rate limit for PaymentGW?" (Hai document cho hai con số khác nhau — system phải xác định cái nào là hiện tại.)*

**Điều kiện pass:** System tổng hợp từ nhiều nguồn và giải quyết conflict đúng.

**Architecture hint — cải thiện L1 pipeline của bạn:**

| Technique | Tác dụng | Khi nào dùng |
|-----------|-------------|-------------|
| **Increase top-K** | Retrieve nhiều chunk hơn (ví dụ K=10 thay vì K=3) | Khi câu trả lời trải rộng nhiều document |
| **Hybrid search** | Kết hợp vector search (semantic) + keyword search (BM25) | Khi câu hỏi đề cập exact ID, error code, hoặc tên mà vector search bỏ sót |
| **Metadata filtering** | Lọc chunks theo ngày, version, status trước khi ranking | Khi documents mâu thuẫn nhau (v1 vs v2, archived vs current) |
| **Improved system prompt** | Nói với LLM: "If sources conflict, prefer the most recent version. State the conflict." | Luôn luôn — cái này miễn phí và hiệu quả cao |

**Các bước để chạy được L2:**

1. Bắt đầu từ L1 pipeline đang hoạt động
2. Tăng retrieval K từ 3-5 lên 8-10 chunk
3. Thêm vào system prompt: "When multiple documents provide different information, check their dates and version numbers. Prefer the most recent. If documents conflict, explain which you trust and why."
4. Test với conflict question: "What is PaymentGW's API rate limit?" — system phải retrieve cả v1 (500) lẫn v2 (1000) và xác định đúng v2 là current
5. Test với multi-doc question: "Can Team Commerce deploy on Friday night?" — system phải kết hợp deployment_policy.md + incident_response_policy.md + thông tin team

---

### L3 — Retrieval + Tools (Tool-Augmented RAG)

**Câu hỏi yêu cầu gì:** Câu trả lời không thể tìm thấy trong bất kỳ document nào. Một số câu hỏi cần current system state từ monitoring API. Một số cần số liệu lịch sử từ database. Một số cần cả hai.

*Ví dụ: "What was PaymentGW's total infrastructure cost in Q1/2026?"*

*Ví dụ: "Is PaymentGW's latency right now better or worse than its Q1 average?"*

**Điều kiện pass:** System trả về câu trả lời đúng số liệu dựa trên real data.

**Architecture hint — thêm tools vào L2 pipeline:**

| Approach | Trông như thế nào | Pros / Cons |
|----------|-------------------|-------------|
| **Bedrock Agents** | Tạo Agent với Action Groups (Lambda functions) + KB. Agent quyết định mỗi query: retrieve từ KB, gọi tool, hoặc cả hai. | Managed orchestration. Agent tự handle routing. Ít kiểm soát thời điểm tool được gọi. |
| **Framework tool integration** | Dùng LangChain hoặc LlamaIndex để define tools. Framework handle vòng lặp LLM ↔ tool call. | Kiểm soát routing tốt hơn. Quen thuộc nếu biết framework. |
| **Raw function calling** | Gọi LLM API trực tiếp với tool definitions trong request. Parse tool call responses trong code. Execute. Feed result trở lại. | Kiểm soát hoàn toàn. Nhiều code nhất. Tốt nhất để hiểu điều gì đang xảy ra. |

**Các bước để chạy được L3:**

1. **Set up data layer trước:**
   - Chạy `seed_data.py` để load CSV vào database (SQLite để bắt đầu nhanh nhất: `python seed_data.py --db-type sqlite`)
   - Start `monitoring_api.py` locally (`uvicorn monitoring_api:app --port 8000`)
   - Test cả hai: query database thủ công, hit từng API endpoint

2. **Build ít nhất 2 tool function:**
   - **Tool 1 — Database Query:** Nhận SQL query string, execute với database, trả về rows. Dùng cho cost questions, incident queries, SLA lookups.
   - **Tool 2 — Service Metrics:** Gọi `GET /metrics/{service_name}` trên monitoring API, trả về current latency, error rate, requests/min.

3. **Register tools với LLM:**
   - Viết tool descriptions rõ ràng: mỗi tool trả về gì, khi nào dùng (current data vs historical data)
   - Nếu dùng Bedrock Agents: tạo Action Groups với Lambda functions
   - Nếu dùng framework/raw API: define tools trong code

4. **Test routing:**
   - "What was PaymentGW's total cost in Q1 2026?" → system phải gọi Database Query tool → trả về $16,500
   - "What is PaymentGW's current p99 latency?" → system phải gọi Service Metrics tool → trả về ~185ms
   - "Is PaymentGW within its latency SLA?" → system phải gọi CẢ HAI (metrics cho current, DB cho target) → so sánh 185ms vs 200ms

5. **Kiểm tra số liệu phải đúng** — L3 được chấm điểm dựa trên numerical accuracy. Sai số = không có credit.

**Lỗi phổ biến ở L3:**
- Tool descriptions quá mơ hồ → LLM gọi nhầm tool
- Monitoring API không chạy → tool call fail silently → LLM hallucinate số
- Database chưa seed → query trả về rỗng → LLM tự bịa data
- Không test với câu hỏi L3 thực tế trước thứ Sáu

---

### L4 — Retrieval + Tools + Memory (10% điểm)

**Câu hỏi yêu cầu gì:** Một cuộc hội thoại multi-turn trong đó các câu hỏi follow-up tham chiếu đến các lượt trước. Người dùng không nhắc lại context.

*Ví dụ:*
- *Turn 1: "Which service had the highest infrastructure cost in March 2026?"*
- *Turn 2: "What was the main cause of the cost increase that month?"*
- *Turn 3: "Which team is responsible?"*
- *Turn 4: "The postmortem mentioned a review deadline. Is it overdue?"*

**Điều kiện pass:** System xử lý đúng cuộc hội thoại 3-4 turn. Các follow-up dùng "that service", "their team", "the same issue" được resolve mà người dùng không cần nhắc lại.

**Hãy nghĩ về điều này:** L3 system của bạn xử lý mỗi câu hỏi độc lập. Hỏi nó "Which service had the highest cost?" rồi hỏi tiếp "Why did its costs spike?" — nó không biết "its" đề cập đến cái gì. Câu hỏi thứ hai đến với zero context từ câu đầu.

Không có memory, mỗi câu hỏi là độc lập. LLM không biết "its costs" hay "that service" đề cập đến gì — vì nó chưa bao giờ thấy câu trả lời Turn 1. L4 là về việc giải quyết vấn đề này: làm thế nào để duy trì context qua các turn để cuộc hội thoại diễn ra liên tục?

Đây là bài toán **context engineering**. Mọi thứ LLM nhận được — system prompt, retrieved chunks, tool results, conversation history — đều cạnh tranh không gian trong context window. Bạn phải quyết định cái gì cần include và cái gì bỏ ra. Câu hỏi là: làm thế nào để đảm bảo LLM vẫn resolve được "that service" hay "their team" ba turn sau — mà không làm ngập context và làm giảm chất lượng câu trả lời?

---

### Bonus Opportunities (+1.0 tối đa)

Bonus chỉ được chấm nếu L1-L3 đang hoạt động. Bonus KHÔNG tính vào điểm cơ bản 10 điểm.

**Bonus A — Observability Dashboard (+0.5)**

Build một màn hình hoặc UI hiển thị nội bộ hệ thống khi xử lý câu hỏi: những gì đã retrieve, tool nào được gọi, LLM nhận gì, LLM quyết định gì, kết quả trả về là gì. Coi như một cửa sổ nhìn vào pipeline — trainer có thể thấy quá trình reasoning xảy ra real-time, không chỉ kết quả cuối cùng.

**Bonus B — Agent Reasoning (+0.5)**

Xử lý các câu hỏi điều tra mở đòi hỏi multi-step reasoning.

*Ví dụ: "Is NotificationSvc in a healthy state? Assess its reliability and flag anything that needs attention."*

System phải lên kế hoạch tiếp cận, thu thập từ nhiều nguồn, và tạo ra structured report với các reasoning step hiển thị rõ ràng.

**Bonus C — Knowledge Base Sync (+0.5)**

Documents thay đổi theo thời gian. Knowledge base chỉ sync một lần sẽ trở nên lỗi thời. Xây dựng cơ chế re-sync Bedrock KB khi documents được cập nhật trên S3 — tự động hoặc chạy tay đều được.

*Ví dụ: S3 event → Lambda → `StartIngestionJob`. Hoặc một Jupyter notebook trigger sync theo yêu cầu. Cách nào hoạt động đều được tính.*

**Bonus tối đa: +1.0.** A hoặc B = +0.5. C = +0.5. Điểm cuối cùng capped tại 11.0.

---

## Bạn nhận được gì

1. **Knowledge base documents** — ~36 file markdown về GeekBrain: company overview, team structure, service architecture, deployment policies, incident postmortems, SLA policy, security policy, meeting notes, runbooks, và nhiều hơn nữa. Đọc kỹ trước khi bắt đầu build. Không phải tất cả documents có cùng format. Một số mâu thuẫn với nhau.

2. **CSV files** — structured data với số liệu chính xác:
   - `monthly_costs.csv` — chi phí theo từng service theo tháng (tháng 10/2025 - tháng 3/2026)
   - `incidents.csv` — lịch sử incident với severity, duration, root cause, resolution
   - `sla_targets.csv` — SLA targets theo từng service theo từng metric
   - `daily_metrics.csv` — daily latency, error rate, và request volume (tháng 1 - tháng 3/2026)

3. **Seed script** (`seed_data.py`) — load CSV files vào SQLite (mặc định) hoặc PostgreSQL. Tạo tables tự động. Chạy script một lần là data sẵn sàng.

4. **Monitoring API** (`monitoring_api.py`) — một Python script chạy locally. Trả về live system state dạng JSON. Hit từng endpoint trước khi bắt đầu build — có data chỉ có từ API mà không có trong bất kỳ document nào.

5. **Tool list** — các tool mà AI system của bạn cần implement (xem bên dưới).

---

## Các Tool System Phải Có

Đây là các tool mà AI system của bạn phải có khả năng gọi. Bạn quyết định cách implement từng tool — tham số nhận vào là gì, trả về gì, kết nối với data như thế nào.

| Tool | Tác dụng |
|------|-------------|
| **Service Status** | Lấy live status hiện tại của một service |
| **Service Metrics** | Lấy current performance metrics của một service |
| **List Services** | Liệt kê tất cả service trong system |
| **Incident History** | Lấy các incident đã qua của một service |
| **Team Info** | Lấy thông tin chi tiết về một team |
| **Compare Services** | So sánh một metric giữa nhiều service |
| **Database Query** | Query structured data (costs, SLAs, daily metrics) |

Các tool này lấp đầy khoảng trống giữa những gì có trong documents và những gì không có. Câu hỏi L3 yêu cầu tools.

---

## Phải Nộp Gì Vào Thứ Sáu

### 1. System đang chạy được

Một AI system đang hoạt động — local hoặc cloud — nhận câu hỏi và trả về câu trả lời. Phải demo live vào thứ Sáu. Không được hardcode response. Trainer sẽ hỏi những câu hỏi system chưa từng thấy.

### 2. Slides

Slides thứ Sáu được rút từ Evidence Pack (xem bên dưới). Build markdown trước, rồi lấy các screenshots và quyết định quan trọng vào slides.

### 3. Evidence Pack

> Trainer chấm điểm theo file này sau khi bạn rời phòng. Xem section **Evidence Pack** riêng bên dưới.

---

## Evidence Pack

> **Đây là deliverable quan trọng nhất trong tuần.** Slides thứ Sáu được rút từ file này. Trainer sẽ kiểm tra lại mọi claim trong file này sau buổi presentation.

**Đây là gì:** một file markdown duy nhất tại `docs/W4_evidence.md` trong group repository.

**Tại sao markdown:** Slides hay bị mất, bullet bị cắt, screenshot bị mờ khi resize. File markdown nằm trong repo, đi cùng code, giữ nguyên resolution, và trainer có thể verify mọi thứ sau thứ Sáu.

---

### Section 1 — Cover

- Số nhóm
- Tên thành viên
- LLM sử dụng (ví dụ: Claude Sonnet via Bedrock)
- Framework sử dụng (ví dụ: LangChain / Bedrock Agents / raw API)
- Link repo

---

### Section 2 — Architecture Overview

- System architecture diagram (ASCII, Mermaid, hoặc image)
- Danh sách component: mỗi phần làm gì
- Data flow: câu hỏi đi từ user input → retrieval/tool → LLM → câu trả lời cuối
- Screenshot system đang chạy (terminal hiển thị app started, hoặc URL nếu deploy cloud)

---

### Section 3 — Decision Log

3 quyết định quan trọng trong tuần. Với mỗi quyết định:
- Bạn chọn gì
- Bạn học được gì

Ít nhất 1 điều không hoạt động và bạn đã làm gì thay thế. "Chúng tôi thử X, fail vì Y, nên chuyển sang Z" có giá trị hơn "mọi thứ đều ổn."

---

### Section 4 — Per-Level Evidence

**Với mỗi level, cần 2 thứ:**

1. **Câu trả lời đúng** — screenshot output của system
2. **Bằng chứng câu hỏi thực sự đi qua system** — không chỉ kết quả cuối, mà phải có bằng chứng pipeline đã xử lý (retrieve chunks, gọi tool, gọi Bedrock, v.v.)

**Cách cung cấp bằng chứng:**
- Nếu bạn có observability dashboard (Bonus A) — screenshot nó. Đó chính LÀ bằng chứng.
- Nếu không — cho 1-2 screenshot terminal log hoặc CloudWatch log cho thấy request đi qua system: Bedrock API call, retrieved chunks, tool invocation và response. Trainer cần thấy LLM nhận data thật, không phải tự đoán.

**Không cần nhiều screenshot. 1-2 mỗi level là đủ.** Chất lượng hơn số lượng.

---

**L1 Evidence:**
- Screenshot: câu trả lời đúng kèm source document được cite
- Bằng chứng: log cho thấy retrieval đã xảy ra (Bedrock Retrieve call trả về chunks, hoặc output từ custom pipeline)

**L2 Evidence:**
- Screenshot: multi-doc synthesis hoặc conflict resolution đúng (ví dụ: API rate limit → 1000, không phải 500)
- 1-2 dòng: system xử lý conflicting documents như thế nào

**L3 Evidence:**
- Screenshot: câu trả lời số liệu chính xác (ví dụ: "PaymentGW Q1 cost = $16,500")
- Bằng chứng: log cho thấy tool đã được gọi và trả về data thật. **Đây là bằng chứng quan trọng nhất trong toàn bộ Evidence Pack.** Trainer cần thấy tool call — không chỉ câu trả lời.

**L4 Evidence (nếu đã thực hiện):**
- Screenshot: cuộc hội thoại 3-4 turn trong đó follow-up tham chiếu lượt trước
- 1-2 dòng: chiến lược memory bạn sử dụng

**Nếu bạn dùng AgentCore:**
- Architecture diagram: phần nào AgentCore quản lý vs phần nào bạn tự build
- Annotated trace logs cho ít nhất 2 câu hỏi (1 RAG-only, 1 tool-augmented) — giải thích từng bước xảy ra gì

**Bonus A Evidence (Observability Dashboard):**
- Screenshot: dashboard hiển thị quá trình xử lý câu hỏi — retrieval, tool calls, LLM decisions hiển thị real-time

**Bonus B Evidence (Agent Reasoning):**
- Screenshot: structured investigation output với reasoning steps hiển thị rõ ràng

---

### Section 5 — Reflection

Level khó nhất và tại sao. Bạn sẽ làm gì khác nếu có thêm một ngày.

---

### Chấm điểm Evidence Pack

| Bạn nộp gì | Điểm evidence tối đa |
|------------|----------------------|
| Không có Evidence Pack | Cap ở 2/5 |
| Chỉ có screenshot câu trả lời — không có log, không có bằng chứng system xử lý | Cap ở 3/5 |
| Screenshot + bằng chứng system (log/dashboard) + notes + decision log | 4/5 |
| Tất cả ở trên, sạch đẹp và có tổ chức | 5/5 |

**Link discipline:** Slides thứ Sáu phải link đến Evidence Pack commit. Post commit link lên Slack trước slot của bạn. Không có link = điểm evidence bị cap ở 3 trước khi demo bắt đầu.

---

## Chấm điểm (thang 10)

### Điểm cơ bản (10 điểm)

| Tiêu chí | Điểm | Đo lường gì |
|-----------|--------|-----------------|
| **L1 — Retrieval** | 2.0 | Câu trả lời single-doc đúng với source citation |
| **L2 — Multi-Source Retrieval** | 3.0 | Multi-doc synthesis, giải quyết conflict |
| **L3 — Retrieval + Tools** | 4.0 | Câu trả lời số liệu chính xác từ tools/DB/API |
| **L4 — Memory** | 1.0 | Multi-turn conversation với pronoun resolution |
| **Tổng** | **10.0** | |

**L1-L3 chiếm 90% điểm của bạn.** Nếu system xử lý L1-L3 ổn định, bạn đạt 9/10 trước L4.

### Điểm thưởng (+1.0 tối đa)

| Bonus | Điểm |
|-------|--------|
| **Bonus A — Observability Dashboard** | +0.5 — UI hiển thị nội bộ pipeline: những gì retrieved, tool nào được gọi, LLM input/output |
| **Bonus B — Agent Reasoning** | +0.5 — Multi-step investigation với structured output và visible reasoning |
| **Bonus C — Data Operations** | +0.5 — Auto-sync S3 với production mindset |

**Điểm tối đa có thể đạt: 11.0.** A và B share +0.5; C là +0.5 riêng. Bonus chỉ chấm nếu L1-L3 đang hoạt động.

### Cách chấm điểm từng level (Likert 1-5)

| Điểm | Ý nghĩa |
|-------|---------|
| 1 | Không thực hiện hoặc hoàn toàn hỏng |
| 2 | Đã thực hiện nhưng chủ yếu sai — câu trả lời sai, thiếu source, sai số |
| 3 | Hoạt động một phần — một số câu trả lời đúng, một số sai. Tool call xảy ra nhưng kết quả không ổn định |
| 4 | Hoạt động ổn định — câu trả lời đúng, source citations, số liệu chính xác. Vài edge case nhỏ |
| 5 | Xuất sắc — xử lý đúng tất cả test questions, graceful error handling, output sạch |

**Chuyển đổi điểm level → điểm số:** `points = (score / 5) * max_points_for_level`

Ví dụ: L3 score 4/5 → (4/5) * 4.0 = 3.2 điểm

### Các thành phần thuyết trình

Điểm 10 đến từ:

| Thành phần | Tỷ trọng | Trainer đánh giá gì |
|-----------|--------|----------------------|
| Live Demo (L1-L4) | 50% | System có trả lời đúng ở mỗi level không? |
| Individual QnA | 30% | Bạn có hiểu system của mình hoạt động như thế nào không? |
| Architecture & Evidence Pack | 20% | Diagram, decision log, chất lượng evidence |

---

## Quy tắc

1. **Architecture là tự do.** Bất kỳ approach nào, bất kỳ framework nào, bất kỳ LLM nào.
2. **Chọn LLM tự do trên AWS Bedrock.**
3. **Không được hardcode câu trả lời.** Trainer hỏi những câu hỏi ngoài tập ví dụ.
4. **Mọi team đều nhận cùng data package.**
5. **AI-assisted coding được phép và được khuyến khích.**

---

## Lịch trình

| Ngày | Diễn ra gì |
|-----|-------------|
| **Thứ Ba** | Nhận data package. Đọc tất cả documents. Start monitoring API và hit từng endpoint. Chạy seed script. Vẽ architecture trước khi viết code. |
| **Thứ Năm 08:30-10:00** | Giới thiệu: RAG systems, tools, memory, agent reasoning. |
| **Thứ Năm 13:00-17:00** | Build. Làm L1 chạy được trước. Không bắt đầu L3 cho đến khi L1 ổn định. |
| **Thứ Sáu 08:00-12:00** | Hoàn thiện system, viết Evidence Pack, chuẩn bị slides. Post Evidence Pack commit link lên Slack trước slot của nhóm. |
| **Thứ Sáu 14:00-18:00** | Thuyết trình (~10-12 phút mỗi nhóm). |

---

## Format thuyết trình thứ Sáu (~10-12 phút)

**Trước khi thuyết trình:** post link commit `docs/W4_evidence.md` lên trainer Slack channel. Không có link = điểm evidence pre-flagged ở cap 2.

**Phần 1 — Architecture (3 phút):** Trình bày system diagram. Đặt tên từng component. Giải thích một quyết định quan trọng và một điều bạn đã thay đổi trong tuần.

**Phần 2 — Individual QnA (3 phút):** 2-3 thành viên team được chọn ngẫu nhiên và hỏi về cách hoạt động của system.

**Phần 3 — Live Demo (4-5 phút):** Demo system trả lời câu hỏi ở mỗi level đã thực hiện.

Nếu live answer thất bại, screenshot trong Evidence Pack cho level đó được chấp nhận thay thế — không bị phạt. Thiếu cả live lẫn screenshot cho một level sẽ cap điểm level đó ở 2.

**Phần 4 — Lessons Learned (1 phút):** Level khó nhất và tại sao. Bạn sẽ làm gì khác.

---

## Bắt đầu — Con đường quan trọng đến L3

Làm theo thứ tự này. Không được bỏ qua bước.

### Ngày 1 (Thứ Ba): Khám phá data

1. Đọc từng document trong knowledge base. Document nào cùng topic? Chỗ nào mâu thuẫn? (Bạn cần điều này cho L2.)
2. Start monitoring API: `cd data_package/scripts && uv sync && uv run uvicorn monitoring_api:app --port 8000`
3. Hit từng API endpoint thủ công. Ghi lại data nào CHỈ có từ API.
4. Chạy seed script: `uv run python seed_data.py --db-type sqlite`
5. Query database: `SELECT service, total_cost FROM monthly_costs WHERE month = '2026-03' ORDER BY total_cost DESC;` — bạn phải thấy PaymentGW ở 7500.

### Ngày 2 (Thứ Năm): Build L1 → L2 → L3

**Buổi sáng — L1 (mục tiêu: chạy được trước 12:00):**
1. Upload knowledge base docs lên S3
2. Tạo Bedrock KB, sync, verify
3. Test retrieval: có trả về đúng chunks không?
4. Kết nối LLM với system prompt
5. Kiểm tra: "Who leads Team Platform?" → "Alex Chen"

**Buổi chiều — L2 (mục tiêu: chạy được trước 15:00):**
1. Tăng retrieval K lên 8-10
2. Cải thiện system prompt cho conflict resolution
3. Test: "What is the API rate limit?" → phải resolve v1 vs v2

**Chiều muộn — L3 (mục tiêu: tool call đầu tiên chạy được trước 17:00):**
1. Build Database Query tool function
2. Build Service Metrics tool function
3. Register tools với LLM
4. Test: "What was PaymentGW's total cost in Q1?" → $16,500

### Ngày 3 (Sáng thứ Sáu): Hoàn thiện + Evidence

1. Test tất cả levels end-to-end
2. Thêm L4 memory nếu còn thời gian (ngay cả simple last-5-turns window cũng tính)
3. Viết Evidence Pack với screenshots và logs
4. Chuẩn bị slides

---

Chúc may mắn. Hãy xây dựng thứ thực sự trả lời được câu hỏi.
