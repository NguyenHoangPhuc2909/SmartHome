import cv2
import requests

# Đảm bảo port ở đây khớp với port Flask của bạn (thường là 5000)
# Nếu backend của bạn có prefix /api thì url sẽ là http://localhost:5000/api/access/recognize
API_URL = "http://localhost:5000/api/access/recognize"

# Mở camera laptop với cờ cv2.CAP_DSHOW để ép dùng DirectShow, tránh lỗi MSMF
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Nếu vẫn lỗi, bạn thử đổi số 0 thành 1: cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

print("=== GIẢ LẬP ESP32-CAM BẰNG LAPTOP ===")
print("Nhấn phím 'Space' (khoảng trắng) để chụp và gửi ảnh nhận diện.")
print("Nhấn phím 'q' để thoát.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("\n[LỖI] Không thể đọc từ camera laptop!")
        print("-> Vui lòng kiểm tra lại xem Backend Flask (file dataset.py) có đang chạy và chiếm dụng Camera không.")
        break

    # Hiển thị camera để bạn căn chỉnh khuôn mặt
    cv2.imshow("ESP32 Simulator (Laptop Cam)", frame)
    key = cv2.waitKey(1)

    # Nếu nhấn phím Space
    if key % 256 == 32:
        print("\n[INFO] Đang chụp ảnh và gửi lên server...")
        
        # Mã hoá frame ảnh sang định dạng JPEG
        _, buffer = cv2.imencode('.jpg', frame)

        # Tạo payload dạng multipart/form-data hệt như cách ESP32 gửi
        files = {
            'image': ('laptop_capture.jpg', buffer.tobytes(), 'image/jpeg')
        }

        try:
            # Gửi POST request lên Flask
            response = requests.post(API_URL, files=files)
            
            # Kiểm tra xem server có trả về JSON hợp lệ không
            try:
                data = response.json()
                print("=> Kết quả từ server:")
                if "error" in data:
                    print("   Lỗi:", data["error"])
                else:
                    print(f"   - Kết quả: {data.get('result', 'Không có dữ liệu')}")
                    print(f"   - Độ tự tin: {data.get('confidence', 'Không có dữ liệu')}")
                    print(f"   - Tên nhận diện: {data.get('matched_name', 'Không có dữ liệu')}")
            except Exception as json_err:
                print(f"[LỖI] Server không trả về JSON hợp lệ. Status code: {response.status_code}")
                print(f"Chi tiết: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("[LỖI] Không thể kết nối đến server. Hãy chắc chắn server Flask đang chạy ở cổng 5000.")
        except Exception as e:
            print("[LỖI] Đã xảy ra lỗi:", e)

    # Nhấn 'q' để thoát
    elif key % 256 == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()