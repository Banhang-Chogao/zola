+++
title = "XGBoost hoạt động như thế nào? Từ Decision Tree đến Gradient Boosting"
slug = "xgboost-hoat-dong-nhu-the-nao"
description = "Giải thích cơ chế hoạt động của XGBoost: decision tree, ensemble learning, gradient boosting và các tham số chính như learning rate, max depth và regularization."
date = 2026-06-30T20:15:00+07:00
aliases = ["/posting/xgboost-hoat-dong-nhu-the-nao/"]
excerpt = "XGBoost hoạt động nhờ gradient boosting: nhiều cây quyết định nhỏ nối tiếp nhau, mỗi cây sửa lỗi cho cây trước. Tìm hiểu decision tree, boosting và cách tinh chỉnh tham số."

[taxonomies]
categories = ["Tất cả", "Công nghệ"]
tags = ["Machine Learning", "XGBoost", "AI WebOps", "Series"]

[extra]
series = "xgboost-model-la-gi"
series_part = 2
series_total = 5
seo_keyword = "XGBoost hoạt động như thế nào"
toc = true

[[extra.faq]]
q = "Gradient boosting là gì?"
a = "Gradient boosting là kỹ thuật xây dựng mô hình bằng cách thêm dần các cây quyết định nhỏ, mỗi cây tập trung giảm sai số của tổ hợp cây trước đó bằng cách đi theo hướng dốc nhất của hàm mất mát."

[[extra.faq]]
q = "Decision tree có liên quan gì đến XGBoost?"
a = "XGBoost dùng decision tree làm 'học viên cơ sở'. Thay vì dùng một cây lớn, nó kết hợp hàng trăm cây nhỏ (thường chỉ sâu 3–6 tầng) để tạo mô hình cuối."

[[extra.faq]]
q = "Overfitting trong XGBoost là gì?"
a = "Overfitting xảy ra khi mô hình học quá khớp với dữ liệu huấn luyện, dẫn đến dự đoán kém trên dữ liệu mới. XGBoost có regularization, max depth, subsample và early stopping để chống overfitting."

[[extra.faq]]
q = "Learning rate trong XGBoost có tác dụng gì?"
a = "Learning rate kiểm soát mức đóng góp của mỗi cây mới vào mô hình. Giá trị thấp (0.01–0.1) giúp học chậm và chính xác hơn, nhưng cần nhiều cây hơn."

[[extra.faq]]
q = "XGBoost có hỗ trợ GPU không?"
a = "Có. Phiên bản XGBoost mới hỗ trợ huấn luyện trên GPU (CUDA), giúp tăng tốc đáng kể với dữ liệu lớn."
[[extra.references_external]]
title = "XGBoost Parameters Documentation"
url = "https://xgboost.readthedocs.io/en/stable/parameter.html"

[[extra.references_external]]
title = "Gradient Boosting — scikit-learn"
url = "https://scikit-learn.org/stable/modules/ensemble.html#gradient-boosting"

[[extra.references_external]]
title = "A Gentle Introduction to Gradient Boosting (Machine Learning Mastery)"
url = "https://machinelearningmastery.com/gentle-introduction-gradient-boosting-algorithm-machine-learning/"

+++

Bài trước chúng ta đã biết XGBoost là một thuật toán machine learning mạnh mẽ, nhưng bạn có tự hỏi bên trong nó hoạt động thế nào không? Làm thế nào hàng trăm cây quyết định nhỏ có thể phối hợp với nhau để tạo ra một mô hình chính xác?

Bài này sẽ giải thích cơ chế hoạt động của XGBoost từ những khái niệm nền tảng nhất: decision tree, ensemble learning, boosting, và gradient boosting. Không có công thức toán dài dòng — chỉ có hình dung trực quan và ví dụ đời thường.

## Decision Tree là gì?

Cây quyết định (decision tree) là một trong những mô hình machine learning dễ hiểu nhất. Hãy tưởng tượng nó như một bảng câu hỏi "có/không" mà bạn đi từ gốc đến lá:

> Thu nhập > 15 triệu/tháng? → Có → Đã có thẻ tín dụng? → Có → Có nợ xấu? → Không → **Khả năng duyệt vay cao**

Mỗi câu hỏi là một **nút**, mỗi câu trả lời dẫn tới một nhánh, và lá cuối cùng là kết quả dự đoán. Decision tree rất dễ giải thích: bạn có thể nhìn vào cây và hiểu tại sao mô hình đưa ra quyết định đó.

Nhưng decision tree có một nhược điểm lớn: **dễ overfitting**. Một cây quá sâu sẽ học thuộc lòng dữ liệu huấn luyện, nhưng dự đoán kém khi gặp dữ liệu mới.

## Ensemble Learning: nhiều cây vẫn hơn một cây

Ensemble learning là ý tưởng kết hợp nhiều mô hình yếu (weak learners) để tạo thành một mô hình mạnh (strong learner). Có hai cách chính:

**Bagging (Bootstrap Aggregating):** Xây nhiều mô hình độc lập trên các mẫu dữ liệu khác nhau, rồi lấy trung bình kết quả. Random Forest là đại diện tiêu biểu.

**Boosting:** Xây các mô hình nối tiếp nhau, mỗi mô hình mới tập trung sửa lỗi của mô hình cũ. Đây là nền tảng của XGBoost.

## Boosting: sửa lỗi dần dần

Hãy tưởng tượng bạn đang chơi một trò chơi đoán số. Người thứ nhất đoán sai 30%. Người thứ hai không đoán lại từ đầu, mà tập trung vào 30% sai đó và tự điều chỉnh. Người thứ ba lại tập trung vào phần còn sai sau hai người trước. Càng nhiều người tham gia, độ chính xác càng tăng.

Đó chính là boosting: một chuỗi các mô hình yếu, mỗi mô hình mới được huấn luyện để khắc phục điểm yếu của mô hình trước đó.

## Gradient Boosting: đi theo hướng dốc

Gradient boosting là phiên bản nâng cấp của boosting. Thay vì chỉ sửa lỗi một cách đơn giản, nó dùng **gradient descent** — một kỹ thuật tối ưu trong học máy — để tìm ra hướng điều chỉnh tốt nhất cho mỗi bước.

Ý tưởng cốt lõi: thay vì dự đoán trực tiếp kết quả, mỗi cây mới sẽ dự đoán **phần dư** (residual) — phần chênh lệch giữa giá trị thực tế và dự đoán hiện tại.

Ví dụ: bạn muốn dự đoán giá căn hộ.
- Cây 1 dự đoán: 2 tỉ. Sai lệch so với giá thật (2,5 tỉ) = +500 triệu.
- Cây 2 dự đoán: phần sai lệch +500 triệu. Nếu cây 2 đoán +400 triệu, tổng dự đoán là 2,4 tỉ.
- Cây 3 lại tập trung vào phần sai lệch còn lại (+100 triệu), và cứ thế tiếp tục.

Càng nhiều cây, tổng dự đoán càng gần giá trị thực.

## XGBoost làm gì khác biệt?

XGBoost triển khai gradient boosting nhưng được tối ưu hoá mạnh mẽ:

**Regularization:** XGBoost thêm các thành phần chống overfitting ngay trong quá trình huấn luyện. Đây là điểm khác biệt lớn so với gradient boosting truyền thống.

**Xử lý dữ liệu thiếu thông minh:** XGBoost tự động học hướng đi nào tốt nhất khi gặp giá trị bị thiếu (missing value), không cần bạn phải điền giá trị thủ công.

**Tối ưu phần cứng:** Thư viện tận dụng bộ nhớ đệm, đa luồng và giảm số lần đọc/ghi để tăng tốc.

**Cắt tỉa cây theo chiều sâu (depth-first):** Khác với các thuật toán khác cắt tỉa theo mức độ, XGBoost xây cây theo chiều sâu trước, giúp kiểm soát overfitting tốt hơn.

## Các tham số quan trọng cần biết

**Learning rate (eta):** Kiểm soát mức đóng góp của mỗi cây mới. Giá trị nhỏ (0.01–0.3) giúp mô hình học chậm và chính xác hơn, nhưng cần nhiều cây hơn.

**Max depth:** Độ sâu tối đa của mỗi cây. Giá trị nhỏ (3–6) tạo cây đơn giản, giảm overfitting. Giá trị lớn có thể học quan hệ phức tạp nhưng dễ overfitting.

**Subsample:** Tỉ lệ dữ liệu được lấy mẫu ngẫu nhiên cho mỗi cây. Giá trị nhỏ hơn 1 giúp giảm overfitting.

**Colsample_bytree:** Tỉ lệ đặc trưng được lấy mẫu cho mỗi cây. Giống subsample nhưng áp dụng cho cột thay vì hàng.

**Alpha và Lambda:** Các tham số regularization L1 và L2. Giá trị cao hơn làm mô hình đơn giản hơn, giảm overfitting.

**n_estimators:** Số lượng cây. Càng nhiều cây thường càng chính xác, nhưng đến một điểm thì ngừng cải thiện và bắt đầu overfitting. Dùng early_stopping_rounds để tự động dừng.

## Khi nào model bắt đầu overfitting?

Khi bạn huấn luyện XGBoost, hãy luôn theo dõi hai đường cong: **training error** và **validation error**. Khi training error tiếp tục giảm nhưng validation error bắt đầu tăng — đó là dấu hiệu overfitting.

Cách xử lý:
- Giảm max depth hoặc learning rate
- Tăng regularization (lambda, alpha)
- Tăng subsample hoặc colsample_bytree
- Dùng early_stopping_rounds

## Điều cần nhớ

XGBoost không phải là một hộp đen kỳ diệu. Sức mạnh của nó đến từ gradient boosting + regularization + tối ưu tốc độ. Nhưng để nó hoạt động tốt, bạn cần hiểu các tham số và biết cách tinh chỉnh. Không có bộ tham số nào phù hợp cho mọi bài toán — bạn phải thử nghiệm trên dữ liệu của chính mình.

Trong bài tiếp theo, chúng ta sẽ khám phá các ứng dụng thực tế của XGBoost trong ngân hàng, y tế, thương mại điện tử và nhiều lĩnh vực khác.
