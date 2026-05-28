# W7 Evidence Pack — BudgetBot (FinTech: AI Money Coach)

**Nhóm:** G4

**Thành viên:**
- Ngô Nguyễn Trường An (ngonguyentruongan2907@gmail.com)
- Phạm Hữu Tiến Thành (tienthanh711204@gmail.com)
- Nguyễn Huy Hoàng (nguyenvanhuyhoang2609@gmail.com)
- Nguyễn Phú Tài (ddor2812@gmail.com)
- Cái Xuân Hoà (xuanhoa2004tt@gmail.com)
- Phan Hoàng Nhật (nhatphanhk102@gmail.com)

**Live URL:** https://xbrain26hackathon269.software/
**Repo link:** https://github.com/dragoncoil2609/w7-budgetbot.git
**Domain choice:** Domain B — FinTech: "AI Money Coach"
**Total spend:**

---

## 1. Lĩnh vực & Use Case

### 1.1 Vấn đề cần giải quyết
Sao kê ngân hàng đã mã hóa và nằm rải rác trên nhiều định dạng (PDF, CSV). Người dùng gặp khó khăn trong:
- Phân loại giao dịch thủ công (tốn thời gian, dễ sai)
- Hiểu được mô hình chi tiêu qua các tháng
- Lập và theo dõi mục tiêu ngân sách
- Trả lời "Tiền của tôi đã đi đâu?" mà không cần đối chiếu thủ công

### 1.2 Giải pháp — BudgetBot
**Tagline:** Tải lên sao kê của bạn. Hiểu chính xác tiền của bạn đã đi đâu.

**Quy trình người dùng cơ bản:**
1. Người dùng đăng nhập qua Cognito → lấy Token truy cập hệ thống.
2. Tải lên sao kê (PDF hoặc CSV) qua S3 Presigned URL.
3. Backend phân tích sao kê (xử lý bất đồng bộ qua SQS) → AI phân loại từng giao dịch.
4. Dashboard hiển thị phân tích, theo dõi ngân sách, xu hướng chi tiêu.

### 1.3 Tại sao chọn use case này (Dưới góc nhìn Technical)?
- **Giải quyết bài toán Data Pipeline điển hình:** Việc trích xuất dữ liệu thô từ file (S3) -> làm sạch & phân tích (Lambda + Bedrock) -> lưu trữ có cấu trúc để truy vấn (RDS) là một luồng xử lý dữ liệu tiêu chuẩn, cho phép team phô diễn kỹ năng kết nối các dịch vụ cốt lõi của AWS.
- **Tính chất "Burst Traffic" lý tưởng để demo Serverless:** Hành vi người dùng thường dồn dập upload sao kê vào cuối tháng. Đặc thù traffic "lúc bùng nổ, lúc trống trơn" này là sân khấu hoàn hảo để trình diễn sức mạnh kiến trúc Serverless: Scale-to-Zero tiết kiệm tiền khi rảnh rỗi, và dùng hàng đợi SQS làm buffer chống sập hệ thống (Anti-Spike) khi tải cao.
- **Xử lý Unstructured Data bằng AI-native:** Dữ liệu sao kê ngân hàng ở Việt Nam rất lộn xộn, viết tắt, không theo chuẩn. Thay vì phải bảo trì hàng nghìn dòng code Regex (Regular Expression) cứng nhắc, việc ứng dụng LLM (**Amazon Nova Lite 2** qua Bedrock) giúp biến đổi dữ liệu phi cấu trúc thành dữ liệu có cấu trúc (Structured Data) một cách linh hoạt, minh chứng giá trị thực tiễn của AI.

---

## 2. Các Bước Triển Khai Dự Án (Deployment Pipeline)

Dự án BudgetBot được triển khai theo 4 bước kiến trúc lớn để từ một MVP trở thành "Production-Ready":

1.  **Thiết lập Hạ tầng Cơ sở (Infrastructure Base):**
    *   **Mạng & Database:** Tạo VPC, thiết lập Private Subnet cho Database (Amazon RDS PostgreSQL) để đảm bảo cô lập mạng.
    *   **Backend Compute:** Khởi tạo kho lưu trữ Amazon ECR (để chứa Docker Image của code Python) và cấu hình AWS Lambda chạy Container Image. Thiết lập HTTP API Gateway làm cổng giao tiếp.
    *   **Frontend & Storage:** Tạo S3 Bucket cho Frontend, S3 Bucket cho upload sao kê gốc, và cấu hình CloudFront CDN để phân phối HTTPS.
2.  **Tự động hóa CI/CD Pipeline:**
    *   Thiết lập GitHub Actions. Mỗi khi code được push lên nhánh `main`:
        *   Frontend: Tự động build React (Vite) và sync lên S3, clear cache CloudFront.
        *   Backend: Build Docker Image, đẩy lên Amazon ECR, và cập nhật code cho AWS Lambda.
    *   *(Hình ảnh bằng chứng: Ảnh chụp màn hình GitHub Actions báo Xanh/Success)*
    *   ![CI/CD Pipeline Success](./image/cicd-success.png)
3.  **Tối ưu luồng Upload File lớn (SQS + Presigned URL):**
    *   Chuyển đổi từ luồng upload đồng bộ (qua Lambda) sang bất đồng bộ: Frontend xin **Presigned URL** từ Lambda, rồi đẩy file thẳng lên S3.
    *   Sau khi upload S3 thành công, Frontend gọi API `/enqueue` để Lambda API đẩy một message chứa thông tin job vào hàng đợi **Amazon SQS**.
    *   Cùng một Lambda đó (nhưng được SQS trigger với vai trò "Worker") sẽ kéo message từ hàng đợi để từ từ xử lý AI nền (gọi Bedrock), tránh bị timeout API Gateway 29s.
4.  **Bảo mật Xác thực (Cognito + API Gateway):**
    *   Tạo AWS Cognito User Pool.
    *   Sử dụng script PowerShell (`setup_auth.ps1`) để gắn JWT Authorizer vào các route của HTTP API Gateway. Chỉ request có token hợp lệ mới được đi vào Lambda.
    *   *(Hình ảnh bằng chứng: Ảnh chụp màn hình API Gateway có gắn JWT Authorizer)*
    *   ![API Gateway JWT Authorizer](./image/api-gateway-authorizer.png)

---

## 3. Kiến trúc & 7 Khả năng Bắt buộc

### 3.1 Sơ đồ kiến trúc logic

*(Hình ảnh bằng chứng: Sơ đồ kiến trúc AWS chi tiết)*
![Sơ đồ kiến trúc AWS](./image/architecture-diagram.png)

### 3.2 Bảy khả năng bắt buộc (Must-Haves): Bước Thực Hiện & Lựa Chọn Service

| # | Năng lực Bắt buộc | Dịch vụ & Bước thực hiện | Lý do (Trade-off & Bảo vệ phương án) |
|---|---|---|---|
| 1 | **User Interface** | **S3 + CloudFront + WAF:** Host tĩnh React trên S3, phân phối qua CloudFront có bật WAF. | Tối ưu chi phí (gần như $0). **CDN cache** tải trang siêu tốc. Gắn thêm **AWS WAF (Layer 7)** ở biên mạng (Edge) chặn đứng DDoS và SQL Injection ngay từ ngoài cửa. |
| 2 | **Application Compute** | **AWS Lambda:** Dùng Lambda chạy Docker Image bọc FastAPI qua thư viện Mangum. | Chạy **Event-driven** và **Scale-to-Zero** giúp tiết kiệm tiền tối đa lúc không có khách. Dùng **Docker Image** giúp vượt giới hạn code 250MB để chạy thư viện xử lý PDF phức tạp. |
| 3 | **AI / ML Feature** | **Bedrock (Nova):** Dùng InvokeModel (Amazon Nova Lite 2) với ThreadPoolExecutor (20 luồng). | **Kiến trúc Hybrid:** Lọc rule-based cục bộ trước, từ nào khó mới gọi AI để **tiết kiệm 80% phí token**. Nova Lite 2 siêu rẻ và có tốc độ xử lý cực nhanh. |
| 4 | **Data Persistence** | **RDS PostgreSQL:** Triển khai Multi-AZ (Primary + Read Replica) với dòng chip t4g siêu rẻ. | **Vượt giới hạn Free Tier:** Nhóm đã cấu hình thành công Multi-AZ để đảm bảo High Availability. Riêng RDS Proxy bị tài khoản Free Tier cấm tạo, nhóm lập tức đổi chiến thuật: Dùng **SQS Buffer** thay thế Proxy để điều tiết luồng ghi, triệt tiêu Connection Spike hoàn hảo. |
| 5 | **Object Storage** | **S3 Bucket:** Lưu sao kê gốc. Áp dụng cơ chế Presigned URL. | S3 là kho lưu trữ Object hoàn hảo. **Presigned URL** cho phép khách hàng upload thẳng file GB lên S3 mà không bị giới hạn 6MB payload của API Gateway. |
| 6 | **Network Foundation** | **VPC (Private RDS):** Đặt DB vào Private Subnet. Dùng VPC Interface Endpoint. | Cô lập hoàn toàn DB khỏi Internet. Việc dùng **VPC Interface Endpoint** gọi nội bộ tới Bedrock thay vì dùng NAT Gateway giúp **tiết kiệm ~$1.08/ngày**. |
| 7 | **Identity & Access** | **Cognito + IAM:** Gắn JWT Authorizer vào API Gateway, IAM Least-Privilege. | **Edge Security (Bảo mật tại cổng):** Cognito chặn request mạo danh ngay tại API Gateway, Lambda không bị đánh thức, **tiết kiệm 100% compute** cho request rác. |

### 3.3 Bằng chứng cấu hình (AWS Console Screenshots)

Để chứng minh hệ thống thực sự được triển khai theo đúng chuẩn, dưới đây là các hình ảnh chụp thực tế từ AWS Console:

*(Lưu ý: Đổi tên ảnh tương ứng và đưa vào thư mục `image`)*

**1. Bằng chứng hạ tầng mạng & Compute (VPC Endpoints & Lambda):**
![Bằng chứng VPC và Lambda](./image/evidence-vpc-lambda.png)

**2. Bằng chứng Database (RDS Multi-AZ):**
![Bằng chứng RDS](./image/evidence-rds.png)

**3. Bằng chứng Frontend (CloudFront & S3):**
![Bằng chứng CloudFront](./image/evidence-cloudfront.png)

---

## 4. Các quyết định kiến trúc chính (Chống sập & Giảm tải)

### 4.1 Xử lý Upload File Lớn: SQS Async vs. Đồng bộ (Sync)
- **Quyết định:** Chuyển từ luồng Upload gọi API trực tiếp sang cấu trúc Bất đồng bộ (S3 Presigned URL + SQS Queue).
- **Lý do & Tác dụng Giảm tải:** 
  - **Tránh Timeout:** API Gateway có giới hạn cứng 29 giây. Xử lý file lớn hàng nghìn dòng bằng AI chắc chắn vượt 29s gây sập API.
  - **Buffer giảm tải (Anti-Spike):** SQS làm hàng đợi trung gian (buffer). Dù 1000 user upload file cùng lúc, SQS sẽ từ từ "nhỏ giọt" message xuống Lambda Worker. 
  - **Chịu tải vô cực:** DB RDS không bị bùng nổ kết nối (Connection Spike), API không bao giờ timeout. Đảm bảo trải nghiệm êm mượt mà không phải scale phần cứng tốn tiền.

### 4.2 Lựa chọn DB: RDS PostgreSQL vs. DynamoDB
- **Lý do:** BudgetBot cần Query phân tích phức tạp. DynamoDB tuy không có cold-start nhưng giới hạn về query phân tích. Nhóm triển khai **Multi-AZ trên chip ARM t4g.micro** để đạt chuẩn High Availability trong khi vẫn tối ưu triệt để chi phí. Chấp nhận trả thêm phí duy trì RDS đổi lại năng lực thống kê báo cáo mạnh mẽ.

### 4.3 Bảo mật tại cổng (Edge Security): WAF + Cognito
- **Quyết định:** Không để phần backend (Lambda) tự lo bảo mật. Chuyển toàn bộ trọng trách phòng thủ ra lớp biên mạng (Edge Layer).
- **Lý do & Tác dụng Giảm tải:** 
  - **AWS WAF (gắn tại CloudFront):** Chặn đứng các đòn tấn công phổ biến (DDoS, SQL Injection) và giới hạn Rate Limiting ngay từ "ngoài cửa".
  - **Cognito JWT Authorizer (gắn tại API Gateway):** Từ chối ngay lập tức các request mạo danh, không có token hợp lệ.
  - **Kết quả:** Thay vì để Request rác lọt vào trong đánh thức Lambda (gây tốn tiền Compute vô ích), kiến trúc này tiêu diệt hiểm họa từ vòng gửi xe. **Tiết kiệm 100% chi phí xử lý request rác!**

---

## 5. Các Bước Hoàn Thành Bonus (Điểm Cộng)

1.  **[B] CI/CD Pipeline (Tự động hóa toàn diện):**
    *   **Bước thực hiện:** Viết Github Actions workflow. Pipeline bao gồm: Docker build -> ECR Push -> Lambda Update -> Node.js build -> S3 Sync -> CloudFront Invalidation.
    *   **Tác dụng:** Giảm thời gian release tính năng từ 15 phút làm thủ công xuống còn ~47 giây.
2.  **[C] Custom Domain + HTTPS (Giao diện chuyên nghiệp):**
    *   **Bước thực hiện:** Đăng ký tên miền `xbrain26hackathon269.software` trên Route 53. Xin chứng chỉ miễn phí AWS ACM và gắn vào CloudFront.
    *   **Tác dụng:** Ứng dụng live với tên miền chuyên nghiệp, có ổ khóa xanh HTTPS đảm bảo an toàn.
3.  **[G] Cost Optimization (Tối ưu hóa và giám sát chi phí):**
    *   **Bước thực hiện:** (1) Dùng mô hình Amazon Nova Lite 2 thay vì các mô hình đắt tiền. (2) SQS bất đồng bộ chống nâng memory Lambda. (3) Dùng VPC Endpoint thay NAT. (4) Cấu hình Cost Anomaly Detection (ngưỡng >$10).
    *   **Tác dụng:** Chi phí thấp kỷ lục, không sợ hóa đơn đột biến.
4.  **[O] Full Observability (Giám sát toàn diện hệ thống):**
    *   **Bước thực hiện:** Xây dựng **CloudWatch Dashboard** cho API (5XX, Latency), Lambda (Errors), SQS (Oldest Message), RDS (Connections) và Custom Metrics.

---

## 6. Phân tích chi phí (Bonus #9 - Advanced Cost Insights)

### 6.1 Ước tính chi phí 48H vs Thực tế
*(Học viên tự điền chi phí thực tế vào sáng Demo Day dựa trên Cost Explorer)*
- **Ngân sách tối đa:** $100
- **Chi phí dự kiến 48h:** ~$5.60 (Tối ưu cực đoan)
- **Top 3 Cost Drivers:** 
  - **RDS Multi-AZ:** ~$3.80 (Sự đánh đổi xứng đáng: Chi thêm tiền để hệ thống Sẵn sàng cao, không bị sập).
  - **VPC Endpoint:** ~$1.20 (Vẫn rẻ hơn rất nhiều so với việc dùng NAT Gateway ~$2.16/48h).
  - **Bedrock Nova Lite 2:** ~$0.60 (Tiết kiệm 80% token nhờ kiến trúc kết hợp Rule-based lọc trước).

### 6.2 Bằng chứng AWS Cost Explorer
![AWS Cost Explorer](./image/evidence-cost-explorer.png)


---

## 7. Triển khai Bảo mật (Security First)

1. **IAM Least-Privilege:** Không dùng wildcard hay Admin. Lambda role được scope nhỏ nhặt đến mức từng bucket name và model ARN.
2. **Edge Security (Bảo mật biên mạng):** Kết hợp chặt chẽ **AWS WAF** và **Cognito JWT Authorizer** để chặn đứng DDoS, SQL Injection và các request nặc danh ngay tại lớp ngoài cùng (CloudFront & API Gateway), bảo vệ tuyệt đối cho Backend bên trong.
3. **Mạng lưới kín (VPC):** RDS không Public IP. Dữ liệu chạy nội bộ qua AWS Backbone network bằng VPC Endpoint.

---

## 8. Giám sát Toàn diện (Full Observability - Bonus #8)

Hệ thống BudgetBot đã chuyển từ "chạy mù" sang "có thể quan sát 360 độ" bằng **CloudWatch Dashboard**:

### 8.1 Bắt lỗi hệ thống (Infrastructure Alarms)
- **API Gateway & Lambda:** Cảnh báo khi API lỗi 5XX, độ trễ cao, hoặc Lambda sắp hết giờ (Duration near timeout).
- **SQS & Dead-Letter Queue (DLQ):** Theo dõi `ApproximateAgeOfOldestMessage` để bắt Job kẹt > 5 phút. Nếu Job chết sau nhiều lần retry, nó rơi vào thùng rác DLQ và báo động ngay.
- **RDS:** Báo động khi Connection DB lên quá cao, chống sập.

### 8.2 Bắt lỗi nghiệp vụ (Custom Metrics)
- Bắn trực tiếp các thông số nghiệp vụ từ Lambda (Namespace: **BudgetBot/W7**) như: `UploadJobCreated`, `UploadJobFailed`, `RowsParsed`, `RowsInserted`. Giúp ban quản trị lập tức biết ứng dụng có đang xử lý tốt file của khách hàng không.

### 8.3 Bằng chứng Giám sát (AWS Console Screenshots)

Nhóm đã ghi lại toàn bộ hệ thống cảnh báo và biểu đồ giám sát thực tế trên CloudWatch:

**1. Tổng quan CloudWatch Dashboard & Custom Metrics (Lỗi nghiệp vụ):**
![CloudWatch Dashboard](./image/CloudWatch%20Dashboard.jpg)
![Custom Metrics](./image/Custom%20metrics.jpg)

**2. Cảnh báo lỗi hệ thống (Infrastructure Alarms):**
![Báo động kẹt SQS DLQ](./image/DLQ%20has%20messages.jpg)
![Báo động quá tải Database](./image/DatabaseConnections.jpg)
![Báo động lỗi 5XX API](./image/5XX%20High%20Alarm.jpg)

---

---

## 9. Bài học rút ra (Lessons Learned)

1. **Khó khăn với Dependency:** Cài PyPDF vào Lambda gặp giới hạn 250MB. Giải quyết bằng Docker Image tốn thời gian nhưng tùy biến tuyệt đối.
2. **Lỗ hổng Connection Pool:** Scale Lambda làm bùng nổ RDS Connection. Giải quyết triệt để bằng SQS Buffer làm hàng đợi tĩnh.
3. **Tư duy Event-Driven:** Chuyển từ API đồng bộ sang luồng Bất đồng bộ (Upload S3 -> Gọi API /enqueue -> SQS -> Lambda Worker) là bước ngoặt mở ra khả năng chịu tải vô cực.

---

## 10. Danh sách kiểm tra Evidence

### Deployment Evidence
- [ ] Public URL qua HTTPS (CloudFront + Domain riêng).
- [ ] Upload sao kê -> /enqueue -> SQS -> Lambda -> Bedrock không timeout.
- [ ] Bypass xử lý AI với file >1000 dòng.

### Architecture Evidence
- [ ] 7 khả năng ánh xạ đúng dịch vụ.
- [ ] SQS và DLQ cấu hình xong.

### Cost & Security Evidence
- [ ] Cost Explorer dưới $100.
- [ ] Lambda IAM Role scope chặt.
- [ ] AWS WAF, Cognito và VPC cấu hình an toàn.

### Observability Evidence
- [ ] CloudWatch Dashboard hiển thị 5+ metrics.
- [ ] Metric `UploadJobFailed` bắn thành công.
