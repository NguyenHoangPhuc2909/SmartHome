import { useEffect, useState, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from "recharts";
import axios from "axios";
import {
  Box,
  Typography,
  Button,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  CircularProgress,
  Paper,
  Card,
  LinearProgress,
  useTheme,
  Alert
} from "@mui/material";
import {
  Settings as SettingsIcon,
  Close as CloseIcon,
  CloudUpload as UploadIcon,
  Storage as StorageIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon
} from "@mui/icons-material";
import useStore from "../store";
import SensorCard from "../components/SensorCard";
import DeviceCard from "../components/DeviceCard";

const roomLabel = {
  living_room: "Phòng khách",
  bedroom: "Phòng ngủ",
  kitchen: "Phòng bếp",
  bathroom: "Phòng tắm",
  entrance: "Cửa chính",
};

// ── Trạng thái của modal train ────────────────────────────────────────────────
const TRAIN_STATUS = { IDLE: "idle", LOADING: "loading", SUCCESS: "success", ERROR: "error" };

function Dashboard() {
  const theme = useTheme();
  const { devices, sensors, aiMode, accessLogs, sensorHistory, fetchDevices, fetchAccessLogs, fetchSensorHistory, toggleDevice } = useStore();
  const [chartData, setChartData] = useState([]);

  // Modal train AI
  const [showTrainModal, setShowTrainModal] = useState(false);
  const [trainStatus, setTrainStatus] = useState(TRAIN_STATUS.IDLE);
  const [trainLines, setTrainLines] = useState([]);
  const [trainError, setTrainError] = useState("");
  const fileInputRef = useRef(null);

  // ── Fetch dữ liệu ban đầu ──────────────────────────────────────────────────
  useEffect(() => {
    fetchDevices();
    fetchAccessLogs();
    fetchSensorHistory();
  }, []);

  // ── Cập nhật chart khi sensors thay đổi ──────────────────────────────────────
  useEffect(() => {
    if (sensors.temp === "--") return;
    const now = new Date().toLocaleTimeString("vi-VN", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
    setChartData((prev) => {
      const next = [...prev, { time: now, temp: sensors.temp, humi: sensors.humi, light: sensors.light, gas: sensors.gas }];
      return next.slice(-5);
    });
  }, [sensors]);

  const closeModal = () => {
    setShowTrainModal(false);
    setTimeout(() => {
      setTrainStatus(TRAIN_STATUS.IDLE);
      setTrainLines([]);
      setTrainError("");
    }, 300);
  };

  const handleTrainSuccess = (message) => {
    const lines = message.split("\n").filter(Boolean);
    setTrainLines(lines);
    setTrainStatus(TRAIN_STATUS.SUCCESS);
  };

  const handleTrainError = (error) => {
    const msg = error.response?.data?.error || error.message || "Lỗi không xác định";
    setTrainError(msg);
    setTrainStatus(TRAIN_STATUS.ERROR);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    event.target.value = null;

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

  const handleAutoControl = async () => {
    try {
      const sensorData = {
        temp: sensors.temp !== "--" ? parseFloat(sensors.temp) : 25.0,
        humi: sensors.humi !== "--" ? parseFloat(sensors.humi) : 60.0,
        light: sensors.light !== "--" ? parseFloat(sensors.light) : 150.0,
        gas: sensors.gas !== "--" ? parseFloat(sensors.gas) : 0.0,
      };
      
      const response = await axios.post("/api/devices/auto-control", sensorData);
      
      if (response.data.status === "ok") {
        const actions = response.data.actions || [];
        const onDevices = actions.filter(a => a.status === 1).map(a => `${a.name} (${roomLabel[a.room] || a.room})`);
        const offDevices = actions.filter(a => a.status === 0).map(a => `${a.name} (${roomLabel[a.room] || a.room})`);
        
        let alertMsg = "🤖 [AI Auto Control] Kết quả xác định trạng thái thiết bị:\n\n";
        alertMsg += `🟢 Thiết bị BẬT:\n${onDevices.length > 0 ? onDevices.map(d => ` - ${d}`).join("\n") : " - Không có"}\n\n`;
        alertMsg += `🔴 Thiết bị TẮT:\n${offDevices.length > 0 ? offDevices.map(d => ` - ${d}`).join("\n") : " - Không có"}`;
        
        alert(alertMsg);
        fetchDevices();
      }
    } catch (error) {
      console.error("Auto control failed:", error);
      alert("❌ Lỗi khi tự động kích hoạt thiết bị!");
    }
  };

  const activeAlerts = accessLogs.filter((l) => l.is_alert);
  const devicesByRoom = devices.reduce((acc, d) => {
    if (d.type === "sensor") return acc;
    if (!acc[d.room]) acc[d.room] = [];
    acc[d.room].push(d);
    return acc;
  }, {});

  return (
    <Box sx={{ width: '100%' }}>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">
            Tổng quan
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Tổng quan hệ thống nhà thông minh
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleAutoControl}
            sx={{ fontWeight: 'bold' }}
          >
            Tự động kích hoạt (AI)
          </Button>

          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => setShowTrainModal(true)}
            sx={{ fontWeight: 'bold' }}
          >
            Huấn luyện AI
          </Button>

        </Box>
      </Box>

      {/* ── Cảm biến ────────────────────────────────────────────────────── */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="overline" color="textSecondary" sx={{ mb: 2, display: 'block', fontWeight: 'bold' }}>
          Cảm biến
        </Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 2 }}>
          <Box>
            <SensorCard type="temp" value={sensors.temp} room="Phòng khách" history={sensorHistory} />
          </Box>
          <Box>
            <SensorCard type="humi" value={sensors.humi} room="Phòng khách" history={sensorHistory} />
          </Box>
          <Box>
            <SensorCard type="light" value={sensors.light} room="Phòng khách" history={sensorHistory} />
          </Box>
          <Box>
            <SensorCard type="gas" value={sensors.gas} room="Phòng bếp" history={sensorHistory} />
          </Box>
        </Box>
      </Box>

      {/* ── Thiết bị theo phòng ─────────────────────────────────────────── */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="overline" color="textSecondary" sx={{ mb: 2, display: 'block', fontWeight: 'bold' }}>
          Thiết bị
        </Typography>
        {Object.entries(devicesByRoom).map(([room, devs]) => (
          <Box key={room} sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 'bold', color: 'primary.main', bgcolor: 'primary.light', display: 'inline-block', px: 1.5, py: 0.5, borderRadius: 1 }}>
              {roomLabel[room] || room}
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 2 }}>
              {devs.map((d) => (
                <Box key={d.id}>
                  <DeviceCard
                    device={d}
                    aiMode={aiMode}
                    onToggle={(id, status) => toggleDevice(id, status, {
                      temp: sensors.temp !== "--" ? sensors.temp : null,
                      humi: sensors.humi !== "--" ? sensors.humi : null,
                      light: sensors.light !== "--" ? sensors.light : null,
                      gas: sensors.gas !== "--" ? sensors.gas : null,
                    })}
                  />
                </Box>
              ))}
            </Box>
          </Box>
        ))}
        {devices.length === 0 && (
          <Typography variant="body2" color="textSecondary" align="center" sx={{ py: 6 }}>
            Chưa có thiết bị nào
          </Typography>
        )}
      </Box>

      {/* ── Chart realtime ───────────────────────────────────────────────── */}
      <Card sx={{ p: { xs: 2, sm: 3 } }}>
        <Typography variant="overline" color="textSecondary" sx={{ mb: 3, display: 'block', fontWeight: 'bold' }}>
          Biểu đồ cảm biến realtime
        </Typography>
        {chartData.length > 1 ? (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={theme.palette.divider} />
              <XAxis dataKey="time" tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 8,
                  boxShadow: theme.shadows[3] }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: theme.palette.text.secondary, paddingTop: 10 }} />
              <Line type="monotone" dataKey="temp" stroke="#ef4444" dot={false} strokeWidth={3} name="Nhiệt độ (°C)" />
              <Line type="monotone" dataKey="humi" stroke="#3b82f6" dot={false} strokeWidth={3} name="Độ ẩm (%)" />
              <Line type="monotone" dataKey="light" stroke="#f59e0b" dot={false} strokeWidth={3} name="Ánh sáng (lux)" />
              <Line type="monotone" dataKey="gas" stroke="#8b5cf6" dot={false} strokeWidth={3} name="Khí gas (ppm)" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <Typography variant="body2" color="textSecondary" align="center" sx={{ py: 8 }}>
            Đang chờ dữ liệu cảm biến...
          </Typography>
        )}
      </Card>

      {/* ══════════════════════════════════════════════════════════════════════
          MODAL TRAIN AI
      ══════════════════════════════════════════════════════════════════════ */}
      <Dialog
        open={showTrainModal}
        onClose={(e, reason) => { if (reason !== 'backdropClick') closeModal(); }}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: {  } }}
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold" color="primary">
            Huấn luyện lại AI
          </Typography>
          <IconButton onClick={closeModal} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
            Cập nhật thói quen bật/tắt thiết bị dựa trên bộ dữ liệu mới.
          </Typography>

          {/* ── TRẠNG THÁI: ĐANG LOADING ── */}
          {trainStatus === TRAIN_STATUS.LOADING && (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 6, gap: 2 }}>
              <CircularProgress size={40} />
              <Typography variant="body2" color="textSecondary">
                Đang huấn luyện model...
              </Typography>
            </Box>
          )}

          {/* ── TRẠNG THÁI: THÀNH CÔNG ── */}
          {trainStatus === TRAIN_STATUS.SUCCESS && (
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                <SuccessIcon color="success" />
                <Typography variant="subtitle1" fontWeight="bold" color="success.main">
                  {trainLines[0]}
                </Typography>
              </Box>

              <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
                {trainLines.slice(1).map((line, idx) => {
                  const colonIdx = line.lastIndexOf(":");
                  const label = colonIdx !== -1 ? line.slice(0, colonIdx).trim() : line;
                  const value = colonIdx !== -1 ? line.slice(colonIdx + 1).trim() : "";
                  const accNum = parseFloat(value);
                  const barColor = accNum >= 85 ? "success" : accNum >= 70 ? "warning" : "error";

                  return (
                    <Box
                      key={idx}
                      sx={{
                        px: 2,
                        py: 1.5,
                        bgcolor: idx % 2 === 0 ? 'background.default' : 'background.paper',
                        borderBottom: idx < trainLines.length - 2 ? `1px solid ${theme.palette.divider}` : 'none'
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2">{label}</Typography>
                        <Typography variant="body2" fontWeight="bold" color={`${barColor}.main`}>{value}</Typography>
                      </Box>
                      {!isNaN(accNum) && (
                        <LinearProgress variant="determinate" value={accNum} color={barColor} sx={{ height: 6 }} />
                      )}
                    </Box>
                  );
                })}
              </Paper>
            </Box>
          )}

          {/* ── TRẠNG THÁI: LỖI ── */}
          {trainStatus === TRAIN_STATUS.ERROR && (
            <Box sx={{ py: 2 }}>
              <Alert severity="error" sx={{ mb: 3 }}>
                {trainError}
              </Alert>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => setTrainStatus(TRAIN_STATUS.IDLE)}
              >
                Thử lại
              </Button>
            </Box>
          )}

          {/* ── TRẠNG THÁI: IDLE ── */}
          {trainStatus === TRAIN_STATUS.IDLE && (
            <Box>
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                accept=".csv,.xlsx"
                onChange={handleFileUpload}
              />
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2
                  }}
                  onClick={() => fileInputRef.current.click()}
                >
                  <UploadIcon color="primary" fontSize="large" />
                  <Box>
                    <Typography variant="subtitle2" fontWeight="bold">Tải lên Dataset</Typography>
                    <Typography variant="caption" color="textSecondary">Hỗ trợ .csv hoặc .xlsx</Typography>
                  </Box>
                </Paper>

                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2
                  }}
                  onClick={handleTrainFromDB}
                >
                  <StorageIcon color="secondary" fontSize="large" />
                  <Box>
                    <Typography variant="subtitle2" fontWeight="bold">Trích xuất từ Database</Typography>
                    <Typography variant="caption" color="textSecondary">Tự động lọc lịch sử hệ thống</Typography>
                  </Box>
                </Paper>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          {trainStatus === TRAIN_STATUS.SUCCESS ? (
            <Button onClick={closeModal} variant="contained" fullWidth>Xong</Button>
          ) : trainStatus === TRAIN_STATUS.IDLE ? (
            <Button onClick={closeModal} color="inherit">Hủy bỏ</Button>
          ) : null}
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Dashboard;