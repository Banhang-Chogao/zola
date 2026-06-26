+++
title = "Git ra đời từ BitKeeper: ngọn lửa sinh ra 'kẻ vô danh'"
description = "Git ra đời thế nào? Câu chuyện Linus Torvalds, cuộc khủng hoảng BitKeeper tháng 4/2005 và một cuối tuần thay đổi lịch sử quản lý mã nguồn."
date = 2026-06-26
aliases = ["/git-ra-doi-tu-bitkeeper/"]
[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["bitkeeper", "git", "linus torvalds", "lịch sử git", "version control"]
[extra]
thumbnail = "https://seomoney.org/img/placeholder/placeholder.svg"
seo_keyword = "git ra đời"
featured = false

[[extra.faq]]
q = "Ai là người sáng lập ra Git?"
a = "Git được tạo ra bởi Linus Torvalds — cha đẻ của hệ điều hành Linux — vào tháng 4 năm 2005. Ông viết phiên bản đầu tiên chỉ trong một cuối tuần để thay thế BitKeeper sau khi công cụ này ngừng cấp phép miễn phí cho dự án nhân Linux."
[[extra.faq]]
q = "Trước Git, người ta quản lý mã nguồn bằng gì?"
a = "Trước Git, phổ biến nhất là các hệ thống tập trung như RCS (quản lý từng file), CVS và SVN (quản lý cả dự án qua một server trung tâm). Dự án Linux kernel thì dùng BitKeeper — một công cụ phân tán mã nguồn đóng — từ năm 2002."
[[extra.faq]]
q = "Vì sao Linux kernel phải bỏ BitKeeper?"
a = "Tháng 4/2005, công ty BitMover tuyên bố ngừng cung cấp phiên bản BitKeeper miễn phí, sau khi Andrew Tridgell cố gắng reverse-engineer giao thức của BitKeeper. Nhóm Linux mất công cụ đang dùng nhưng cũng không muốn quay lại CVS/SVN — đó chính là động lực sinh ra Git."
[[extra.faq]]
q = "Hệ thống tập trung và phân tán khác nhau thế nào?"
a = "Hệ thống tập trung (CVS, SVN) có một kho duy nhất trên server; ai cũng phải kết nối tới đó để làm việc. Hệ thống phân tán (BitKeeper, Git) cho mỗi người một bản sao đầy đủ của toàn bộ lịch sử trên máy mình, làm việc offline thoải mái và không sợ mất dữ liệu khi server hỏng."
+++

> 📚 **Series "Git — Kẻ vô danh thành người thống trị" (Bài 1/10).** Đây là bài mở màn cho hành trình từ con số 0 đến những khái niệm cao cấp nhất của [Git](https://git-scm.com), giúp bạn hiểu tường tận và phổ cập kiến thức này đến mọi người.

Bạn có bao giờ tự hỏi, thế giới lập trình sẽ ra sao nếu không có Git? Chắc hẳn bạn đã từng nghe qua cái tên này, thậm chí dùng nó mỗi ngày. Nhưng ít ai biết rằng, **Git ra đời** từ một cuộc khủng hoảng có thật, và người tạo ra nó cũng chẳng hề có ý định làm một "ông vua" quản lý mã nguồn.

<!-- more -->

> **Lời mở đầu.** Chào mừng bạn đến với series **"Git — Kẻ vô danh thành người thống trị"**. Trong 10 bài viết, chúng ta sẽ cùng nhau khám phá hành trình từ con số 0 đến những khái niệm cao cấp nhất của Git, giúp bạn hiểu tường tận và phổ cập kiến thức này đến mọi người.

Trong bài đầu tiên này, mình muốn trả lời thật rõ hai câu hỏi mà rất nhiều người dùng Git mỗi ngày nhưng chưa bao giờ thật sự để tâm: **"Ai là người sáng lập ra Git?"** và **"Trước khi có Git, người ta quản lý source code như thế nào?"**. Hiểu được gốc rễ này, bạn sẽ thấy mọi lệnh `git` về sau đều có lý do tồn tại của nó, chứ không phải mớ cú pháp khó nhớ.

## Ai là người sáng lập ra Git?

Câu trả lời ngắn gọn: **Linus Torvalds — cha đẻ của hệ điều hành Linux**. Cũng chính là người đứng sau dự án mã nguồn mở lớn và quan trọng bậc nhất hành tinh.

Điều thú vị là Linus không phải fan của các công cụ quản lý phiên bản. Trong nhiều lần chia sẻ công khai, ông thẳng thắn thừa nhận mình **"căm ghét tất cả các SCM"** (Source Code Management) và xem đây là thứ nhàm chán nhất. Với một người dành phần lớn thời gian để viết kernel, việc quản lý phiên bản giống như công việc giấy tờ: cần thiết, nhưng phiền phức.

Vậy điều gì khiến một người "ghét tất cả SCM" lại đổi ý? Đó là **BitKeeper** — một công cụ quản lý phiên bản phân tán (distributed version control) do công ty BitMover phát triển. Lần đầu tiên, Linus tìm thấy một công cụ làm việc theo cách ông thấy hợp lý: mỗi lập trình viên giữ một bản sao đầy đủ của kho mã, làm việc độc lập rồi mới đồng bộ. Chính ý tưởng **phân tán** này, chứ không phải bản thân BitKeeper, mới là thứ đã thay đổi cách nhìn của ông — và sau này trở thành DNA của Git.

## Trước Git, người ta quản lý source như thế nào?

Để hiểu vì sao Git lại quan trọng, ta phải quay về bối cảnh trước nó. Và câu chuyện hay nhất chính là câu chuyện BitKeeper.

### Câu chuyện BitKeeper: từ giải pháp đến khủng hoảng

Vào **năm 2002, dự án Linux kernel bắt đầu sử dụng BitKeeper**. Đây là một quyết định không hề dễ dàng. BitKeeper là phần mềm **mã nguồn đóng (proprietary)**, trong khi Linux là biểu tượng của mã nguồn mở. Việc dùng một công cụ đóng cho một dự án mở đã gây ra nhiều tranh cãi trong cộng đồng. **Richard Stallman — người sáng lập GNU — thậm chí đã lên tiếng lo ngại** rằng các nhà phát triển đang bị phụ thuộc vào một công cụ mà họ không kiểm soát được.

Dù vậy, BitMover cho phép cộng đồng kernel dùng BitKeeper miễn phí (với một số điều kiện ràng buộc), và trên thực tế nó hoạt động rất tốt trong vài năm. Linus và nhiều maintainer thực sự thích trải nghiệm phân tán mà nó mang lại.

Điểm nổ xảy ra vào **tháng 4 năm 2005, khi BitMover tuyên bố ngừng cung cấp phiên bản miễn phí**. Nguyên nhân là do **Andrew Tridgell** — lập trình viên nổi tiếng với Samba và rsync — **đã cố gắng reverse-engineer giao thức của BitKeeper** để tạo ra một client mở. BitMover xem đây là vi phạm điều khoản và rút lại giấy phép miễn phí.

Hậu quả: nhóm phát triển Linux rơi vào thế khó. Họ **không còn được dùng BitKeeper**, nhưng cũng **chẳng ai muốn quay lại CVS hay SVN** — những công cụ tập trung chậm chạp mà họ đã thoát ra được. Đây chính là khoảng trống đã buộc Git phải ra đời.

### Sơ lược lịch sử các SCM trước Git

Trước BitKeeper, thế giới đã có một loạt công cụ quản lý phiên bản. Hiểu nhanh chúng giúp bạn thấy Git kế thừa và vượt qua điều gì:

| Công cụ | Năm | Mô hình | Đặc điểm nổi bật | Hạn chế lớn nhất |
|---|---|---|---|---|
| **RCS** | 1982 | Local (từng file) | Đơn giản, quản lý lịch sử từng file riêng lẻ | Không hiểu khái niệm "cả dự án", không làm việc nhóm thật sự |
| **CVS** | 1990 | Tập trung | Quản lý cả cây thư mục, nhiều người cùng làm | Server là điểm chết duy nhất, branch/merge yếu, không atomic commit |
| **SVN** | 2000 | Tập trung | "CVS làm đúng" — atomic commit, đổi tên file tốt hơn | Vẫn cần server trung tâm, commit phải online, merge vẫn đau |
| **BitKeeper** | 2000 | **Phân tán** | Mỗi người một bản sao đầy đủ, làm việc offline | Mã nguồn đóng → khủng hoảng 2005 |

### Tập trung (Centralized) vs Phân tán (Distributed)

Đây là khái niệm nền tảng quan trọng nhất của cả bài, hãy hình dung bằng một phép so sánh đơn giản.

**Hệ thống tập trung (CVS, SVN)** giống như một **thư viện trung tâm** duy nhất trong thành phố. Mọi cuốn sách (lịch sử mã nguồn) chỉ nằm ở đó. Muốn mượn hay trả sách, bạn phải đi tới thư viện và kết nối với nó. Nếu thư viện đóng cửa (server hỏng, mất mạng), cả thành phố ngừng làm việc. Tệ hơn, nếu thư viện cháy mà không có bản sao lưu, toàn bộ lịch sử có thể mất sạch.

**Hệ thống phân tán (BitKeeper, Git)** thì ngược lại: **mỗi người có nguyên một thư viện riêng tại nhà**. Khi bạn "clone" một dự án, bạn nhận về **toàn bộ lịch sử** chứ không chỉ phiên bản mới nhất. Bạn đọc, ghi, tạo nhánh, xem lại lịch sử — tất cả ngay tại máy mình, không cần mạng. Khi nào sẵn sàng, bạn mới đồng bộ phần thay đổi với người khác. Nếu một máy chủ trung tâm cháy rụi, bất kỳ bản sao nào của cộng tác viên cũng đủ để dựng lại tất cả.

Chính sự khác biệt này giải thích vì sao Linus mê mô hình phân tán đến vậy — và vì sao việc mất BitKeeper lại là một mất mát lớn đến mức ông quyết định tự viết công cụ thay thế. Nếu bạn muốn đào sâu hơn về định nghĩa version control, mình đã viết riêng một bài [Git là gì — version control cho người mới bắt đầu](/zola/posting/git-la-gi-version-control-cho-nguoi-moi/).

## Một cuối tuần thay đổi lịch sử

Đây là phần mình thích nhất trong toàn bộ câu chuyện.

Sau khủng hoảng tháng 4/2005, thay vì chờ đợi hay tranh cãi, **Linus Torvalds đã "biến mất" trong một ngày cuối tuần và quay trở lại với phiên bản đầu tiên của Git**. Không họp hành, không bản kế hoạch dài dằng dặc — chỉ một người, một mục tiêu rõ ràng, và một mô hình dữ liệu trong đầu.

Tốc độ thì gần như khó tin. Anh **mất khoảng một ngày để Git có thể "self-hosting"** — tức là Git đã đủ chức năng để tự quản lý chính mã nguồn của nó. Và **chỉ khoảng 10 ngày sau, anh thực hiện commit đầu tiên cho nhân Linux** bằng chính công cụ mới của mình. Một công cụ vừa mới sinh ra đã lập tức gánh dự án phần mềm phức tạp bậc nhất thế giới.

Nhưng đừng nhầm đây là phép màu. **Số lượng code thực tế trong những ngày đầu là rất nhỏ.** Bí quyết không nằm ở việc gõ thật nhanh, mà nằm ở việc **thiết kế cách tổ chức dữ liệu**. Linus không cố viết một công cụ "đẹp"; ông tập trung vào một câu hỏi gốc: *làm sao lưu trữ và đối chiếu nội dung một cách an toàn, nhanh và không thể bị âm thầm sửa đổi?* Câu trả lời — lưu mọi thứ thành các đối tượng được định danh bằng mã băm SHA — chính là nền tảng khiến Git nhanh và đáng tin đến tận hôm nay. Phần lớn thời gian "biến mất" cuối tuần đó là thời gian **suy ngẫm về mô hình dữ liệu**, không phải gõ phím.

Nói cách khác: Git nhanh được tạo ra vì nó được *nghĩ* kỹ trước khi *viết*. Đó là bài học thiết kế mà bất kỳ lập trình viên nào cũng nên ghi nhớ. Chúng ta sẽ mổ xẻ chính mô hình dữ liệu này — object, commit, tree — ở các bài sau, và bắt đầu thực hành với [các lệnh Git cơ bản: init, add, commit](/zola/posting/lenh-git-co-ban-init-add-commit-status/) cũng như [làm việc với nhánh](/zola/posting/git-branch-lam-viec-voi-nhanh/).

## Kết: Git ra đời và hành trình của "kẻ vô danh"

Sự ra đời của Git là một **bước ngoặt** thật sự của ngành phần mềm. Một công cụ được viết trong một cuối tuần, từ sự bực bội và một cuộc khủng hoảng cấp phép, đã dần trở thành tiêu chuẩn quản lý mã nguồn của gần như toàn bộ thế giới lập trình — từ dự án cá nhân nhỏ xíu đến những hệ thống khổng lồ.

Điều đáng nói là Linus chưa bao giờ có ý định tạo ra một "ông vua". Ông chỉ cần một công cụ đủ tốt để tiếp tục công việc viết kernel. Vậy mà "kẻ vô danh" ấy đã lớn lên thành kẻ thống trị. Bạn có thể đọc thêm các bài cùng chủ đề tại chuyên mục [Công nghệ](/zola/categories/cong-nghe/), và xem cách Git được dùng trong quy trình thực tế ở bài [Git workflow chuyên nghiệp: Git Flow và GitHub Flow](/zola/posting/git-workflow-chuyen-nghiep-gitflow-github-flow/).

Hành trình mới chỉ bắt đầu. Ở **Bài 2: "Cài đặt và cấu hình Git — Bước chân đầu tiên"**, chúng ta sẽ rời khỏi lịch sử để chính tay cài đặt Git trên máy, thiết lập tên và email, và chuẩn bị cho commit đầu tiên của riêng bạn. Hẹn gặp lại bạn ở bài tiếp theo — và đừng quên, mọi chuyên gia Git đều từng bắt đầu từ con số 0 giống như chúng ta bây giờ.
