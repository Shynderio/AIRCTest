# Recommendation System

## Phân tích dataset:

- **User-Item Pairwise cùng Context:**
  - Dataset chứa các cặp user-item trong các bối cảnh (context) khác nhau.
  - Không có đánh giá explicit (chỉ có đánh giá implicit là `cnt`).

## Thư viện Surprise:

### Ưu điểm:
  - Có thể xây dựng và đánh giá các mô hình collaborative filtering và content-based filtering.

### Nhược điểm:
  - Không hỗ trợ content-based filtering đầy đủ.
  - Các thuật toán chủ yếu dựa trên dữ liệu có đánh giá explicit và không xử lý đánh giá implicit.
  - Không tận dụng được context.

## Giải pháp:

### Đánh giá Implicit:
  - Công thức đặt nhãn:
    - Nếu chưa có trong 1 context cụ thể mà user chỉ gặp 1 lần, độ ưa thích của người dùng đối với item trong context đó sẽ là 50%.
    - Nếu trong 1 context cụ thể mà user đã gặp nhiều lần, độ ưa thích của người dùng đối với các item khác nhau được tính theo tỷ lệ phần trăm.

### Sử dụng Factorization Machine làm base:
  - Áp dụng mô hình interaction-aware factorization machine để học được cả quan hệ giữa các trường của 2 feature.

### Xử lý dữ liệu tương tác (interaction-aware):
  - Sử dụng mô hình Factorization Machine để học các tương tác giữa các feature và context.

## Triển khai/demo:

### Môi trường:
  - Python phiên bản 3.6.3
  - Các yêu cầu được liệt kê trong tệp `requirements.txt`

### Chạy demo:
  - Di chuyển đến thư mục `src`:
    ```bash
    cd src
    ```
  - Chạy ứng dụng Flask:
    ```bash
    flask run
    ```
