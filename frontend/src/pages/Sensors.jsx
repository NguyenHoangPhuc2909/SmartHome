import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Box, Typography, Card, useTheme, Alert } from "@mui/material";
import axios from "axios";
import useStore from "../store";
import SensorCard from "../components/SensorCard";

const chartConfig = {
  temp:  { name: "Nhiệt độ",  color: "#ef4444", unit: "°C" },
  humi:  { name: "Độ ẩm",     color: "#3b82f6", unit: "%" },
  light: { name: "Ánh sáng",  color: "#f59e0b", unit: "lux" },
  gas:   { name: "Khí gas",   color: "#8b5cf6", unit: "ppm" },
};

function Sensors() {
  const theme = useTheme();
  const { sensors, devices, fetchDevices, sensorHistory, fetchSensorHistory } = useStore();
  const [selectedSensor, setSelectedSensor] = useState("temp");
  const [history, setHistory] = useState([]);
  
  const masterSensor = devices.find(d => d.type === "sensor");

  // Fetch devices để lấy masterSensor nếu chưa có
  useEffect(() => {
    fetchDevices();
    fetchSensorHistory();
  }, []);

  // Lấy lịch sử cảm biến khi có masterSensor hoặc khi có data realtime mới
  useEffect(() => {
    if (masterSensor) {
      axios.get(`/api/devices/${masterSensor.id}/logs?limit=50`)
        .then(res => {
          const data = res.data.map(log => ({
            time: new Date(log.timestamp).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
            temp: log.temp,
            humi: log.humi,
            light: log.light,
            gas: log.gas
          })).reverse();
          setHistory(data);
        })
        .catch(console.error);
    }
  }, [masterSensor, sensors]); // Re-fetch khi realtime sensors thay đổi (mỗi 5s)

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="bold">
          Cảm biến
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Nhấn vào từng thẻ để xem biểu đồ chi tiết bên dưới
        </Typography>
      </Box>

      {/* ── Thẻ Cảm biến ────────────────────────────────────────────────── */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'repeat(2, 1fr)', md: 'repeat(4, 1fr)' }, gap: 2 }}>
          <Box>
            <SensorCard 
              type="temp" 
              value={sensors.temp} 
              room="Phòng khách" 
              selected={selectedSensor === "temp"}
              onClick={() => setSelectedSensor("temp")}
              history={sensorHistory}
            />
          </Box>
          <Box>
            <SensorCard 
              type="humi" 
              value={sensors.humi} 
              room="Phòng khách" 
              selected={selectedSensor === "humi"}
              onClick={() => setSelectedSensor("humi")}
              history={sensorHistory}
            />
          </Box>
          <Box>
            <SensorCard 
              type="light" 
              value={sensors.light} 
              room="Phòng khách" 
              selected={selectedSensor === "light"}
              onClick={() => setSelectedSensor("light")}
              history={sensorHistory}
            />
          </Box>
          <Box>
            <SensorCard 
              type="gas" 
              value={sensors.gas} 
              room="Phòng bếp" 
              selected={selectedSensor === "gas"}
              onClick={() => setSelectedSensor("gas")}
              history={sensorHistory}
            />
          </Box>
        </Box>
      </Box>

      {/* ── Biểu đồ lịch sử chi tiết ────────────────────────────────────── */}
      <Card sx={{ p: { xs: 2, sm: 3 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="overline" color="textSecondary" sx={{ display: 'block', fontWeight: 'bold' }}>
            Biểu đồ lịch sử: {chartConfig[selectedSensor].name}
          </Typography>
          <Typography variant="caption" sx={{ color: chartConfig[selectedSensor].color, fontWeight: 'bold', bgcolor: `${chartConfig[selectedSensor].color}15`, px: 1.5, py: 0.5, borderRadius: 1 }}>
            {history.length} mốc dữ liệu
          </Typography>
        </Box>
        
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={history} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={theme.palette.divider} />
              <XAxis 
                dataKey="time" 
                tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} 
                axisLine={false} 
                tickLine={false} 
              />
              <YAxis 
                tick={{ fill: theme.palette.text.secondary, fontSize: 11 }} 
                axisLine={false} 
                tickLine={false} 
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 8,
                  boxShadow: theme.shadows[3] }}
                formatter={(value) => [`${value} ${chartConfig[selectedSensor].unit}`, chartConfig[selectedSensor].name]}
                labelStyle={{ color: theme.palette.text.primary, fontWeight: 'bold', marginBottom: 4 }}
              />
              <Line 
                type="monotone" 
                dataKey={selectedSensor}  
                stroke={chartConfig[selectedSensor].color} 
                dot={false}
                activeDot={{ r: 6, fill: chartConfig[selectedSensor].color, stroke: '#fff', strokeWidth: 2 }}
                strokeWidth={3} 
                name={chartConfig[selectedSensor].name} 
                animationDuration={500}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <Typography variant="body2" color="textSecondary" align="center" sx={{ py: 8 }}>
            Đang tải dữ liệu lịch sử...
          </Typography>
        )}
      </Card>
    </Box>
  );
}

export default Sensors;
