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