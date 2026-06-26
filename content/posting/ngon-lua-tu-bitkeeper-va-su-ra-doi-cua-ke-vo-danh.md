---
title: "Ngọn lửa từ BitKeeper và sự ra đời của 'kẻ vô danh'"
slug: "ngon-lua-tu-bitkeeper-va-su-ra-doi-cua-ke-vo-danh"
date: 2026-06-26
description: "Khám phá câu chuyện đầy kịch tính về sự ra đời của Git từ cuộc khủng hoảng năm 2005, khi dự án Linux kernel mất quyền truy cập BitKeeper. Tìm hiểu ai là người sáng lập Git và tại sao nó lại thay đổi cách cả thế giới quản lý mã nguồn."
category: "Công nghệ"
tags: ["git", "version-control", "lịch-sử", "bitkeeper", "linux-kernel"]
series: "git-ke-vo-danh-thanh-nguoi-thong-tri"
series_part: 1
extra:
  series: "git-ke-vo-danh-thanh-nguoi-thong-tri"
  series_part: 1
toc: true
---

## Mở đầu: Một câu hỏi ngôn ngữ

Bạn có bao giờ tự hỏi, thế giới lập trình sẽ ra sao nếu không có Git? Chắc hẳn bạn đã từng nghe qua cái tên này, thậm chí dùng nó mỗi ngày. Nhưng ít ai biết rằng, Git ra đời từ một cuộc khủng hoảng có thật, và người tạo ra nó cũng chẳng hề có ý định làm một "ông vua" quản lý mã nguồn.

Chào mừng bạn đến với series **"Git - Kẻ vô danh thành người thống trị"**. Trong 10 bài viết, chúng ta sẽ cùng nhau khám phá hành trình từ con số 0 đến những khái niệm cao cấp nhất của Git, giúp bạn hiểu tường tận và phổ cập kiến thức này đến mọi người.

Bài viết hôm nay sẽ trả lời hai câu hỏi cơ bản nhưng không hề đơn giản:

1. **Ai là người sáng lập Git?**
2. **Trước Git, người ta quản lý mã nguồn như thế nào?**

---

## Ai là người sáng lập ra Git?

Trước khi bàn về Git, bạn cần biết ai là "tác giả" của nó.

**Linus Torvalds** — cái tên không xa lạ với bất kỳ lập trình viên nào — là người tạo ra Git. Ông là **cha đẻ của hệ điều hành Linux**, người mà vào năm 1991 đã viết những dòng code đầu tiên của kernel, biến nó thành một trong những công nghệ quan trọng nhất trên hành tinh.

Nhưng điều thú vị là, Linus không phải là fan của các công cụ quản lý phiên bản (Source Control Management - SCM). Thực tế, anh ta thừa nhận mình **"căm ghét tất cả các SCM"** và xem đây là thứ nhàm chán nhất. Chính từ sự "ghét" này, lại nảy sinh ra một trong những công cụ vĩ đại nhất của thế giới lập trình.

Tại sao lại như vậy? Câu trả lời nằm ở một công cụ khác: **BitKeeper**.

---

## Trước Git, người ta quản lý source như thế nào?

### Chuyện của BitKeeper: Ánh sáng giữa bóng tối

Năm 2002, dự án Linux kernel đang phát triển với tốc độ chóng mặt. Hàng trăm nhà phát triển từ khắp nơi trên thế giới đóng góp code, mỗi người đều có những thay đổi, những patch, những ý tưởng mới. Vấn đề là: **làm sao để quản lý tất cả những thay đổi đó một cách hiệu quả?**

Những công cụ quản lý phiên bản lúc bấy giờ (mà chúng ta sẽ nhắc đến sau) đều có chung một khuyết điểm: chúng hoạt động theo mô hình **tập trung (centralized)**. Nói cách khác, có một máy chủ trung tâm, và tất cả mọi người đều phải kết nối tới máy chủ đó để lấy code, lưu trữ code, và xem lịch sử thay đổi.

Đột nhiên, xuất hiện **BitKeeper** — một công cụ do công ty BitMover phát triển. BitKeeper là một hệ thống quản lý phiên bản **phân tán (distributed version control)**. Khác với các công cụ truyền thống, BitKeeper cho phép mỗi nhà phát triển có một bản sao **đầy đủ** của toàn bộ lịch sử repository, thay vì phải phụ thuộc vào một máy chủ trung tâm.

Đây là một bước nhảy vọt về mặt khái niệm. Nó giải phóng vấn đề nghẽn cổ chai ở máy chủ trung tâm, cho phép làm việc offline, và quan trọng hơn, nó cho phép các tính năng quản lý branching và merging mạnh mẽ hơn.

Linus Torvalds bị thu hút. Anh ta quyết định sử dụng BitKeeper cho dự án Linux kernel.

Nhưng — như mọi câu chuyện hay đều có một "nhưng" — không phải ai cũng vui vẻ.

### Cuộc tranh cãi BitKeeper

Việc sử dụng một công cụ mã nguồn **đóng (proprietary)** cho một dự án mã nguồn **mở (open source)** đã gây ra nhiều tranh cãi. **Richard Stallman** — người sáng lập GNU, một người có tầm nhìn sâu sắc về tự do phần mềm — đã lên tiếng lo ngại về quyết định này.

Những lo lắc của ông là có cơ sở: nếu Linux phụ thuộc vào một công cụ mã nguồn đóng, thì ai cũng có thể bị lock-in (bị khóa lại). Điều gì xảy ra nếu BitMover thay đổi chính sách, tăng giá, hay đơn giản là đóng cửa?

Mối lo đó không phải bốc đồng. **Vào tháng 4 năm 2005**, BitMover tuyên bố ngừng cung cấp phiên bản miễn phí cho dự án Linux kernel. Nguyên nhân? Do **Andrew Tridgell** — một nhà phát triển từ cộng đồng Linux — đã cố gắng **reverse-engineer** giao thức của BitKeeper, chuẩn bị viết một công cụ mã nguồn mở thay thế.

BitMover xem đây là một hành vi vi phạm giấy phép. Họ quyết định rút lại quyền truy cập miễn phí.

Ngay lập tức, nhóm Linux kernel rơi vào thế khó khăn: **không thể dùng BitKeeper nữa**. Nhưng họ cũng **không muốn quay lại các công cụ cũ** như CVS hay SVN — những công cụ mà họ đã từng xem là lạc hậu.

### Bảng tóm tắt: Các công cụ SCM trước Git

Để hiểu rõ hơn tại sao nhóm Linux lại chọn tạo một công cụ hoàn toàn mới, hãy nhìn vào những công cụ mà họ có sẵn:

| Công cụ | Năm ra đời | Mô hình | Ưu điểm | Nhược điểm |
|---------|-----------|--------|--------|-----------|
| **RCS** | 1982 | Tập trung | Quản lý phiên bản cơ bản cho file đơn lẻ | Quá tấu, không phù hợp cho dự án lớn |
| **CVS** | 1986 | Tập trung | Hỗ trợ nhiều người dùng, branching cơ bản | Quản lý lịch sử kém, merge phức tạp, không atomic |
| **SVN** | 2000 | Tập trung | Cải tiến CVS, atomic commits, xóa file tốt hơn | Vẫn dựa trên mô hình tập trung, phụ thuộc máy chủ |
| **BitKeeper** | 1999 | Phân tán | Phân tán, mạnh mẽ, branching tuyệt vời | Proprietary, không mã nguồn mở |

Nhìn vào bảng, bạn sẽ thấy một xu hướng tiến hóa: từ những công cụ quản lý từng file (RCS), sang những công cụ tập trung (CVS, SVN), cho tới những công cụ phân tán (BitKeeper). Mỗi bước là một cải tiến, một giải pháp cho những vấn đề của thế hệ trước.

### Tập trung vs Phân tán: Sự khác biệt cơ bản

Để hiểu tại sao mô hình phân tán lại quan trọng đến vậy, hãy dùng một phép ẩn dụ:

**Mô hình tập trung (CVS, SVN)** giống như một **thư viện trung tâm**. Khi bạn muốn mượn sách, bạn đi tới thư viện, mượn sách, đọc tại nhà, rồi trả lại. Nếu thư viện đóng cửa, bạn không thể mượn hay kiểm tra lịch sử. Nếu máy chủ thư viện "chết", cả hệ thống ngừng hoạt động.

**Mô hình phân tán (BitKeeper, sau này Git)** giống như **mỗi người có một bản sao của thư viện** ở nhà. Bạn có thể đọc sách, kiểm tra lịch sử, thậm chí tạo ra "sách mới" mà không cần tới thư viện trung tâm. Khi bạn muốn chia sẻ, bạn gửi những sách đó đi, hoặc mượn từ bạn bè.

Đây là sự khác biệt căn bản. Mô hình phân tán mang lại **tự do, tốc độ, và khả năng chịu lỗi** — những thứ mà một dự án như Linux kernel cần.

---

## Một cuối tuần thay đổi lịch sử

Tình thế bế tắc này là **chất xúc tác hoàn hảo** cho một sự thay đổi lớn.

Vào cuối tháng 4 năm 2005, sau khi mất quyền truy cập BitKeeper, Linus Torvalds quyết định **tự viết một công cụ quản lý phiên bản mới**. Anh ta không mất thời gian lấy ý kiến từ các chương trình quản lý dự án hay lên kế hoạch chi tiết. Thay vào đó, anh ta vừa tư duy vừa code.

Linus **"biến mất" trong một ngày cuối tuần** (khoảng 4-5 ngày giữa tháng 4 năm 2005) và quay trở lại với phiên bản đầu tiên của Git.

Những con số dưới đây sẽ cho bạn thấy tốc độ phi thường:

- **Mất khoảng 1 ngày** để Git có thể **"self-hosting"** — tức là có thể quản lý chính mã nguồn của nó.
- **Chỉ khoảng 10 ngày sau**, anh thực hiện **commit đầu tiên cho nhân Linux** bằng chính công cụ mới của mình.

Điều này nghe có vẻ như phép màu. Làm sao một người có thể viết được một công cụ phức tạp như vậy chỉ trong vài ngày?

Bí mật không nằm ở tốc độ viết code (tuy Linus coding khá nhanh). Bí mật nằm ở **thiết kế căn bản**. Linus không phải bắt đầu từ con số 0. Anh ta đã dành nhiều thời gian để suy ngẫm, đọc về BitKeeper, và suy nghĩ **làm sao để tổ chức dữ liệu một cách thông minh nhất?**

Như anh ta từng nói: **"Số lượng code thực tế trong những ngày đầu là rất nhỏ. Bí quyết nằm ở việc thiết kế cách tổ chức dữ liệu."**

Git được xây dựng dựa trên một nền tảng toán học vững chắc: **object model** và **hash-based storage**. Thay vì lưu trữ "delta" (những sự thay đổi), Git lưu trữ **snapshots** (ảnh chụp) toàn bộ của repository tại từng thời điểm. Mỗi commit được định danh bằng một **hash SHA-1**, tạo nên một chuỗi (chain) bất khả xâm phạm của lịch sử.

Đây không phải một ý tưởng hoàn toàn mới — Linus đã học từ BitKeeper. Nhưng cách anh ta **đơn giản hóa** và **thực thi** nó lại rất khác.

---

## Kết thúc: Lịch sử thay đổi trong một ngày cuối tuần

Câu chuyện của Git bắt đầu không phải từ một "dự án lớn" hay một "kế hoạch tham vọng". Nó bắt đầu từ **sự khủng hoảng, sự bất mãn, và sự tư duy sâu sắc**.

Linus Torvalds — một người từng "căm ghét tất cả các SCM" — đã tạo ra một công cụ không chỉ giải quyết vấn đề của Linux kernel, mà sau này trở thành **công cụ quản lý phiên bản phổ cập nhất thế giới**.

Trong bài viết này, chúng ta đã khám phá:

1. **Ai tạo ra Git:** Linus Torvalds, cha đẻ của Linux
2. **Tại sao nó được tạo ra:** Vì Linux kernel mất quyền truy cập BitKeeper
3. **Bối cảnh lịch sử:** Từ RCS, CVS, SVN đến BitKeeper — một hành trình tiến hóa từ tập trung sang phân tán
4. **Bí quyết của Git:** Thiết kế dữ liệu thông minh, không phải lượng code khổng lồ

Nhưng đây chỉ là **chương mở đầu** của câu chuyện. Git không chỉ là một công cụ được tạo ra trong ngày cuối tuần — nó là một **triết lý**, một **cách suy nghĩ** về quản lý phiên bản.

---

## Bài tiếp theo: Cài đặt và cấu hình Git — Bước chân đầu tiên

Giờ đây, khi bạn đã biết **từ đâu Git mà có**, trong bài viết tiếp theo, chúng ta sẽ bước vào **lãnh địa thực hành**. Bạn sẽ học cách:

- Cài đặt Git trên máy tính của bạn
- Cấu hình tên và email
- Khởi tạo repository đầu tiên
- Tạo commit đầu tiên của riêng bạn

Vì khi bạn đã hiểu **tại sao** Git lại được tạo ra, việc học **cách dùng** nó sẽ trở nên dễ dàng và ý nghĩa hơn rất nhiều.

Hẹn gặp bạn ở bài tiếp theo! 

---

**Series "Git - Kẻ vô danh thành người thống trị":**
- **Bài 1 (hiện tại):** Ngọn lửa từ BitKeeper và sự ra đời của 'kẻ vô danh'
- **Bài 2:** Cài đặt và cấu hình Git — Bước chân đầu tiên
- ... (các bài tiếp theo)
