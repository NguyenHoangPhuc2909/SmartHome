#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <DHT.h> 

// 1. CẤU HÌNH
const char* ssid     = "XiaoHuHu";
const char* password = "urauraura";

//  DHT11 & Servo
#define DHT_PIN 4      
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

const int SERVO_PIN = 18; 

Servo myServo;
WebServer server(80);

// 2. BIẾN TRẠNG THÁI HỆ THỐNG
bool motorRunning   = false;
int  degreeInput    = 90;     // Góc quay mặc định
int  delayInput     = 500;    // Thời gian chờ (ms) mặc định

// Biến phục vụ cho hàm millis() (Non-blocking)
unsigned long previousMillis = 0;
bool isAtMaxAngle = false; 

// 3. GIAO DIỆN WEB
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset='UTF-8'>
  <title>ESP32 Servo Control</title>
  <style> body { font-family: Arial; padding: 20px; } </style>
</head>
<body>
  <h2>ESP32 - CẢM BIẾN DHT11 & SERVO</h2>
  <hr>
  <p><b>Nhiệt độ:</b> <span id='tempValue'>Đang cập nhật...</span> &deg;C</p>
  <p><b>Độ ẩm:</b> <span id='humValue'>Đang cập nhật...</span> %</p>
  <p><b>Trạng thái Servo:</b> <span id='motorState'>Đã dừng</span></p>
  <hr>
  <form action='/start' method='GET'>
    <label>Góc quay (Độ):</label><br>
    <input type='number' name='degree' min='1' max='180' value='%DEGREE%'><br><br>
    
    <label>Thời gian trễ (ms):</label><br>
    <input type='number' name='delay' min='100' max='5000' value='%DELAY%'><br><br>
    
    <input type='submit' value='BẮT ĐẦU QUÉT'>
    <button type='button' onclick="location.href='/stop'">DỪNG SERVO</button>
  </form>

  <script>
    // DHT11 phản hồi chậm, bắt buộc phải giãn thời gian cập nhật lên 2000ms
    setInterval(() => {
      fetch('/status')
        .then(res => res.json())
        .then(data => {
          document.getElementById('tempValue').innerText = data.temp;
          document.getElementById('humValue').innerText = data.hum;
          document.getElementById('motorState').innerText = data.motor;
        });
    }, 2000); 
  </script>
</body>
</html>
)rawliteral";

// 4. CÁC HÀM XỬ LÝ 

// Trả về JSON trạng thái
void handleStatus() {
  // Đọc nhiệt độ và độ ẩm từ DHT11
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  // Kiểm tra lỗi nếu cảm biến lỏng dây hoặc đọc quá nhanh
  String tempStr = isnan(t) ? "Lỗi" : String(t, 1);
  String humStr  = isnan(h) ? "Lỗi" : String(h, 1);

  String state = motorRunning ? "Đang quét liên tục (0 - " + String(degreeInput) + " độ)" : "Đã dừng (Về 0 độ)";
  
  // Gửi giá trị qua JSON
  String json = "{\"temp\":\"" + tempStr + "\", \"hum\":\"" + humStr + "\", \"motor\":\"" + state + "\"}";
  server.send(200, "application/json", json);
}

// Xử lý khi nhấn nút BẮT ĐẦU
void handleStart() {
  if (server.hasArg("degree")) degreeInput = server.arg("degree").toInt();
  if (server.hasArg("delay"))  delayInput  = server.arg("delay").toInt();

  // Giới hạn giá trị an toàn
  degreeInput = constrain(degreeInput, 1, 180);
  delayInput  = constrain(delayInput, 100, 5000);

  motorRunning = true;
  previousMillis = millis(); // Đặt lại bộ đếm thời gian
  isAtMaxAngle = false;
  myServo.write(degreeInput); // Cho Servo chạy ngay vòng đầu tiên
  isAtMaxAngle = true;

  server.sendHeader("Location", "/");
  server.send(303); 
}

// Xử lý khi nhấn nút DỪNG
void handleStop() {
  motorRunning = false;
  myServo.write(0); // Trả Servo về vị trí 0 độ khi dừng
  server.sendHeader("Location", "/");
  server.send(303);
}

// Hàm gửi trang Web giao diện
void handleRoot() {
  String html = String(index_html);
  
  html.replace("%DEGREE%", String(degreeInput));
  html.replace("%DELAY%", String(delayInput));
  
  server.send(200, "text/html", html);
}

// 5. SETUP & LOOP
void setup() {
  Serial.begin(9600);

  // Khởi tạo cảm biến DHT11
  dht.begin();

  // Cấu hình Servo
  ESP32PWM::allocateTimer(0);
  myServo.setPeriodHertz(50); 
  myServo.attach(SERVO_PIN, 500, 2400);
  myServo.write(0); // Mặc định ở 0 độ

  // Kết nối WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Dang ket noi WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nIP Web Server: " + WiFi.localIP().toString());

  // Định tuyến Web
  server.on("/", handleRoot);
  server.on("/status", handleStatus);
  server.on("/start", handleStart);
  server.on("/stop", handleStop);
  server.begin();
}

void loop() {
  server.handleClient(); 

  if (motorRunning) {
    unsigned long currentMillis = millis();
    
    // Kiểm tra xem đã trôi qua đủ thời gian delayInput chưa
    if (currentMillis - previousMillis >= delayInput) {
      previousMillis = currentMillis; // Cập nhật lại mốc thời gian
      
      if (isAtMaxAngle) {
        myServo.write(0);          
        isAtMaxAngle = false;
      } else {
        myServo.write(degreeInput); 
        isAtMaxAngle = true;
      }
    }
  }
}
