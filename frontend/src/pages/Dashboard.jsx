import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import useStore from "../store";
import SensorCard  from "../components/SensorCard";
import DeviceCard  from "../components/DeviceCard";
import AlertBanner from "../components/AlertBanner";

const roomLabel = {
  living_room: "Phòng khách",
  bedroom:     "Phòng ngủ",
  kitchen:     "Phòng bếp",
  bathroom:    "Phòng tắm",
  entrance:    "Cửa chính",
};

function Dashboard() {
  const { devices, sensors, aiMode, accessLogs, fetchDevices, fetchAccessLogs, toggleDevice, setAiMode } = useStore();
  const [chartData,      setChartData]      = useState([]);
  const [dismissedAlert, setDismissedAlert] = useState(false);

  // Poll mỗi 5 giây
  useEffect(() => {
    fetchDevices();
    fetchAccessLogs();
    const interval = setInterval(() => {
      fetchDevices();
      fetchAccessLogs();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Cập nhật chart khi sensors thay đổi
  useEffect(() => {
    if (sensors.temp === "--") return;
    const now = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setChartData((prev) => {
      const next = [...prev, { time: now, temp: sensors.temp, humi: sensors.humi, light: sensors.light }];
      return next.slice(-20); // giữ 20 điểm gần nhất
    });
  }, [sensors]);

  // Lọc alerts chưa xử lý
  const activeAlerts = accessLogs.filter((l) => l.is_alert);

  // Nhóm thiết bị theo phòng
  const devicesByRoom = devices.reduce((acc, d) => {
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

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold" style={{ fontFamily: "monospace", color: "var(--text)" }}>
              Dashboard
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
              Tổng quan hệ thống nhà thông minh
            </p>
          </div>

          {/* AI Mode toggle */}
          <div className="flex items-center gap-3">
            <span className="text-xs tracking-widest uppercase"
                  style={{ fontFamily: "monospace", color: "var(--muted)" }}>
              AI Mode
            </span>
            <button
              onClick={() => setAiMode(!aiMode)}
              className="relative w-12 h-6 rounded-full transition-all"
              style={{
                background: aiMode ? "var(--accent)" : "rgba(255,255,255,0.1)",
                border: "none", cursor: "pointer",
              }}>
              <div className="absolute top-1 w-4 h-4 rounded-full transition-all"
                   style={{
                     background: aiMode ? "#0d0f0f" : "var(--muted)",
                     left: aiMode ? "calc(100% - 20px)" : "4px",
                   }} />
            </button>
            <span className="text-xs font-bold"
                  style={{ fontFamily: "monospace", color: aiMode ? "var(--accent)" : "var(--muted)" }}>
              {aiMode ? "ON" : "OFF"}
            </span>
          </div>
        </div>

        {/* Sensor cards */}
        <div className="mb-8">
          <h2 className="text-xs tracking-widest uppercase mb-4"
              style={{ fontFamily: "monospace", color: "var(--muted)" }}>
            Cảm biến
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <SensorCard type="temp"  value={sensors.temp}  room="Phòng khách" />
            <SensorCard type="humi"  value={sensors.humi}  room="Phòng khách" />
            <SensorCard type="light" value={sensors.light} room="Phòng khách" />
            <SensorCard type="gas"   value={sensors.gas}   room="Phòng bếp" />
          </div>
        </div>

        {/* Devices by room */}
        <div className="mb-8">
          <h2 className="text-xs tracking-widest uppercase mb-4"
              style={{ fontFamily: "monospace", color: "var(--muted)" }}>
            Thiết bị
          </h2>
          {Object.entries(devicesByRoom).map(([room, devs]) => (
            <div key={room} className="mb-6">
              <div className="text-xs mb-3 px-2 py-1 rounded-sm inline-block"
                   style={{
                     fontFamily: "monospace",
                     color: "var(--accent)",
                     background: "rgba(184,245,80,0.08)",
                     border: "1px solid rgba(184,245,80,0.2)",
                   }}>
                {roomLabel[room] || room}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {devs.map((d) => (
                  <DeviceCard
                    key={d.id}
                    device={d}
                    aiMode={aiMode}
                    onToggle={(id, status) => toggleDevice(id, status, {
                      temp:  sensors.temp  !== "--" ? sensors.temp  : null,
                      humi:  sensors.humi  !== "--" ? sensors.humi  : null,
                      light: sensors.light !== "--" ? sensors.light : null,
                      gas:   sensors.gas   !== "--" ? sensors.gas   : null,
                    })}
                  />
                ))}
              </div>
            </div>
          ))}

          {devices.length === 0 && (
            <div className="text-sm text-center py-12" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
              Chưa có thiết bị nào
            </div>
          )}
        </div>

        {/* Chart */}
        <div className="rounded-sm p-6"
             style={{
               background: "rgba(255,255,255,0.02)",
               border: "1px solid rgba(255,255,255,0.07)",
             }}>
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
                    background: "var(--surface)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 2,
                    color: "var(--text)",
                    fontSize: 11,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: "var(--muted)" }} />
                <Line type="monotone" dataKey="temp"  stroke="#ff6b6b" dot={false} strokeWidth={1.5} name="Nhiệt độ (°C)" />
                <Line type="monotone" dataKey="humi"  stroke="#4ecdc4" dot={false} strokeWidth={1.5} name="Độ ẩm (%)" />
                <Line type="monotone" dataKey="light" stroke="#ffd93d" dot={false} strokeWidth={1.5} name="Ánh sáng (lux)" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-sm text-center py-12" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
              Đang chờ dữ liệu cảm biến...
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

export default  Dashboard;