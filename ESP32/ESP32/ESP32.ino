#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"
#include <ESP32Servo.h>
#include <LiquidCrystal_I2C.h>
#include <Wire.h>

// ===========================
// Cấu hình WiFi & MQTT
// ===========================
const char* ssid = "XiaoHuHu";
const char* password = "urauraura";

const char* mqtt_server = "broker.hivemq.com";
const int mqtt_port = 1883;

// Các Topic MQTT
const char* topic_sensors = "myiot/home/sensors";
const char* topic_trigger = "myiot/home/commands/camera_capture";
const char* topic_controls = "myiot/home/controls/#";
const char* topic_status_prefix = "myiot/home/status/";
const char* topic_servo = "myiot/home/commands/servo";

WiFiClient espClient;
PubSubClient client(espClient);

// ===========================
// Khai báo Chân (Pin Mapping mới theo dschan.md)
// ===========================
// 1. Cảm biến
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);
#define MQ2_PIN 34
#define LDR_PIN 35
#define PIR_PIN 36 // VP - Chỉ nhận tín hiệu

// 2. Thiết bị cảnh báo
#define BUZZER_PIN 16

// 3. Nút bấm Camera
#define CAM_BTN_PIN 32

// 4. Thiết bị ra (Động cơ & Servo)
#define SERVO_PIN 18

// 4 chân điều khiển L298N (2 động cơ)
// Quạt 1 (Phòng Khách) nối vào OUT3, OUT4 -> điều khiển bởi IN3, IN4
// Quạt 2 (Phòng Ngủ) nối vào OUT1, OUT2 -> điều khiển bởi IN1, IN2
#define MOTOR1_IN3 27
#define MOTOR1_IN4 13
#define MOTOR2_IN1 26
#define MOTOR2_IN2 14

// 5. Các LED (5 cái)
// LED 1: Phòng Khách, 2: Ngủ, 3: Bếp, 4: Cổng, 5: Vệ Sinh
const int ledPins[5] = {17, 19, 23, 25, 33};

// ===========================
// Màn hình LCD I2C
// ===========================
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ===========================
// Biến trạng thái
// ===========================
Servo myServo;
bool servoActive = false;
unsigned long servoStartTime = 0;

int motorStates[2] = {0, 0};
int ledStates[5] = {0, 0, 0, 0, 0};

int lastPirState = LOW;
int lastLdrState = 0;

unsigned long lastSensorMsg = 0;
unsigned long lastReconnectAttempt = 0;
bool isGasAlert = false;
bool alarmEnabled = true; // Tính năng còi báo động (mặc định bật)
bool alertActive = false;
unsigned long alertStartTime = 0;

// Ngắt nút Camera
volatile bool camTriggered = false;

void IRAM_ATTR camBtnISR() {
  camTriggered = true;
}

// ===========================
// Hàm hỗ trợ
// ===========================
void setup_wifi() {
  delay(10);
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void publishStatus(String deviceName, int state) {
  String topic = String(topic_status_prefix) + deviceName;
  client.publish(topic.c_str(), String(state).c_str());
  Serial.println("[MQTT TX] Published status: " + topic + " -> " + String(state));
}

// Điều khiển Động cơ (Hoán đổi: Motor1 -> IN3/IN4, Motor2 -> IN1/IN2)
void controlMotor(int motorIdx, int state) {
  motorStates[motorIdx] = state;
  if (motorIdx == 0) { // Quạt 1 (Phòng khách) - OUT3, OUT4
    if (state == 1) {
      digitalWrite(MOTOR1_IN3, HIGH);
      digitalWrite(MOTOR1_IN4, LOW);
    } else {
      digitalWrite(MOTOR1_IN3, LOW);
      digitalWrite(MOTOR1_IN4, LOW);
    }
  } else if (motorIdx == 1) { // Quạt 2 (Phòng ngủ) - OUT1, OUT2
    if (state == 1) {
      digitalWrite(MOTOR2_IN1, HIGH);
      digitalWrite(MOTOR2_IN2, LOW);
    } else {
      digitalWrite(MOTOR2_IN1, LOW);
      digitalWrite(MOTOR2_IN2, LOW);
    }
  }
}

// Cập nhật LED
void controlLed(int ledIdx, int state) {
  if (ledIdx >= 0 && ledIdx < 5) {
    ledStates[ledIdx] = state;
    digitalWrite(ledPins[ledIdx], state);
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }

  String t = String(topic);
  int state = msg.toInt();
  
  Serial.println("[MQTT RX] Topic: " + t + " | Msg: " + msg);

  // Xử lý các lệnh điều khiển
  if (t.startsWith("myiot/home/controls/led")) {
    int ledNum = t.substring(23).toInt(); // Lấy số 1, 2, 3, 4, 5
    if (ledNum >= 1 && ledNum <= 5) {
      controlLed(ledNum - 1, state);
      publishStatus("led" + String(ledNum), state);
    }
  }
  else if (t == "myiot/home/controls/buzzer") {
    if (isGasAlert) {
      digitalWrite(BUZZER_PIN, alarmEnabled ? HIGH : LOW);
    }
    publishStatus("buzzer", state);
  }
  else if (t == "myiot/home/commands/alert") {
    if (state == 1 && alarmEnabled) {
      digitalWrite(BUZZER_PIN, HIGH);
      alertActive = true;
      alertStartTime = millis();
    }
  }
  else if (t == "myiot/home/controls/motor1") {
    controlMotor(0, state);
    publishStatus("motor1", state);
  }
  else if (t == "myiot/home/controls/motor2") {
    controlMotor(1, state);
    publishStatus("motor2", state);
  }
  else if (t == topic_servo && state == 1) {
    Serial.println("Activating Servo to 90 degrees...");
    myServo.write(90);
    servoActive = true;
    servoStartTime = millis(); // Cập nhật mốc thời gian TẠI THỜI ĐIỂM nhận lệnh
  }
}

boolean reconnect() {
  Serial.print("Attempting MQTT connection...");
  String clientId = "ESP32Client-";
  clientId += String(random(0, 0xffff), HEX);
  if (client.connect(clientId.c_str())) {
    Serial.println("connected");
    client.subscribe(topic_controls);
    client.subscribe(topic_servo);
    return true;
  } else {
    Serial.print("failed, rc=");
    Serial.print(client.state());
    Serial.println(" try again in 5 seconds");
    return false;
  }
}

// ===========================
// SETUP
// ===========================
void setup() {
  Serial.begin(115200);
  
  // Khởi tạo I2C và LCD
  Wire.begin(21, 22); // SDA=21, SCL=22
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Khoi dong...");
  
  dht.begin();
  
  // Cài đặt các chân Sensor
  pinMode(PIR_PIN, INPUT); 
  
  // Nút bấm Camera
  pinMode(CAM_BTN_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(CAM_BTN_PIN), camBtnISR, FALLING);

  // Cảnh báo
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // Servo
  myServo.attach(SERVO_PIN);
  myServo.write(0); 

  // Motors
  pinMode(MOTOR1_IN3, OUTPUT);
  pinMode(MOTOR1_IN4, OUTPUT);
  pinMode(MOTOR2_IN1, OUTPUT);
  pinMode(MOTOR2_IN2, OUTPUT);
  controlMotor(0, 0);
  controlMotor(1, 0);

  // Leds
  for(int i=0; i<5; i++) {
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }

  // Khởi tạo kết nối
  setup_wifi();
  
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  reconnect(); // Kết nối MQTT ngay sau WiFi

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi OK!");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP().toString());
  delay(2000);
}

// ===========================
// LOOP
// ===========================
void loop() {
  unsigned long now = millis();

  // 1. Nút chụp ảnh Camera
  static unsigned long lastCamTrigger = 0;
  if (camTriggered) {
    camTriggered = false;
    if (now - lastCamTrigger > 800) {
      client.publish(topic_trigger, "1");
      Serial.printf("[%lu] Camera Button Pressed! (MQTT Trigger Sent)\n", now);
      lastCamTrigger = now;
    }
  }

  // 2. Duy trì MQTT
  if (!client.connected()) {
    if (now - lastReconnectAttempt > 5000) {
      lastReconnectAttempt = now;
      if (reconnect()) {
        lastReconnectAttempt = 0;
      }
    }
  } else {
    client.loop();
  }

  // 3. Xử lý Servo Timer (Dùng millis() trực tiếp để tránh lỗi underflow do now được tính từ trước callback)
  if (servoActive && (millis() - servoStartTime >= 10000)) {
    myServo.write(0);
    servoActive = false;
    Serial.println("Servo returned to 0.");
  }

  // 3.1. Xử lý Còi cảnh báo ngắn (Face Recognition)
  if (alertActive && (millis() - alertStartTime >= 3000)) {
    digitalWrite(BUZZER_PIN, LOW);
    alertActive = false;
  }

  // 4. Xử lý PIR Sensor (Vệ sinh - LED 5)
  int pirState = digitalRead(PIR_PIN);
  if (pirState != lastPirState) {
    lastPirState = pirState;
    int isOn = (pirState == HIGH) ? 1 : 0;
    controlLed(4, isOn); // LED thứ 5 (index 4)
    publishStatus("led5", isOn);
    Serial.printf("PIR Triggered: pirState = %d -> LED 5 is %s\n", pirState, isOn ? "ON" : "OFF");
  }

  // 5. Xử lý LDR Sensor (Cổng - LED 4), kiểm tra mỗi 2 giây
  static unsigned long lastLdrCheck = 0;
  if (now - lastLdrCheck > 2000) {
    lastLdrCheck = now;
    int ldrValue = analogRead(LDR_PIN);
    int isDark = (ldrValue < 1500) ? 1 : 0;
    if (isDark != lastLdrState) {
      controlLed(3, isDark); // LED thứ 4 (index 3)
      publishStatus("led4", isDark);
      lastLdrState = isDark;
      Serial.printf("LDR: %d -> isDark: %d\n", ldrValue, isDark);
    }
  }

  // 6. Đọc cảm biến & gửi MQTT mỗi 5s
  static float cached_t = 0, cached_h = 0;
  if (now - lastSensorMsg > 5000) {
    lastSensorMsg = now;
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    if (!isnan(h) && !isnan(t)) { cached_t = t; cached_h = h; }
    int mq2 = analogRead(MQ2_PIN);
    int light = analogRead(LDR_PIN);

    String json = "{\"temp\": " + String(cached_t) + ", \"humi\": " + String(cached_h) +
                  ", \"gas\": " + String(mq2) + ", \"light\": " + String(light) + "}";
    client.publish(topic_sensors, json.c_str());

    // Cảnh báo Gas
    if (mq2 > 3000 && !isGasAlert) {
      isGasAlert = true;
      digitalWrite(BUZZER_PIN, HIGH);
      controlLed(2, 1); // Bật nháy LED Bếp (index 2)
      publishStatus("buzzer", 1);
      publishStatus("led3", 1);
    } else if (mq2 <= 3000 && isGasAlert) {
      isGasAlert = false;
      digitalWrite(BUZZER_PIN, LOW);
      controlLed(2, 0); // Tắt LED Bếp
      publishStatus("buzzer", 0);
      publishStatus("led3", 0);
    }
  }

  // 7. Cập nhật LCD
  static unsigned long lastLcdUpdate = 0;
  if (now - lastLcdUpdate > 3000) {
    lastLcdUpdate = now;
    lcd.clear();
    if (isGasAlert) {
      lcd.setCursor(0, 0);
      lcd.print("CANH BAO GAS!");
      lcd.setCursor(0, 1);
      lcd.print("Nguy Hiem!");
    } else {
      lcd.setCursor(0, 0);
      lcd.print("T:"); lcd.print(cached_t, 1); lcd.print("C H:"); lcd.print(cached_h, 1); lcd.print("%");
      lcd.setCursor(0, 1);
      lcd.print("Gas: An toan");
    }
  }
}
