import { create } from "zustand";
import api from "../services/api";

const useStore = create((set, get) => ({

  // ── User ─────────────────────────────────────────────────────────────────
  user: null,
  fetchUser: async () => {
    try {
      const res = await api.get("/auth/me");
      set({ user: res.data });
    } catch {
      set({ user: null });
    }
  },

  // ── Devices ───────────────────────────────────────────────────────────────
  devices: [],
  fetchDevices: async () => {
    try {
      const res = await api.get("/api/devices/status");
      set({ devices: res.data });

      // Lấy các chỉ số cảm biến mới nhất từ tất cả device (kể cả light/fan khi Postman/ESP32 gửi)
      let latestSensors = { temp: null, humi: null, light: null, gas: null };
      res.data.forEach((d) => {
        // Ưu tiên đọc từ sensor device trước
        if (d.type === "sensor") {
          if (d.sensor_type === "temp"  && d.temp  != null) latestSensors.temp  = d.temp;
          if (d.sensor_type === "humi"  && d.humi  != null) latestSensors.humi  = d.humi;
          if (d.sensor_type === "light" && d.light != null) latestSensors.light = d.light;
          if (d.sensor_type === "gas"   && d.gas   != null) latestSensors.gas   = d.gas;
        }
        // Fallback: nếu sensor device chưa có, lấy từ log của light/fan (khi test Postman)
        else if (d.type === "light" || d.type === "fan") {
          if (latestSensors.temp  == null && d.temp  != null) latestSensors.temp  = d.temp;
          if (latestSensors.humi  == null && d.humi  != null) latestSensors.humi  = d.humi;
          if (latestSensors.light == null && d.light != null) latestSensors.light = d.light;
          if (latestSensors.gas   == null && d.gas   != null) latestSensors.gas   = d.gas;
        }
      });
      // Chỉ cập nhật những giá trị thực sự có (null → giữ nguyên "--")
      const prev = get().sensors;
      set({ sensors: {
        temp:  latestSensors.temp  ?? prev.temp,
        humi:  latestSensors.humi  ?? prev.humi,
        light: latestSensors.light ?? prev.light,
        gas:   latestSensors.gas   ?? prev.gas,
      }});
    } catch (err) {
      console.error("fetchDevices:", err);
    }
  },
  toggleDevice: async (deviceId, currentStatus, sensorData = {}) => {
    const newStatus = currentStatus === 1 ? 0 : 1;
    try {
      await api.post(`/api/devices/${deviceId}/control`, {
        status: newStatus,
        ...sensorData,
      });
      // Cập nhật local state ngay, không cần chờ poll
      set((state) => ({
        devices: state.devices.map((d) =>
          d.id === deviceId ? { ...d, status: newStatus, mode: "Manual" } : d
        ),
      }));
    } catch (err) {
      console.error("toggleDevice:", err);
    }
  },

  // ── AI Mode ───────────────────────────────────────────────────────────────
  aiMode: false,
  setAiMode: (val) => set({ aiMode: val }),

  // ── Sensors (dữ liệu realtime từ ESP32) ──────────────────────────────────
  sensors: { temp: "--", humi: "--", light: "--", gas: "--" },
  setSensors: (data) => set({ sensors: data }),

  // ── Access Logs ───────────────────────────────────────────────────────────
  accessLogs: [],
  fetchAccessLogs: async () => {
    try {
      const res = await api.get("/api/access/logs?limit=20");
      set({ accessLogs: res.data });
    } catch (err) {
      console.error("fetchAccessLogs:", err);
    }
  },

  // ── Schedules ─────────────────────────────────────────────────────────────
  schedules: [],
  fetchSchedules: async () => {
    try {
      const res = await api.get("/api/schedules/");
      set({ schedules: res.data });
    } catch (err) {
      console.error("fetchSchedules:", err);
    }
  },

  // ── Datasets ──────────────────────────────────────────────────────────────
  datasets: [],
  fetchDatasets: async () => {
    try {
      const res = await api.get("/api/datasets/");
      set({ datasets: res.data });
    } catch (err) {
      console.error("fetchDatasets:", err);
    }
  },

}));

export default useStore;