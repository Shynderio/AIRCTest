Phân tích dataset:
    u-i pair wise cùng context
    không có explicit rating(chỉ có implicit là cnt)


Thư viện surprise:
    - có thể xây dựng và đánh giá các mô hình collaborative filtering và content-based filtering
    drawback:
    - không có content based support, các thuật toán thiên hướng về dự đoán trên dữ liệu có explicit
    rating và không xử lý implicit
    - không tận dụng được context

Solution:
    - Implicit rating:
        Công thức đặt label:
            + nếu chưa có trong 1 context cụ thể mà user chỉ gặp 1 lần, thì độ ưa thích của người dùng đối với item trong context đó sẽ là 50%
            + nếu trong 1 context cụ thể mà user đã gặp nhiều lần, thì độ ưa thích của người dùng 
            đối với các item khác nhau được tính theo tỉ lệ phần trăm
    - Sử dụng factorization machine làm base

Production:
    - Xử dụng mô hình interaction-aware factorization machine để học được cả quan hệ giữa trường 
    của 2 feature

Implementation/demo:
    - môi trường: 
        Python phiên bản 3.6.3
        requirement ở requirement.txt

cd to src
    - run demo:
    
        flask run