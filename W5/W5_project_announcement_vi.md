---
week: 5
title: "W5: The Network Fortress"
audience: students
release: "Sáng Thứ Hai 11-05-2026"
deadline: "Thứ Sáu 15-05-2026, presentation nhóm"
---

# W5: The Network Fortress

> 11–15 tháng 5, 2026

---

## Thử thách tuần này

Đến lúc này, ứng dụng của bạn đã suy luận trên tài liệu, gọi tool, và trả lời câu hỏi — không chỉ còn là hạ tầng để lưu và xử lý data. Kiến trúc bạn xây từ W1 đã chạy được. Tuần này nó vẫn chạy, và còn phải lớn thêm.

Cái thay đổi tuần này là **những gì bao quanh nó**. Tuần 5 là về hardening: làm cho network quan sát được, làm cho security control ép buộc được tại biên, làm cho lớp file có thể chia sẻ, làm cho lớp API tử tế, và bảo đảm mọi tài nguyên có state trong ứng dụng đều có một backup **đã được test khôi phục thật**.

Ứng dụng cloud thực tế hỏng theo những cách rất dễ đoán. Traffic đi sai route sẽ vòng qua firewall. Backup plan chưa từng restore là backup plan không chạy được. Một Lambda endpoint không throttling sẽ bị nện và kéo theo mọi thứ khác sập. Một file dùng chung chỉ nằm trên một EC2 trở thành single point of failure ngay khi bạn scale. Tuần này bạn đóng các khe hở đó — **trên chính ứng dụng của team**.

Workshop AWS account reset mỗi tuần, nên bạn deploy lại stack ứng dụng tươi trên account sạch. Cái không đổi là **kiến trúc, business domain, và các quyết định thiết kế** — tiếp tục xây cùng ứng dụng 3-tier bạn đã đề xuất trong W1 và đào sâu mỗi tuần kể từ đó. **Đừng pivot sang ứng dụng khác. Đừng đổi core stack** (database engine, cách tích hợp AI) chỉ để tiện cho W5.

---

## Cái gì phải mang theo từ tuần trước (Bắt buộc)

Trước khi thêm nội dung W5, các thứ sau phải được deploy và chạy được vào Thứ Sáu — trainer sẽ verify hết trong Part 1 cùng với các must-haves mới:

**Bắt buộc:**
- [ ] **Ứng dụng đã deploy và hoạt động end-to-end.** Chạy 1–2 action đại diện trên deployment live chứng minh app chạy đúng như team thiết kế — request qua API, một downstream operation, action admin, hoặc bất cứ thứ gì chứng tỏ tốt nhất hệ thống đang sống.
- [ ] **Architecture diagram khớp với những gì thực sự được deploy.** Không có tầng vẽ mà chưa deploy, không có tầng đã deploy mà chưa vẽ. Diagram trong Part 1 phản ánh đúng những gì trainer thấy trên console AWS của bạn.
- [ ] **Feedback từ tuần trước được giải quyết trong Part 1.** Nêu một feedback cụ thể và show W5 build tiếp hoặc fix nó thế nào.

Bên trong ứng dụng team xây thế nào — stack gì, service gì, AI tích hợp ra sao, có data pipeline hay không — là lựa chọn của team. W5 không chỉ định cái đó. W5 chỉ định **lớp hardening (5 must-haves dưới đây) bao quanh app**.

Nếu bất kỳ mục bắt buộc nào ở trên bị hỏng vào Thứ Sáu, **tính trừ Criterion II (AWS Architecture)**.

---

## Phải nộp gì (Năm Core Must-Haves)

Năm cái này map trực tiếp vào những gì bạn học tuần này: networking Thứ Hai, file storage và backup Thứ Ba, serverless và API Gateway Thứ Tư. **Vừa học vừa xây.**

---

### 1. Multi-VPC Connectivity — Làm cho network quan sát được

Nhìn lại setup VPC hiện tại. Đưa ra một quyết định connectivity có chủ đích và document lại.

Ba path đều hợp lệ:

**Path A — VPC Peering:** team có hai hoặc ba VPC với CIDR không chồng và cần traffic point-to-point direct. Tạo peering connection, cập nhật route table cả hai bên, và test connectivity cross-VPC bằng curl hoặc ping.

**Path B — AWS Transit Gateway:** team có ba VPC trở lên, hoặc cần transitive routing, hoặc dự định thêm kết nối VPN/Direct Connect sau này. Tạo TGW, attach các VPC, cấu hình TGW route table, và test traffic chảy qua hub.

**Path C — Justified Single-VPC:** ứng dụng thực sự chạy đúng trong một VPC được thiết kế tốt và không có business case nào để tách. Path này đòi **justification cụ thể cho ứng dụng** (không phải câu chữ chung chung), cộng thêm việc đưa mọi tầng subnet chưa multi-AZ lên multi-AZ, cộng thêm viết ra event kiến trúc nào sẽ trigger thêm VPC thứ hai sau này.

**Default vào single-VPC mà không có justification viết tay = không tính Path C.**

**Bắt buộc bất kể chọn path nào:** bật VPC Flow Logs trên mọi VPC và publish về CloudWatch Logs hoặc S3. Show sample log entry trong Evidence Pack. Flow Logs là cách bạn chứng minh traffic đang chảy đúng nơi bạn nghĩ.

---

### 2. Network Firewall Hardening — Ép buộc tại biên

Security Group và NACL bảo vệ từng resource. Network Firewall ép buộc stateful rule và phát hiện xâm nhập tại biên VPC. Hai path đều hợp lệ:

**Path A — Deploy AWS Network Firewall:** instance Lambda hoặc EC2 của bạn ra internet qua NAT Gateway vì bất kỳ lý do gì. Deploy firewall endpoint trong một firewall subnet riêng, tạo ít nhất một stateful rule group (domain-based egress allowlist hoặc một IPS signature), bật Alert Logs, và cập nhật route table để traffic đi qua firewall trước NAT Gateway.

Show một request được cho phép đi qua (thấy trong Flow Logs) và một request bị chặn (thấy trong Alert Logs).

**Path B — Hardened SG + NACL:** topology thực sự cô lập khỏi internet — mọi truy cập AWS service đều qua VPC endpoint, không có NAT Gateway, không có đường ra internet từ bất kỳ instance hay Lambda nào. Viết justification giải thích (a) vì sao egress firewall không cần thiết cho topology này và (b) traffic nào sẽ đòi deploy nó trong production. Sau đó: xóa mọi rule inbound 0.0.0.0/0 trên port 22/3389 ở mọi Security Group, thêm ít nhất một NACL DENY rule rõ ràng, và show negative test (kết nối bị từ chối kèm screenshot).

**Nếu bất kỳ EC2 hay Lambda nào trong stack ra internet qua NAT Gateway, bắt buộc Path A.**

---

### 3. File Storage Layer + Backup Plan — Chia sẻ data, bảo vệ state

**File storage:** thêm một lớp file dùng chung cho app tier. Đa số nhóm sẽ dùng **Amazon EFS** — mount lên một hoặc nhiều EC2/Lambda trong private application subnet. File system phải phục vụ **nội dung thật của ứng dụng**: file upload chung, session token, model artifact, config chung — bất cứ gì có ý nghĩa với ứng dụng. Security Group của mount target chỉ được allow từ SG của app tier (không phải 0.0.0.0/0).

Show một file ghi và đọc lại từ path đã mount. Phải làm trên instance trong private subnet, không phải EC2 public hoặc bài test rời.

**Backup plan:** tạo backup plan trong AWS Backup bao trùm ít nhất ba loại resource trong stack: file system (EFS/FSx), database W3 (RDS/DynamoDB/Aurora), và EBS volume W2. Plan phải có schedule (tối thiểu daily), retention (tối thiểu 7 ngày), và một backup vault.

**Restore test là bắt buộc.** Trigger restore job từ một recovery point. Đợi nó complete. Connect vào resource đã khôi phục. Đọc lại data đã biết và xác nhận có ở đó. **Backup plan chưa từng restore không phải kế hoạch khôi phục — nó là hy vọng.**

Đưa screenshot restore job Completed **và** screenshot data đọc được từ resource đã khôi phục vào Evidence Pack.

---

### 4. API Gateway trước Lambda — Xây surface API tử tế

Các Lambda function của bạn hiện đang được gọi trực tiếp — từ code ứng dụng dùng SDK, hoặc từ ALB, hoặc từ event trigger. Đây không phải surface API tử tế: không throttling, không auth tại tầng API, không có URL frontend gọi an toàn được.

Chọn một Lambda đang có trong ứng dụng — cái xử lý Bedrock query, hoặc lookup database, hoặc trigger pipeline — và đặt API Gateway trước nó.

Phải cấu hình:
- Một API Gateway REST API hoặc HTTP API (chọn theo phương thức auth — xem course Thứ Tư để hiểu trade-off)
- Ít nhất một route tích hợp Lambda qua Lambda Proxy Integration
- Throttling: usage plan với rate limit (requests/giây) và burst limit
- Authentication: API Key, Lambda Authorizer, hoặc Cognito User Pool Authorizer — phải có một cái cấu hình và chạy được

**Cập nhật code ứng dụng** để gọi URL API Gateway thay vì invoke Lambda trực tiếp.

Show hai test curl: một authenticated trả 200, một unauthenticated trả 403. Cả hai phải có trong Evidence Pack.

---

### 5. Serverless Scaling Pattern — Xử lý tải đúng cách

Hành vi mặc định của Lambda — concurrency không giới hạn tới account limit, chỉ gọi đồng bộ — chạy được trong dev. Trong production nó hỏng theo những cách rất dễ đoán. Chọn một scaling pattern và apply lên một Lambda đang có trong ứng dụng.

Bốn pattern hợp lệ:

**Reserved Concurrency:** set concurrency tối đa cho một function vốn có thể nuốt hết account limit (ví dụ batch processor trigger bởi S3 event lúc import dữ liệu lớn). Show throttle behavior: invoke nhiều hơn limit, screenshot metric `Throttles` trong CloudWatch hoặc response `TooManyRequestsException`.

**Provisioned Concurrency:** pre-warm function Lambda đứng sau API Gateway MH4 để loại bỏ cold start. So sánh CloudWatch trace trước (thấy init duration) và sau (init duration 0ms). Note chi phí của provisioned concurrency setting vào Evidence Pack.

**Async Invocation + Dead Letter Queue:** cấu hình ít nhất một đường gọi Lambda dùng invocation type Event (async), gắn DLQ (SQS hoặc SNS), và demo invocation thất bại rơi vào DLQ — show message DLQ kèm chi tiết lỗi.

**S3-Event-Triggered Lambda Pattern:** một biến thể đơn giản chạy cho mọi nhóm bất kể có pipeline W4 hay không. Cấu hình S3 PutObject event notification trên một prefix (ví dụ bucket source của Bedrock KB, hoặc bất kỳ S3 location nào app ghi vào) để trigger Lambda đọc file mới, trích các field chính, và ghi vào DynamoDB. Nhóm có pipeline W4 có thể mở rộng thêm thành near-real-time analytics layer với Athena. Show flow end-to-end: thả một file, show CloudWatch log của Lambda, show output row trong DynamoDB.

**Pattern phải apply lên function thật trong ứng dụng đang có — không phải function tạo mới chỉ để làm bài.**

---

## Evidence Pack (Bắt buộc — Deliverable thứ sáu)

Tất cả ở trên phải được document trong một file markdown duy nhất: `docs/W5_evidence.md` commit vào repo của nhóm.

Evidence Pack phải có các mục:

1. Cover: group ID, thành viên, link repo, link tới evidence pack tuần trước
2. MH1 — Multi-VPC Connectivity: lựa chọn + rationale, screenshot route table, sample Flow Logs
3. MH2 — Firewall / Hardened SG+NACL: path đã chọn + rationale, screenshot liên quan, negative test
4. MH3 — File Storage + Backup Plan: bằng chứng mount, backup plan, recovery point, kết quả restore test có data
5. MH4 — API Gateway: cây resource, cấu hình auth, test curl (200 + 403)
6. MH5 — Scaling Pattern: pattern đã chọn, bằng chứng theo tiêu chí trên
7. Application Carry-Forward Verification: pipeline thực thi, Bedrock retrieval, database query — mỗi cái một screenshot
8. Negative Security Tests: ít nhất một cho mỗi bổ sung W5

**Xây Evidence Pack vừa làm vừa lưu — đừng để đến tối Thứ Năm.** Screenshot chụp trong lúc build luôn đáng tin hơn screenshot dựng lại trước Thứ Sáu.

Slide Thứ Sáu phải link ngược về Evidence Pack markdown. Trainer sẽ mở nó trong lúc chấm để verify mọi claim trong phần thuyết trình.

---

## Định dạng Friday Presentation

Vẫn bốn phần. Mục tiêu 10–12 phút tổng.

**Part 1 — Application Recap & Reflection (~1.5 phút):** show kiến trúc ứng dụng hiện tại. Chạy 1–2 action đại diện chứng minh app chạy đúng thiết kế (bạn chọn cái đại diện nhất). Cite một feedback cụ thể từ presentation trước và show W5 đáp lại thế nào.

**Part 2 — W5 Architecture (~3 phút):** show diagram cập nhật với cả năm bổ sung MH được gắn nhãn: lớp VPC connectivity, control firewall/security, EFS/FSx mount trong app tier, API Gateway trước Lambda, và scaling pattern apply lên một function cụ thể.

**Part 3 — QnA (~3 phút):** câu hỏi cá nhân từ trainer. Sẽ chấm trên chất lượng và độ sâu hiểu biết. Không tiết lộ chi tiết ở đây.

**Part 4 — Deployment Demo (~3–4 phút):** đi qua bằng chứng live: connectivity cross-VPC hoặc Flow Logs, một request bị chặn và một được cho phép, EFS/FSx mount với file đọc được, kết quả restore backup test, API Gateway 200 và 403, output scaling pattern, cộng action end-to-end của ứng dụng từ phần carry-forward.

---

## Stretch Goals (Tuỳ chọn)

Cho các nhóm hoàn tất cả năm must-haves và Evidence Pack trước chiều Thứ Năm:

- **VPC Reachability Analyzer:** dùng để verify một path connectivity, sau đó cố ý break một entry route table và chạy lại để xác nhận tool phát hiện được lỗi.
- **Backup Vault Lock:** cấu hình Vault Lock ở Compliance Mode — sau khi set, không IAM principal nào (kể cả root) xóa được recovery point trước khi retention hết.
- **Lambda Power Tuning:** chạy AWS Lambda Power Tuning trên function MH4 với nhiều mức memory và tìm điểm tối ưu cost-performance.
- **API Gateway custom domain:** gắn custom domain với ACM certificate vào stage API Gateway.
- **CloudFormation template cho một resource W5:** viết và validate CFN template cho Network Firewall, API Gateway, hoặc EFS.

Stretch goal cộng tối đa **+0.5** vào điểm tuần nhưng không bao giờ bắt buộc. **Một cái làm tử tế kèm document Evidence Pack đầy đủ đáng giá hơn ba cái làm dở.**

---

## "Done" trên Thứ Sáu trông như thế nào

Đến cuối phần thuyết trình Thứ Sáu, trainer phải có thể:

- Thấy ứng dụng chạy end-to-end trên deployment live (action nào chứng minh app chạy tốt nhất tùy bạn chọn)
- Đọc topology VPC của bạn và hiểu traffic đi đâu và vì sao
- Quan sát một request bị chặn và một được cho phép trong log của firewall hoặc NACL
- Mount path EFS/FSx của bạn trên một test instance và đọc data thật của ứng dụng
- Xác nhận backup vault có một recovery point Completed và restore test cho ra một resource đọc được
- Gọi endpoint API Gateway của bạn với auth hợp lệ (200) và không có auth (403) từ command line
- Thấy scaling pattern của Lambda đã cấu hình và đang tạo ra hành vi quan sát được

**Đó là "done".** Evidence Pack làm cho mọi thứ vẫn verify được sau khi bạn rời phòng.

Đây không phải xây cái mới từ con số không — đây là việc làm cho thứ bạn đã xây trở nên production-grade. Khoảng cách giữa prototype và hệ thống thật là: network quan sát được, security control ép buộc được, một lớp file sống sót khi scale, backup bạn đã thật sự test, và một surface API bảo vệ Lambda bên dưới. **Tuần này xây cái đó.**
