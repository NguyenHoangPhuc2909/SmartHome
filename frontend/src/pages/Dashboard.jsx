import { useEffect, useState, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import axios from "axios";
import useStore from "../store";
import SensorCard from "../components/SensorCard";
import DeviceCard from "../components/DeviceCard";
import AlertBanner from "../components/AlertBanner";

const roomLabel = {
  living_room: "Phòng khách",
  bedroom: "Phòng ngủ",
  kitchen: "Phòng bếp",
  bathroom: "Phòng tắm",
  entrance: "Cửa chính",
};

// ── Trạng thái của modal train ────────────────────────────────────────────────
// idle | loading | success | error
const TRAIN_STATUS = { IDLE: "idle", LOADING: "loading", SUCCESS: "success", ERROR: "error" };

function Dashboard() {
  const { devices, sensors, aiMode, accessLogs, fetchDevices, fetchAccessLogs, toggleDevice, setAiMode } = useStore();
  const [chartData, setChartData] = useState([]);
  const [dismissedAlert, setDismissedAlert] = useState(false);

  // Modal train AI
  const [showTrainModal, setShowTrainModal] = useState(false);
  const [trainStatus, setTrainStatus] = useState(TRAIN_STATUS.IDLE);
  const [trainLines, setTrainLines] = useState([]);  // mảng từng dòng kết quả
  const [trainError, setTrainError] = useState("");
  const fileInputRef = useRef(null);

  // ── Poll mỗi 5 giây ─────────────────────────────────────────────────────────
  useEffect(() => {
    fetchDevices();
    fetchAccessLogs();
    const interval = setInterval(() => {
      fetchDevices();
      fetchAccessLogs();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // ── Cập nhật chart khi sensors thay đổi ──────────────────────────────────────
  useEffect(() => {
    if (sensors.temp === "--") return;
    const now = new Date().toLocaleTimeString("vi-VN", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
    setChartData((prev) => {
      const next = [...prev, { time: now, temp: sensors.temp, humi: sensors.humi, light: sensors.light, gas: sensors.gas }];
      return next.slice(-20);
    });
  }, [sensors]);

  // ── Reset trạng thái khi đóng modal ─────────────────────────────────────────
  const closeModal = () => {
    setShowTrainModal(false);
    // Delay nhỏ để animation đóng modal xong mới reset state
    setTimeout(() => {
      setTrainStatus(TRAIN_STATUS.IDLE);
      setTrainLines([]);
      setTrainError("");
    }, 300);
  };

  // ── Xử lý kết quả từ backend ─────────────────────────────────────────────────
  const handleTrainSuccess = (message) => {
    // message từ backend là chuỗi nhiều dòng, tách ra thành mảng
    const lines = message.split("\n").filter(Boolean);
    setTrainLines(lines);
    setTrainStatus(TRAIN_STATUS.SUCCESS);
  };

  const handleTrainError = (error) => {
    const msg = error.response?.data?.error || error.message || "Lỗi không xác định";
    setTrainError(msg);
    setTrainStatus(TRAIN_STATUS.ERROR);
  };

  // ── Upload file để train ──────────────────────────────────────────────────────
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    event.target.value = null; // reset để có thể chọn lại file cùng tên

    setTrainStatus(TRAIN_STATUS.LOADING);
    setTrainLines([]);
    setTrainError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("/api/devices/train", formData);
      handleTrainSuccess(response.data.message);
    } catch (error) {
      handleTrainError(error);
    }
  };

  // ── Train từ database ─────────────────────────────────────────────────────────
  const handleTrainFromDB = async () => {
    setTrainStatus(TRAIN_STATUS.LOADING);
    setTrainLines([]);
    setTrainError("");

    try {
      const response = await axios.post("/api/devices/train-from-db");
      handleTrainSuccess(response.data.message);
    } catch (error) {
      handleTrainError(error);
    }
  };

  // ── Nhóm thiết bị theo phòng ──────────────────────────────────────────────────
  const activeAlerts = accessLogs.filter((l) => l.is_alert);
  const devicesByRoom = devices.reduce((acc, d) => {
    // Ẩn các cảm biến (sensor) khỏi danh sách thiết bị điều khiển ON/OFF
    if (d.type === "sensor") return acc;
    
    if (!acc[d.room]) acc[d.room] = [];
    acc[d.room].push(d);
    return acc;
  }, {});

  return (
    <div className="pt-14 min-h-screen" style={{ background: "var(--bg)" }}>
      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Alert banner */}
        {!dismissedAlert && activeAlerts.length > 0 && (
          <AlertBanner alerts={activeAlerts} onDismiss={() => setDismissedAlert(true)} />
        )}

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold" style={{ fontFamily: "monospace", color: "var(--text)" }}>
              Dashboard
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
              Tổng quan hệ thống nhà thông minh
            </p>
          </div>

          <div className="flex items-center gap-6">
            {/* Nút mở modal train */}
            <button
              onClick={() => setShowTrainModal(true)}
              className="btn-secondary flex items-center gap-2"
              style={{ fontSize: "12px" }}
            >
              <span className="text-xs tracking-widest uppercase font-bold">⚙️ Train AI</span>
            </button>

            <div style={{ width: "1px", height: "24px", background: "var(--border)" }} />

            {/* AI Mode toggle */}
            <div className="flex items-center gap-3">
              <span className="text-xs tracking-widest uppercase"
                style={{ fontFamily: "monospace", color: "var(--muted)" }}>
                AI Mode
              </span>
              <button
                onClick={async () => {
                  const newMode = !aiMode;
                  setAiMode(newMode);
                  // Khi BẬT AI mode → gọi API reset tất cả thiết bị Manual về AI
                  if (newMode) {
                    try {
                      await axios.post("/api/devices/reset-to-ai");
                      fetchDevices(); // Refresh lại UI
                    } catch (err) {
                      console.error("Không thể reset về AI mode:", err);
                    }
                  }
                }}
                className="relative w-12 h-6 rounded-full transition-all"
                style={{
                  background: aiMode ? "var(--accent)" : "#CBD5E1",
                  border: "none", cursor: "pointer",
                }}
              >
                <div className="absolute top-1 w-4 h-4 rounded-full transition-all"
                  style={{
                    background: aiMode ? "#ffffff" : "#9ca3af",
                    left: aiMode ? "calc(100% - 20px)" : "4px",
                  }}
                />
              </button>
              <span className="text-xs font-bold"
                style={{ fontFamily: "monospace", color: aiMode ? "var(--accent)" : "var(--muted)" }}>
                {aiMode ? "ON" : "OFF"}
              </span>
            </div>
          </div>
        </div>

        {/* ── Cảm biến ────────────────────────────────────────────────────── */}
        <div className="mb-8">
          <h2 className="text-xs tracking-widest uppercase mb-4"
            style={{ fontFamily: "monospace", color: "var(--muted)" }}>
            Cảm biến
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <SensorCard type="temp" value={sensors.temp} room="Phòng khách" />
            <SensorCard type="humi" value={sensors.humi} room="Phòng khách" />
            <SensorCard type="light" value={sensors.light} room="Phòng khách" />
            <SensorCard type="gas" value={sensors.gas} room="Phòng bếp" />
          </div>
        </div>

        {/* ── Thiết bị theo phòng ─────────────────────────────────────────── */}
        <div className="mb-8">
          <h2 className="text-xs tracking-widest uppercase mb-4"
            style={{ fontFamily: "monospace", color: "var(--muted)" }}>
            Thiết bị
          </h2>
          {Object.entries(devicesByRoom).map(([room, devs]) => (
            <div key={room} className="mb-6">
              <div className="badge badge-accent text-xs mb-3" style={{ fontSize: "11px" }}>
                {roomLabel[room] || room}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {devs.map((d) => (
                  <DeviceCard
                    key={d.id}
                    device={d}
                    aiMode={aiMode}
                    onToggle={(id, status) => toggleDevice(id, status, {
                      temp: sensors.temp !== "--" ? sensors.temp : null,
                      humi: sensors.humi !== "--" ? sensors.humi : null,
                      light: sensors.light !== "--" ? sensors.light : null,
                      gas: sensors.gas !== "--" ? sensors.gas : null,
                    })}
                  />
                ))}
              </div>
            </div>
          ))}
          {devices.length === 0 && (
            <div className="text-sm text-center py-12"
              style={{ color: "var(--muted)", fontFamily: "monospace" }}>
              Chưa có thiết bị nào
            </div>
          )}
        </div>

        {/* ── Chart realtime ───────────────────────────────────────────────── */}
        <div className="card p-6">
          <h2 className="text-xs tracking-widest uppercase mb-6"
            style={{ fontFamily: "monospace", color: "var(--muted)" }}>
            Biểu đồ cảm biến realtime
          </h2>
          {chartData.length > 1 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <XAxis dataKey="time" tick={{ fill: "var(--muted)", fontSize: 10 }} />
                <YAxis tick={{ fill: "var(--muted)", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    background: "#FFFFFF",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    color: "var(--text)",
                    fontSize: 12,
                    boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: "var(--muted)" }} />
                <Line type="monotone" dataKey="temp"  stroke="#DC2626" dot={false} strokeWidth={2} name="Nhiệt độ (°C)" />
                <Line type="monotone" dataKey="humi"  stroke="#0284C7" dot={false} strokeWidth={2} name="Độ ẩm (%)" />
                <Line type="monotone" dataKey="light" stroke="#D97706" dot={false} strokeWidth={2} name="Ánh sáng (lux)" />
                <Line type="monotone" dataKey="gas"   stroke="#7C3AED" dot={false} strokeWidth={2} name="Khí gas (ppm)" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-sm text-center py-12"
              style={{ color: "var(--muted)", fontFamily: "monospace" }}>
              Đang chờ dữ liệu cảm biến...
            </div>
          )}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════════
          MODAL TRAIN AI
      ══════════════════════════════════════════════════════════════════════ */}
      {showTrainModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-70 backdrop-blur-sm"
          onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }}
        >
          <div
            className="card p-6 w-full max-w-md"
          >
            {/* Header modal */}
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-bold uppercase tracking-wide"
                style={{ color: "var(--accent)", fontFamily: "monospace" }}>
                ⚙️ Huấn luyện lại AI
              </h3>
              <button
                onClick={closeModal}
                style={{ color: "var(--muted)", background: "transparent", border: "none", cursor: "pointer", fontSize: 18 }}
              >
                ✕
              </button>
            </div>

            <p className="text-sm mb-5" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
              Cập nhật thói quen bật/tắt thiết bị dựa trên bộ dữ liệu mới.
            </p>

            {/* ── TRẠNG THÁI: ĐANG LOADING ── */}
            {trainStatus === TRAIN_STATUS.LOADING && (
              <div className="flex flex-col items-center gap-3 py-8">
                <div
                  className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
                  style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
                />
                <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                  Đang huấn luyện model...
                </span>
              </div>
            )}

            {/* ── TRẠNG THÁI: THÀNH CÔNG ── */}
            {trainStatus === TRAIN_STATUS.SUCCESS && (
              <div className="mb-5">
                {/* Tiêu đề thành công */}
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-base">🎉</span>
                  <span className="text-sm font-bold" style={{ color: "var(--accent)", fontFamily: "monospace" }}>
                    {trainLines[0]}
                  </span>
                </div>

                {/* Bảng kết quả accuracy */}
                <div
                  className="rounded-sm overflow-hidden"
                  style={{ border: "1px solid rgba(45,158,107,0.25)" }}
                >
                  {trainLines.slice(1).map((line, idx) => {
                    // Mỗi dòng có dạng "Tên thiết bị (ID x): 92.5%"
                    const colonIdx = line.lastIndexOf(":");
                    const label = colonIdx !== -1 ? line.slice(0, colonIdx).trim() : line;
                    const value = colonIdx !== -1 ? line.slice(colonIdx + 1).trim() : "";
                    const accNum = parseFloat(value);

                    // Màu thanh progress theo accuracy
                    const barColor =
                      accNum >= 85 ? "#b8f550" :
                        accNum >= 70 ? "#ffd93d" : "#ff6b6b";

                    return (
                      <div
                        key={idx}
                        className="px-4 py-3"
                        style={{
                          background: idx % 2 === 0 ? "#f9fafb" : "#ffffff",
                          borderBottom: idx < trainLines.length - 2 ? "1px solid var(--border)" : "none",
                        }}
                      >
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                            {label}
                          </span>
                          <span className="text-xs font-bold" style={{ color: barColor, fontFamily: "monospace" }}>
                            {value}
                          </span>
                        </div>
                        {/* Thanh progress */}
                        {!isNaN(accNum) && (
                          <div className="w-full rounded-full h-1" style={{ background: "#e5e7eb" }}>
                            <div
                              className="h-1 rounded-full transition-all"
                              style={{ width: `${accNum}%`, background: barColor }}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                <button
                  onClick={closeModal}
                  className="mt-4 w-full py-2 text-xs uppercase tracking-widest font-bold rounded-sm transition-all hover:opacity-90"
                  style={{ background: "var(--accent)", color: "#ffffff", border: "none", cursor: "pointer" }}
                >
                  Xong
                </button>
              </div>
            )}

            {/* ── TRẠNG THÁI: LỖI ── */}
            {trainStatus === TRAIN_STATUS.ERROR && (
              <div className="mb-5">
                <div
                  className="p-3 rounded-sm mb-4 text-xs"
                  style={{
                    background: "rgba(255,107,107,0.1)",
                    border: "1px solid rgba(255,107,107,0.3)",
                    color: "#ff6b6b",
                    fontFamily: "monospace",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  ❌ {trainError}
                </div>
                <button
                  onClick={() => setTrainStatus(TRAIN_STATUS.IDLE)}
                  className="w-full py-2 text-xs uppercase tracking-widest font-bold rounded-sm"
                  style={{
                    color: "var(--muted)",
                    background: "transparent",
                    border: "1px solid var(--border)",
                    cursor: "pointer",
                  }}
                >
                  ← Thử lại
                </button>
              </div>
            )}

            {/* ── TRẠNG THÁI: IDLE — chọn nguồn train ── */}
            {trainStatus === TRAIN_STATUS.IDLE && (
              <>
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  accept=".csv,.xlsx"
                  onChange={handleFileUpload}
                />

                <div className="flex flex-col gap-3 mb-5">
                  {/* Option 1: Upload file */}
                  <button
                    onClick={() => fileInputRef.current.click()}
                    className="w-full py-3 px-4 flex flex-col items-start gap-1 rounded-sm transition-all text-left hover:opacity-90"
                    style={{ background: "#f3f4f6", border: "1px solid var(--border)" }}
                  >
                    <span className="font-bold text-sm" style={{ color: "var(--text)" }}>
                      📁 Tải lên Dataset
                    </span>
                    <span className="text-xs" style={{ color: "var(--muted)" }}>
                      Hỗ trợ .csv hoặc .xlsx (sheet: "Dữ liệu thô")
                    </span>
                  </button>

                  {/* Option 2: Train từ DB */}
                  <button
                    onClick={handleTrainFromDB}
                    className="w-full py-3 px-4 flex flex-col items-start gap-1 rounded-sm transition-all text-left hover:opacity-90"
                    style={{ background: "var(--accent-light)", border: "1px solid rgba(45,158,107,0.3)" }}
                  >
                    <span className="font-bold text-sm" style={{ color: "var(--accent)" }}>
                      🗄️ Trích xuất từ Database
                    </span>
                    <span className="text-xs" style={{ color: "var(--muted)", opacity: 0.8 }}>
                      Tự động lọc lịch sử hệ thống (DeviceLog)
                    </span>
                  </button>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={closeModal}
                    className="px-4 py-2 text-xs uppercase tracking-wider font-bold rounded-sm"
                    style={{
                      color: "var(--muted)",
                      background: "transparent",
                      border: "1px solid var(--border)",
                      cursor: "pointer",
                    }}
                  >
                    Hủy bỏ
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;