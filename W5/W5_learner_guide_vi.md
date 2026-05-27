# Tuần 5 — Network Fortress: Hardening lại những gì bạn đã xây

## Tuần này học gì

Đến lúc này, team bạn đã có một ứng dụng chạy được — với stack nào tùy bạn chọn trong W1–W4. Tuần 5 là tuần biến nó thành **production-ready**. Cụ thể: làm cho network quan sát được, ép buộc security ngay tại biên VPC, cấp cho tầng ứng dụng một lớp storage dùng chung tồn tại được khi scale, bảo vệ mọi tài nguyên có state bằng backup đã được test khôi phục, và đặt một lớp API tử tế trước Lambda. Đây là khoảng cách giữa "chạy được trong demo" và "chạy được trong điều kiện thật". Mỗi thứ vừa kể đều là việc cloud operations engineer làm ngay trong ngày đầu đi làm.

Ứng dụng team bạn phát triển từ W1 là **nền**. Tuần 5 thêm một **lớp vỏ cứng** bao quanh nó. Bên trong ứng dụng xây thế nào — stack gì, tích hợp AI ra sao, gọi service nào — vẫn là thiết kế của team. Tuần 5 chỉ định lớp hardening, không chỉ định ứng dụng.

---

## Trọng tâm theo ngày

### Thứ Hai — Networking Foundations + Network Security

**Khoá học hôm nay:**
- Configuring and Deploying VPCs with Multiple Subnets (1h, Digital Course) — Bắt buộc
- Introduction to Amazon Virtual Private Cloud (VPC) (1h, Lab) — Bắt buộc
- AWS Network Connectivity Options (2h 30m, Digital Course) — Bắt buộc (phần VPC Peering và Transit Gateway); Tự học (phần Direct Connect)
- AWS SimuLearn: Connecting VPCs (1h, Lab) — Bắt buộc
- AWS Network – Monitoring and Troubleshooting (1h, Digital Course) — Bắt buộc
- AWS Network Firewall Getting Started (1h, Digital Course) — Bắt buộc

**Nội dung chính**: thiết kế subnet trong VPC, lập kế hoạch CIDR, VPC Peering vs Transit Gateway, Site-to-Site VPN, VPC Flow Logs, Reachability Analyzer, AWS Network Firewall stateful rules và IDS/IPS.

**Cần đặc biệt chú ý:**

- Quyết định connectivity cho MH1 quy về hai câu hỏi: "Tôi có bao nhiêu VPC?" và "Tôi có cần transitive routing không?" Hai hoặc ba VPC, CIDR không chồng, không cần transitive routing → **VPC Peering**. Ba VPC trở lên, hoặc cần hub-and-spoke, hoặc dự định thêm VPN sau → **Transit Gateway**. Nếu thực sự chỉ có một VPC được thiết kế tốt thì vẫn justify được — nhưng phải có justification cụ thể cho kiến trúc của team, không phải câu chữ chung chung.

- **VPC Peering KHÔNG transitive.** Nếu VPC A peer với VPC B, VPC B peer với VPC C, thì VPC A vẫn không tới được VPC C. Mỗi kết nối phải direct. Gần như sinh viên nào lần đầu cũng bị bất ngờ chỗ này.

- **Network Firewall** là course mới nhất trong toàn bộ syllabus W5. Đa số sinh viên đến Thứ Hai với zero kinh nghiệm trước đó. Tập trung kỹ và hỏi nhiều trong buổi Q&A buổi chiều — checkpoint Thứ Hai sẽ có câu Network Firewall, QnA Thứ Sáu rất có thể cũng có. Ý quan trọng nhất: Network Firewall **chỉ chặn được traffic nếu route table của bạn thật sự đẩy traffic qua firewall endpoint**. Không sửa route table = firewall đã deploy nhưng không thấy gì cả.

- **VPC Flow Logs là bắt buộc cho MH1** — bất kể bạn chọn path nào. Bật trên tất cả VPC và publish về CloudWatch Logs hoặc S3. Sample log entry phải xuất hiện trong Evidence Pack.

**Mẹo thực hành:**
- Trong lab Connecting VPCs, sau khi accept peering connection, kiểm tra route table cả hai bên ngay — accept thôi chưa đủ. Route table của cả hai VPC phải có entry trỏ về peering connection. Test connectivity bằng curl hoặc ping trước khi gọi là xong.
- Trong course Network Firewall, vẽ route path ra giấy: private subnet → firewall subnet (firewall endpoint) → NAT Gateway → internet. Nếu bỏ qua bước vẽ, bước cấu hình route table sẽ không hiểu nổi.

---

### Thứ Ba — File Storage & Backup

**Khoá học hôm nay:**
- AWS File Storage Services Getting Started (2h, Digital Course) — Bắt buộc
- Amazon EFS Primer (30m, Digital Course) — Bắt buộc
- AWS SimuLearn: File Systems in the Cloud (1h, Lab) — Bắt buộc
- AWS Backup Getting Started (1h, Digital Course) — Bắt buộc

**Nội dung chính**: khung quyết định S3 vs EFS vs FSx (Windows, Lustre, NetApp ONTAP, OpenZFS), cấu hình EFS (NFSv4, Standard vs One Zone, Elastic/Bursting/Provisioned throughput, lifecycle to IA), AWS Backup plans và vaults, Vault Lock, cross-region copy, restore testing.

**Cần đặc biệt chú ý:**

- Quyết định file storage không phải tùy tiện — nó phụ thuộc OS và access pattern. **EFS dùng NFSv4, chỉ chạy trên Linux và macOS.** Nếu tầng app là Windows, EFS không mount được. Phải dùng FSx for Windows File Server. Với workload high-performance parallel (HPC, ML training), FSx for Lustre mới đúng. Đa số nhóm trong chương trình sẽ dùng EFS.

- **EFS encryption at rest chỉ bật được lúc tạo file system** — không bật ngược lại được. Nếu nhóm bạn lỡ tạo EFS test mà chưa bật encryption, tạo cái mới có encryption trước Thứ Năm.

- **Restore test là bước quan trọng nhất của MH3** và là bước sinh viên hay bỏ qua nhất. Tạo backup plan và thấy recovery point trong vault **chưa đủ**. Bạn phải khôi phục từ recovery point thành một resource mới, kiểm tra restore job báo Completed, và kiểm tra đọc được data thật từ resource đã khôi phục. **Chạy restore job vào chiều Thứ Ba** — restore mất thời gian và bạn muốn có status Completed trước khi spot-check Thứ Năm.

**Mẹo thực hành:**
- Trong lab File Systems, trước khi gõ bất kỳ lệnh mount nào, check hai thứ: (1) instance là Linux không phải Windows, và (2) security group của mount target cho phép TCP port 2049 từ security group của instance. Sai một trong hai = lệnh mount sẽ treo im lặng.
- Với AWS Backup: sau khi tạo backup plan và thấy "Completed" trên backup job đầu tiên, **trigger restore ngay**. Chọn recovery point, chọn destination mới (EFS mới, RDS instance mới), khởi động restore job. Đừng đợi đến Thứ Năm.
- EFS lifecycle policy: set chuyển file sang Infrequent Access (IA) sau 30 ngày. Đây là setting một click trong console EFS và cắt giảm chi phí storage cho file ít truy cập — không phải sửa code gì cả.

---

### Thứ Tư — Serverless & API Gateway

**Khoá học hôm nay:**
- Introduction to Amazon API Gateway (1h, Lab) — Bắt buộc
- Architecting Serverless Applications (2h, Digital Course) — Bắt buộc
- Scaling Serverless Architectures (1h 30m, Digital Course) — Bắt buộc
- Serverless Analytics (25m, Digital Course) — Khuyến nghị

**Nội dung chính**: API Gateway types (REST, HTTP, WebSocket), Lambda proxy integration, throttling và usage plans, authorizers, event-driven architecture patterns, choreography vs orchestration, cold start, idempotency, reserved concurrency, provisioned concurrency, DLQ cho async retry, S3-event-triggered analytics.

**Cần đặc biệt chú ý:**

- **REST API vs HTTP API**: HTTP API rẻ hơn tới 71% và độ trễ thấp hơn. REST API hỗ trợ usage plan với API key và throttling theo từng method, là cái đa số implementation MH4 sẽ dùng. Cả hai đều được chấp nhận cho MH4 — nhưng phải justify lựa chọn trong Evidence Pack.

- **Format response của Lambda proxy integration quan trọng cho MH4**: Lambda phải trả về JSON object có statusCode, headers, và body. Nếu Lambda trả về cái khác (raw string, XML, object thiếu statusCode), API Gateway sẽ trả 502 về client — không phải Lambda lỗi, mà là Gateway lỗi format.

- **Throttle và quota là hai setting độc lập trên usage plan.** Throttle = requests/giây (rate + burst). Quota = tổng requests theo ngày hoặc tháng. Hết quota trong khi function đang idle (zero Lambda invocation trong CloudWatch) nghĩa là quota cạn ở tầng API Gateway — request không bao giờ tới Lambda.

- **Reserved concurrency và provisioned concurrency KHÔNG giống nhau.** Reserved concurrency = giới hạn cứng số concurrent invocation cho một function (bảo vệ các function khác không bị nuốt hết quota). Provisioned concurrency = execution environment được pre-warm (loại bỏ cold start). Một function có thể có cả hai. Reserved concurrency = 0 nghĩa là function không invoke được — kể cả vô tình.

**Mẹo thực hành:**
- Trong lab API Gateway, sau khi deploy REST/HTTP API, chạy hai lệnh curl: một có API key/Authorization header đúng (kỳ vọng 200), một không có (kỳ vọng 403). Screenshot cả hai. Đây là hai screenshot Evidence Pack cho MH4.
- Cho MH5, chọn scaling pattern **trước Thứ Năm**: reserved concurrency (cap function + show metric Throttles trong CloudWatch), provisioned concurrency (so sánh Init Duration trước/sau trong CloudWatch), async invocation + DLQ (gây failure và show event rơi vào DLQ), hoặc S3-event-triggered analytics pipeline (PutObject → Lambda → DynamoDB hoặc Athena, end-to-end). Apply lên function thật đang có — không phải function tạo mới cho bài tập.
- Course Serverless Analytics (25 phút): nếu nhóm bạn có batch pipeline (Glue / Kinesis / etc.), course này dạy thêm layer near-real-time với S3 events và Lambda — một trong bốn pattern hợp lệ cho MH5. Nếu app không có batch pipeline, cùng pattern S3-event-Lambda vẫn dùng được như demo MH5 độc lập.

---

### Thứ Năm — Review và chốt bài

Dùng Thứ Năm để củng cố nội dung Mon–Wed và **chốt 5 must-haves trước Thứ Sáu**.

**Buổi sáng**: trainer review top những hiểu nhầm phổ biến từ Kahoot checkpoint. Tập trung kỹ nếu các chủ đề này xuất hiện: VPC Peering non-transitive, route table cho Network Firewall, EFS chỉ chạy Linux, reserved vs provisioned concurrency, hoặc phân biệt quota vs throttle trong API Gateway.

**Hoạt động nhóm — W5 Architecture Hardening:**

Đi qua 5 must-haves theo thứ tự:

1. **MH1**: xác nhận connectivity choice đã có rationale và Flow Logs bật trên mọi VPC. Show sample log entry với ACCEPT hoặc REJECT trong Evidence Pack.
2. **MH2**: xác nhận firewall path. Nếu deploy Network Firewall, show firewall endpoint trong dedicated subnet và route table đẩy traffic qua đó trước NAT Gateway. Nếu đi hardened SG+NACL path, show NACL DENY rule rõ ràng và screenshot negative test. Lưu ý: **nếu bất kỳ EC2 hay Lambda nào trong stack ra internet qua NAT Gateway, bắt buộc đi path Network Firewall.**
3. **MH3**: xác nhận EFS/FSx đã mount lên instance ở app tier trong private subnet và đã ghi/đọc được một file có ý nghĩa. Xác nhận backup plan bao trùm file system + database W3 + EBS volume W2. Xác nhận restore test job báo Completed và data đọc được từ resource đã khôi phục.
4. **MH4**: chạy test 200 (authenticated) và 403 (unauthenticated) cho API Gateway và thêm cả hai screenshot vào Evidence Pack. Xác nhận code ứng dụng đã thay thế đường gọi Lambda trực tiếp cũ.
5. **MH5**: xác nhận scaling pattern apply lên function thật với bằng chứng CloudWatch. Thêm pattern rationale + screenshot vào Evidence Pack.

Post architecture diagram cập nhật và link Evidence Pack vào kênh Slack trainer **trước 17:00 Thứ Năm**.

---

### Thứ Sáu — Show What You Know

Mỗi nhóm thuyết trình theo bốn phần (~10–12 phút tổng):

1. **Part 1 — Application Recap & Reflection (~1.5 phút)**: show kiến trúc ứng dụng hiện tại, nêu **một** feedback cụ thể từ buổi presentation tuần trước, và show cụ thể W5 fix nó thế nào. Đồng thời chạy 1–2 action đại diện trên deployment live chứng minh app hoạt động end-to-end (bạn chọn action nào tiêu biểu nhất — request qua API, downstream call trả về data, action admin, v.v.). Nếu app không deployed hoặc không chạy end-to-end vào Thứ Sáu, **Criterion II cap ở 3**.

2. **Part 2 — W5 Architecture (~3 phút)**: show diagram cập nhật với cả 5 must-haves được gắn nhãn rõ. Đi từng cái: connectivity decision + sample Flow Log entry, firewall path + justification, EFS/FSx mount + backup plan + restore test result, API Gateway có throttling + auth, scaling pattern apply lên function thật.

3. **Part 3 — Individual QnA (~3 phút)**: 2–3 thành viên được gọi tên. Mọi thành viên đều có thể bị gọi — cả team sở hữu các quyết định này.

4. **Part 4 — Deployment / Live Demo (~3–4 phút)**: show một blocked request trong Alert Log hoặc test NACL deny, show một file ghi/đọc trên EFS/FSx mount, show test 200/403 của API Gateway, và show bằng chứng scaling pattern trong CloudWatch. Nếu live action bị hỏng, **screenshot trong Evidence Pack** của chính action đó được tính như evidence thay thế — không bị trừ. Thiếu cả live lẫn screenshot = **Criterion IV cap ở 2**.

Bảo đảm diagram khớp với deployment, và Evidence Pack khớp với phần thuyết trình. Trước Thứ Sáu, post commit link `docs/W5_evidence.md` vào kênh Slack trainer. Slide không có link tới Evidence Pack = **Criterion IV cap ở 3**.

---

## Deliverables tuần này

Đến Thứ Sáu nhóm phải nộp:

1. **MH1 — Multi-VPC Connectivity**: connectivity decision có document (VPC Peering với route table cập nhật cả hai bên + connectivity test, hoặc Transit Gateway với attachment + TGW route table + connectivity test, hoặc justified single-VPC với subnet multi-AZ + rationale viết tay); VPC Flow Logs bật trên mọi VPC với sample log entry trong Evidence Pack. Redeploy với cùng topology VPC team đã thiết kế từ tuần trước — cùng CIDR plan, cùng tầng subnet — và thêm lớp connectivity lên trên.

2. **MH2 — Network Firewall Hardening**: deploy AWS Network Firewall (firewall subnet riêng, stateful rule group có domain allowlist hoặc IPS rule, Alert Logs bật, route table cập nhật, **một blocked request hiển thị trong Alert Logs**) HOẶC hardened SG+NACL (justification viết tay, không có 0.0.0.0/0 trên port 22/3389, NACL DENY rule rõ ràng, screenshot negative test). Nếu bất kỳ Lambda hay EC2 nào ra internet qua NAT Gateway, **không được dùng path SG+NACL**.

3. **MH3 — File Storage Layer + Backup Plan**: EFS hoặc FSx mount lên ít nhất một instance ở app tier trong private subnet, phục vụ content thật của ứng dụng, SG của mount target chỉ allow từ SG app tier (không phải 0.0.0.0/0); AWS Backup plan bao trùm file system + database W3 + EBS volume W2, ít nhất một recovery point Completed trong vault, **restore test đã hoàn tất và data đọc được** từ resource đã khôi phục.

4. **MH4 — API Gateway + Auth + Throttling**: ít nhất một Lambda endpoint hiện có được thay bằng API Gateway (REST hoặc HTTP API) với Lambda proxy integration, usage plan có rate + burst throttling, và authentication (API Key, Lambda Authorizer, hoặc Cognito); request có auth trả 200, không auth trả 403; code ứng dụng đã thay đường gọi trực tiếp cũ.

5. **MH5 — Serverless Scaling Pattern**: một scaling pattern thật apply lên function đang có — reserved concurrency (cap + throttle evidence trong CloudWatch), provisioned concurrency (so sánh Init Duration cold-start vs warm-start), async invocation + DLQ (event lỗi rơi vào DLQ được demo), hoặc S3-event-triggered analytics pipeline (PutObject → Lambda → DynamoDB hoặc Athena, end-to-end); **apply lên function thật**, không phải function test mới.

6. **Evidence Pack** (`docs/W5_evidence.md`): chín mục — Cover, MH1, MH2, MH3, MH4, MH5, Application Carry-Forward Verification, Negative Security Test, Bonus (tuỳ chọn). Mỗi mục có screenshot kèm note cấu hình 1–2 dòng. Slide Thứ Sáu xuất từ file này — copy screenshot vào slide, link ngược về commit. W5 thêm lớp vỏ hardening vào ứng dụng của bạn — **cùng kiến trúc, cùng business domain** như tuần trước, redeploy trên workshop account với các bổ sung W5.

---

## Cách chấm điểm

- **Group (Criterion II, 20%)**: cả 5 must-haves có được implement đúng và đặt đúng vị trí trong kiến trúc không? Team có defend được các lựa chọn (vì sao Peering vs TGW, vì sao Firewall vs SG+NACL, vì sao EFS vs FSx, vì sao chọn scaling pattern đó)?
- **Individual QnA (Criterion III, 30%)**: khả năng giải thích quyết định topology, rationale firewall, hành vi Lambda concurrency khi bị gọi — độ chính xác, logic, và liên hệ với project cụ thể của bạn. Mọi thành viên đều có thể bị gọi.
- **Deployment and Evidence (Criterion IV, 40%)**: phần nặng nhất. Chấm theo Evidence Pack markdown, từng mục. **Không có Evidence Pack = cap ở 2.** Screenshot không có note = cap ở 3. Đủ 5 mục MH với screenshot + note + application carry-forward verification + negative test = 4. Có thêm bằng chứng restore test toàn vẹn data và metric concurrency = 5. Slide phải link tới Evidence Pack commit — không link = cap ở 3.
- **Recap and Reflection (Criterion I, 10%)**: có cite feedback cụ thể từ buổi trước và show W5 đáp lại thế nào không? Có chạy end-to-end action chứng minh ứng dụng chạy live không?
- **Daily checkpoints**: Kahoot game Thứ Hai đến Thứ Tư tính vào điểm.
- **Peer evaluation**: đồng đội đánh giá đóng góp của bạn hàng tuần.

---

## Pro Tips

- **Chạy restore test vào chiều Thứ Ba.** Restore job mất thời gian. Đợi đến sáng Thứ Năm thì job có thể vẫn In Progress lúc spot-check, và bạn sẽ không có screenshot Completed cho Evidence Pack.
- **Vẽ đường traffic Network Firewall ra giấy trước khi đụng console.** Cấu hình route table là bước hay bị quên nhất. Traffic phải đi qua firewall endpoint trong firewall subnet trước khi tới NAT Gateway. Nếu route table đẩy thẳng tới NAT Gateway, firewall không thấy gì.
- **Chạy auth test API Gateway sớm.** 200 với API key và 403 không có key chỉ mất 2 phút và cho ra hai trong số screenshot quan trọng nhất của MH4. Làm vào chiều Thứ Tư sau lab, không phải tối Thứ Năm.
- **Apply MH5 lên function đang làm việc thật.** Scaling pattern phải trên một function đang có trong ứng dụng. Tạo hello-world mới cho MH5 = không tính. Ứng viên tốt: Lambda đứng sau API Gateway MH4, S3-event handler trong stack của bạn, hoặc bất kỳ function nào đang xử lý backend thực sự.
- **EFS và Windows không hợp nhau.** Nếu có bất kỳ instance app tier nào là Windows, dùng FSx for Windows File Server (SMB) thay vì EFS (NFSv4). Trộn lẫn sẽ fail âm thầm và đốt thời gian debug.

---

## AWS Services trọng tâm tuần này

| Service | Làm gì | Vì sao quan trọng cho project |
|---------|--------|-------------------------------|
| Amazon VPC | Network riêng trong AWS với subnet, route table, gateway | Mọi service trong kiến trúc đều nằm ở đây; W5 làm topology trở nên có chủ đích và quan sát được |
| VPC Peering | Kết nối private trực tiếp giữa hai VPC có CIDR không chồng | Một trong hai path cho MH1 — point-to-point, non-transitive |
| AWS Transit Gateway | Hub-and-spoke gateway nối nhiều VPC qua trung tâm | Path còn lại cho MH1 — bắt buộc khi có 3+ VPC hoặc cần transitive routing |
| VPC Flow Logs | Ghi nhận thông tin lưu lượng IP cho từng ENI trong VPC | Bắt buộc cho MH1: chứng minh traffic chảy (hoặc bị chặn) trên các đường đã thiết kế |
| AWS Network Firewall | Stateful firewall và IDS/IPS managed tại biên VPC (engine Suricata) | MH2 path A: bắt và inspect traffic trước NAT Gateway; Alert Logs chứng minh enforcement |
| Amazon EFS | File system shared elastic dùng NFSv4, mount đồng thời từ nhiều EC2 Linux | MH3 file storage: thay EBS riêng từng instance bằng storage chung cho cả app tier |
| Amazon FSx | Họ file system managed: Windows (SMB+AD), Lustre (HPC+S3), NetApp ONTAP (đa protocol), OpenZFS | MH3 phương án thay EFS khi OS, protocol hoặc yêu cầu throughput khác |
| AWS Backup | Backup service tập trung theo policy, bao trùm EFS, EBS, RDS, DynamoDB, EC2, S3 | MH3 backup plan: một plan bao trùm mọi resource có state từ W2; Vault Lock chống xóa |
| Amazon API Gateway | Lớp API managed (REST, HTTP, WebSocket) có throttling, auth, tích hợp Lambda | MH4: thay invocation Lambda trực tiếp bằng một surface API tử tế ép buộc throttling và auth |
| AWS Lambda | Compute serverless theo event, trigger bởi API Gateway, S3, các nguồn khác | Backend của MH4; scaling pattern MH5 apply lên function đang có |
| Reachability Analyzer | Tool phân tích cấu hình tĩnh để test connectivity giữa hai resource không cần gói thật | Tool troubleshoot: dùng khi connectivity hỏng và cần tìm rule chặn mà không phải đoán |
