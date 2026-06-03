# Smart Home Management System

## Project Overview
Dự án là một hệ thống quản lý nhà thông minh toàn diện, được tích hợp công nghệ nhận diện khuôn mặt để tăng cường bảo mật và tự động hóa các thiết bị trong gia đình. Hệ thống cho phép người dùng giám sát các thông số môi trường, điều khiển thiết bị từ xa qua giao diện web, cũng như thiết lập các lịch trình hoạt động tự động.

## Key Features
*   **Bảo mật & Nhận diện khuôn mặt:**
    *   Xác thực người dùng thông qua nhận diện khuôn mặt ứng dụng mô hình Deep Learning (OpenCV & ONNXRuntime).
    *   Tự động mở cửa khi nhận diện thành công hoặc phát cảnh báo khi có người lạ đột nhập.
    *   Lưu trữ và quản lý tập dữ liệu khuôn mặt của từng thành viên trong gia đình.
*   **Điều khiển thiết bị thông minh:**
    *   Bật/tắt các thiết bị điện (đèn, quạt, cửa, còi báo động) trong từng khu vực (phòng khách, phòng ngủ, nhà bếp,...).
    *   Hỗ trợ 3 chế độ điều khiển: Thủ công, Tự động (AI/Cảm biến), và Theo lịch trình.
*   **Giám sát môi trường thời gian thực:**
    *   Thu thập và hiển thị các chỉ số môi trường từ cảm biến (nhiệt độ, độ ẩm, ánh sáng, nồng độ khí gas).
    *   Lưu trữ lịch sử hoạt động của thiết bị và vẽ biểu đồ trực quan (sử dụng Recharts).
*   **Quản lý lịch trình:**
    *   Hẹn giờ bật/tắt thiết bị tự động theo các ngày trong tuần và khung giờ cụ thể.

## System Architecture
Hệ thống được chia thành 3 thành phần chính:

1.  **Frontend:**
    *   Framework: ReactJS, Vite.
    *   Thiết kế giao diện: Tailwind CSS, Material UI, Emotion.
    *   Quản lý trạng thái: Zustand.
    *   Đồ thị & Biểu đồ: Recharts.
2.  **Backend:**
    *   Framework: Python (Flask).
    *   Cơ sở dữ liệu: MySQL (thông qua SQLAlchemy ORM).
    *   Xử lý ảnh & Trí tuệ nhân tạo: OpenCV, NumPy, ONNXRuntime, scikit-learn.
    *   Quản lý tác vụ ngầm định kỳ: Flask-APScheduler.
3.  **Hardware:**
    *   Vi điều khiển chính: ESP32, ESP32-CAM (phục vụ thu thập dữ liệu cảm biến và nhận diện hình ảnh tại cửa).

## Installation Guide

### Prerequisites
*   Python 3.8 trở lên.
*   Node.js 18.x trở lên.
*   Hệ quản trị cơ sở dữ liệu MySQL.

### 1. Cài đặt và cấu hình Backend
Di chuyển vào thư mục `backend` và thực hiện các lệnh sau:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
*Lưu ý: Tạo và cấu hình file `.env` để chứa thông tin kết nối cơ sở dữ liệu MySQL và các biến môi trường bắt buộc khác trước khi khởi chạy.*

### 2. Cài đặt Frontend
Di chuyển vào thư mục `frontend` và thực hiện cài đặt:
```bash
cd frontend
npm install
```

## Usage

### Chạy Backend Server
Mở terminal, đảm bảo môi trường ảo (nếu có) đã được kích hoạt, chạy lệnh:
```bash
cd backend
python app.py
```

### Chạy Frontend Development Server
Mở một terminal mới, chạy lệnh:
```bash
cd frontend
npm run dev
```
Sau khi khởi chạy thành công, truy cập vào đường dẫn được hiển thị trên terminal để sử dụng ứng dụng web.

## Demo & Documentation
