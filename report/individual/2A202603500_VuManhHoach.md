# Báo cáo cá nhân — Day 6

**Họ và tên:** Vũ Mạnh Hoạch  
**MSSV:** 2A202603500  
**Lớp:** L3A  
**Học phần:** Data Ingestion Engineering (Day 06)

---

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  - *Chủ đề:* Đề án mở chương trình đào tạo trình độ đại học ngành Trí tuệ nhân tạo (Mã ngành: 7480107) của Học viện Công nghệ Bưu chính Viễn thông (PTIT).
  - *Nguồn và quyền:* Tài liệu đề án chính thức, công khai của PTIT ban hành năm 2024, được lưu hành phục vụ học tập, nghiên cứu và quản lý giáo dục. Lưu tại [starter/data/De-an-mo-nganh-AI_Final.pdf](../../starter/data/De-an-mo-nganh-AI_Final.pdf) và mô tả chi tiết tại [starter/data/manifest.json](../../starter/data/manifest.json).
  - *Số trang:* Tổng cộng 57 trang vật lý.
  - *Quy tắc tính trang:* Loại bỏ trang 1 (bìa) và trang 2, 3 (mục lục). Tổng số trang nội dung hữu ích được đưa vào pipeline là **54 trang** (từ trang vật lý 4 đến 57, tương ứng trang in 1 đến 54), vượt xa yêu cầu tối thiểu $\ge 30$ trang. Tổng số ký tự nội dung là 131.388 ký tự.
- **Chuẩn hóa, lỗi và giới hạn:**
  - *Chuẩn hóa:* Áp dụng chuẩn Unicode NFC (`unicodedata.normalize('NFC')`), xử lý ký tự trắng đặc biệt (`\xa0`, `\u200b`), chuẩn hóa khoảng trắng thừa và ngắt dòng (`\n\n` tối đa cho phân đoạn).
  - *Lỗi phát hiện và xử lý:* Ở đầu mỗi trang PDF trích xuất bằng `pypdf`, số trang in thường đứng độc lập (ví dụ `'2'`, `'3'`), nếu chia theo paragraph thông thường sẽ tạo ra các chunk rác chỉ chứa 1-2 ký tự. Bộ chunker đã được bổ sung bộ lọc loại bỏ các header số trang đứng lẻ này.
  - *Giới hạn:* Một số bảng biểu trong PDF (như ma trận phân bổ tín chỉ, bảng khảo sát lương) khi trích xuất bằng PDF text-layer bị chuyển đổi thành dòng văn bản tuyến tính, làm suy giảm cấu trúc hai chiều của dữ liệu bảng.
- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  - *Embedding Model:* `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` chạy local trên CPU thông qua thư viện `sentence-transformers` phiên bản 6.3.0. Hỗ trợ xử lý ngữ nghĩa đa ngữ (Việt - Anh), số chiều vector: **384**.
  - *Vector Store:* PostgreSQL 16.16 (Debian) + pgvector extension 0.8.7 chạy trên Docker container local (`127.0.0.1:55433`).
  - *Metric:* Cosine distance (`<=>`), chuyển đổi sang Cosine Similarity (`1.0 - distance`).
  - *Lệnh chạy toàn bộ pipeline:* `python -m starter.src.run`
  - *Chi phí:* **0.00 USD** (mô hình hoàn toàn local, mã nguồn mở, không tốn chi phí API).
- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  - *Metadata bắt buộc:* `document_id` (`de_an_ai_ptit_2024`), `source` (`De-an-mo-nganh-AI_Final.pdf`), `page` (số trang vật lý từ 4 đến 57).
  - *Trường lọc bổ sung:* `section` (phân đoạn chính của đề án).
  - *Nguồn giá trị:* Trích xuất trực tiếp từ cấu trúc mục lục chính thức của đề án:
    - `phan_1`: Giới thiệu khái quát về Học viện (trang vật lý 4–11).
    - `phan_2`: Sự cần thiết mở ngành đào tạo Trí tuệ nhân tạo (trang vật lý 12–41).
    - `phan_3`: Chương trình đào tạo ngành Trí tuệ nhân tạo (trang vật lý 42–43).
    - `phan_4`: Năng lực của cơ sở đào tạo (trang vật lý 44–55).
    - `phan_5`: Kết luận và kiến nghị (trang vật lý 56–57).
  - *Lý do chọn:* `section` là thuộc tính phân vùng ngữ cảnh tự nhiên và đáng tin cậy nhất trong một đề án đào tạo, giúp thu hẹp phạm vi tìm kiếm theo chuyên môn mà không sinh dữ liệu giả định.

---

## Cấu hình và benchmark
- **A / B / C (tham số cụ thể, khác biệt duy nhất B–C):**
  - **Strategy A (Fixed-size Baseline):** Cửa sổ trượt cố định độ dài ký tự `size = 500`, `overlap = 50`. Không sử dụng bộ lọc metadata.
  - **Strategy B (Paragraph/Structure-aware):** Gom các đoạn văn bản liền kề theo ranh giới `\n\n`, giới hạn độ dài `max_size = 800` ký tự, loại bỏ header rời rạc. Không sử dụng bộ lọc metadata.
  - **Strategy C (Paragraph + Metadata Filter):** Cơ chế chunking hoàn toàn giống Strategy B (`max_size = 800`). Khác biệt duy nhất giữa B và C nằm ở khâu truy xuất: Strategy C áp dụng mệnh đề lọc SQL `WHERE section = %s` khi câu hỏi có yêu cầu phạm vi ngữ cảnh.
- **$\ge 20$ câu: phân chia $\ge 15$ dev / $\ge 5$ test, câu metadata filter và cách kiểm chứng evidence:**
  - *Quy mô:* Tổng cộng 20 câu hỏi (15 dev: `q01`–`q15`, 5 test: `q16`–`q20`). Lưu tại [starter/benchmark/benchmark.json](../../starter/benchmark/benchmark.json).
  - *Câu hỏi metadata filter:* Có 3 câu chứa filter `section`: `q03` (dev, `phan_1`), `q12` (dev, `phan_4`), và `q18` (test, `phan_4`).
  - *Cách kiểm chứng evidence:* Từng đoạn trích `evidence_quote` được kiểm tra đối sánh tự động 100% bằng script [starter/scripts/verify_benchmark.py](../../starter/scripts/verify_benchmark.py), đảm bảo tồn tại nguyên vẹn trong văn bản đã chuẩn hóa tại đúng trang `gold_page`.
- **Tiêu chí chọn chiến lược đã chốt trước khi xem test:**
  1. Ưu tiên hàng đầu là **Evidence Hit@3** trên tập Dev (đảm bảo bằng chứng đúng nằm trong top-3 để LLM có thể trả lời).
  2. Tiếp theo là **Tính mạch lạc của Chunk (Coherence)**: Chunk phải giữ trọn vẹn ý tứ, không bị cắt đứt giữa từ/câu.
  3. Thứ ba là **Tác động của Metadata Filter**: Đánh giá khả năng triệt tiêu kết quả nhiễu từ các chương khác.
  4. Cuối cùng là **Chi phí tài nguyên**: Số lượng chunk lưu trữ và thời gian index.

---

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| **Strategy A** (Fixed 500/50) | Dev | 6/15 (40.0%) | 12/15 (80.0%) | 317 | 8.00s | 0.00$ |
| **Strategy A** (Fixed 500/50) | Test | 3/5 (60.0%) | 3/5 (60.0%) | 317 | 8.00s | 0.00$ |
| **Strategy B** (Paragraph 800) | Dev | 6/15 (40.0%) | 9/15 (60.0%) | 209 | 5.13s | 0.00$ |
| **Strategy B** (Paragraph 800) | Test | 3/5 (60.0%) | 3/5 (60.0%) | 209 | 5.13s | 0.00$ |
| **Strategy C** (Paragraph + Filter) | Dev | 6/15 (40.0%) | **11/15 (73.33%)** | 209 | 5.06s | 0.00$ |
| **Strategy C** (Paragraph + Filter) | Test | 3/5 (60.0%) | 3/5 (60.0%) | 209 | 5.06s | 0.00$ |

| Strategy | Coherence trung bình /2 (n=10) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| **Strategy A** | 1.0 / 2.0 (10 vị trí) | 15/15 (100%) | N/A (không dùng filter) | 0: 2 câu, 1: 0 câu, 2: 3 câu $\rightarrow$ **1.2 / 2.0** |
| **Strategy B** | **2.0 / 2.0** (10 vị trí) | 15/15 (100%) | N/A (không dùng filter) | 0: 2 câu, 1: 0 câu, 2: 3 câu $\rightarrow$ **1.2 / 2.0** |
| **Strategy C** | **2.0 / 2.0** (10 vị trí) | 15/15 (100%) | **1/1 (100% tuân thủ, 3/3 top chunks)** | 0: 2 câu, 1: 0 câu, 2: 3 câu $\rightarrow$ **1.2 / 2.0** |

- **Đường dẫn trace, nhãn thủ công và cách chọn mẫu:**
  - File trace chi tiết top-3: [traces_strategy_A.json](../../starter/results/traces_strategy_A.json), [traces_strategy_B.json](../../starter/results/traces_strategy_B.json), [traces_strategy_C.json](../../starter/results/traces_strategy_C.json).
  - Tóm tắt tổng hợp: [summary_metrics.json](../../starter/results/summary_metrics.json) và [experiment_log.csv](../../artifacts/experiment_log.csv).
  - Mẫu đánh giá Coherence: 10 vị trí nguồn đầu tiên (trang vật lý 4 đến 13), chấm độc lập theo thang 0–2.
  - Mẫu đánh giá Metadata & Grounding: Toàn bộ 5 câu test $\times$ top-3 retrieved chunks (15 bản ghi/chiến lược).

---

## Phân tích và kết luận
- **So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn:**
  - *So sánh A và B:*
    - Strategy A tạo ra 317 chunks, trong khi Strategy B chỉ tạo ra 209 chunks (giảm 34% dung lượng index).
    - Về mặt Coherence, Strategy B vượt trội hoàn toàn (2.0/2 so với 1.0/2). Ở Strategy A, 100% các chunk tại vị trí kiểm tra đều bị ngắt quãng giữa từ (ví dụ: `tuỳ thuộc vào thời gian đào t...`, `an toàn thông tin và m...`).
    - Tuy nhiên, Strategy A có Hit@3 cao hơn trên Dev (80% so với 60%) do kích thước chunk nhỏ hơn (455 ký tự) giúp embedding tập trung hơn vào các từ khóa cục bộ, trong khi chunk dài 625 ký tự của Strategy B đôi khi chứa nhiều ý làm loãng vector đại diện.
  - *So sánh B và C:*
    - Khi bổ sung Metadata Filter (`section`), Evidence Hit@3 trên Dev tăng mạnh từ **60.0% (9/15) lên 73.33% (11/15)**. Bộ lọc loại bỏ hoàn toàn các đoạn văn trùng từ khóa nhưng khác chương (ví dụ câu hỏi về máy tính thư viện không bị nhầm với máy tính phòng thực hành Khoa AI).
  - *02 ví dụ sai phân tích chi tiết:*
    1. **Câu `q16` (Test set - Tên tiếng Anh chính thức của ngành AI):**
       - *Nguồn:* Trang vật lý 4 (`phan_1`): `Tên ngành (tiếng Anh): Artificial Intelligence`.
       - *Kết quả:* Cả A, B, C đều thất bại (không lọt vào top-3). Top-3 lại rơi vào trang 43 (`phan_3`) và trang 9 do chứa các cụm từ *"ngành Trí tuệ nhân tạo tại Học viện Công nghệ Bưu chính Viễn thông"* lặp lại nhiều lần với mật độ cao hơn trang bìa/tiêu đề mở đầu.
    2. **Câu `q19` (Test set - Hai trường đại học Hoa Kỳ được đối sánh):**
       - *Nguồn:* Trang vật lý 42 (`phan_3`): `Đại học Stanford (Hoa Kỳ)... Đại học Carnegie Mellon (Hoa Kỳ)`.
       - *Kết quả:* Strategy A đạt Hit@1 (điểm Cosine similarity cao vì đoạn danh sách ngắn nằm trọn trong cửa sổ 500 ký tự). Strategy B và C bị trượt khỏi top-3 do đoạn văn này bị gộp chung với phần giới thiệu dài về quá trình xây dựng chương trình đào tạo, làm suy giảm độ tương đồng vector ngữ nghĩa so với câu truy vấn.
- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:**
  - *Chiến lược chọn:* **Strategy C (Paragraph Chunking kết hợp Metadata Filter)**.
  - *Lý do:* Strategy C đạt được sự cân bằng tối ưu: giữ được trọn vẹn ngữ cảnh ngữ pháp (Coherence = 2.0/2), tiết kiệm 34% số lượng vector cần lưu trữ, và tăng độ chính xác truy xuất lên 73.33% nhờ loại bỏ nhiễu ngữ cảnh thông qua trường `section`.
  - *Đánh đổi:* Cần hệ thống tiền xử lý có khả năng phân loại hoặc gắn thẻ metadata chính xác cho tài liệu trước khi index; nếu truy vấn người dùng không có ngữ cảnh để suy diễn filter thì hệ thống sẽ hoạt động tương đương Strategy B.
  - *Điều kiện áp dụng:* Thích hợp cho các kho tri thức có cấu trúc phân mục rõ rệt (hợp đồng, quy chế đào tạo, sổ tay hướng dẫn kỹ thuật, tài liệu luật).
- **Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí:**
  - *Tập test:* Tập test gồm 5 câu là quy mô nhỏ, mang tính chất kiểm tra xác thực định tính chứ chưa đủ lớn để đưa ra kết luận thống kê p-value có ý nghĩa lớn.
  - *Độ trễ/Chi phí:* Model embedding chạy local trên CPU nên chi phí là 0 USD, tuy nhiên tốc độ nhúng phụ thuộc vào phần cứng máy tính cá nhân.
- **Nếu làm lại hoặc mở rộng, cải tiến gì?**
  1. *Hybrid Retrieval:* Bổ sung BM25 kết hợp với Dense Vector (Reciprocal Rank Fusion - RRF) để giải quyết triệt để các câu hỏi tìm kiếm theo mã ngành (`7480107`) hoặc tên viết tắt (`CDIT`, `CMU`).
  2. *Hierarchical Chunking (Parent-Child):* Lưu trữ các chunk nhỏ (200 ký tự) cho việc tìm kiếm vector chính xác, nhưng khi trả về sẽ mở rộng ngữ cảnh sang chunk cha (paragraph/section 1000 ký tự) để gửi cho LLM.

