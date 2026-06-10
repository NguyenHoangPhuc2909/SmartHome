import { WiThermometer, WiHumidity } from "react-icons/wi";
import { MdLightMode, MdOutlineGasMeter } from "react-icons/md";
import { Card, CardContent, Typography, Box, Chip } from '@mui/material';
import { AreaChart, Area, ResponsiveContainer } from "recharts";

const sensorConfig = {
  temp:  { label: "Nhiệt độ",  unit: "°C",  icon: WiThermometer,    color: "#ef4444" },
  humi:  { label: "Độ ẩm",     unit: "%",   icon: WiHumidity,       color: "#3b82f6" },
  light: { label: "Ánh sáng",  unit: "lux", icon: MdLightMode,      color: "#f59e0b" },
  gas:   { label: "Khí gas",   unit: "ppm", icon: MdOutlineGasMeter, color: "#8b5cf6" },
};

function SensorCard({ type, value, room, selected, onClick, history = [] }) {
  const config  = sensorConfig[type] || {};
  const Icon    = config.icon;
  const isAlert = type === "gas" && value !== "--" && value > 3000;

  // Tính trend (so sánh value hiện tại với giá trị đầu tiên trong history)
  let trendStr = null;
  let trendColor = "text.secondary";
  let trendIcon = "";

  if (history.length > 0 && value !== "--") {
    const oldestValue = history[0][type];
    if (oldestValue != null) {
      const diff = parseFloat(value) - parseFloat(oldestValue);
      if (Math.abs(diff) >= 0.1) {
        if (diff > 0) {
          trendStr = `+${diff.toFixed(1)} ${config.unit}`;
          trendIcon = "↑";
          trendColor = type === "gas" || type === "temp" ? "error.main" : "success.main";
        } else {
          trendStr = `${diff.toFixed(1)} ${config.unit}`;
          trendIcon = "↓";
          trendColor = type === "gas" || type === "temp" ? "success.main" : "error.main";
        }
      } else {
         trendStr = `0 ${config.unit}`;
         trendIcon = "−";
         trendColor = "text.secondary";
      }
    }
  }

  // Dữ liệu cho biểu đồ Mini
  const chartData = history.map(item => ({
    value: item[type]
  }));

  return (
    <Card 
      onClick={onClick}
      sx={{ 
        height: '100%',
        bgcolor: isAlert ? 'error.light' : selected ? 'primary.50' : 'background.paper',
        color: isAlert ? 'error.contrastText' : 'text.primary',
        transition: '0.3s',
        border: isAlert 
          ? '2px solid #ef4444' 
          : selected 
            ? '2px solid #3b82f6' 
            : '1px solid #cbd5e1',
        cursor: onClick ? 'pointer' : 'default',
        transform: selected ? 'translateY(-2px)' : 'none',
        boxShadow: selected ? 3 : 1,
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 3,
        }
      }}
    >
      <CardContent sx={{ p: 2, pb: 1, flexGrow: 1, zIndex: 1 }}>
        {/* Header: Label + Icon */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="overline" color={isAlert ? 'inherit' : 'textSecondary'} fontWeight="bold" sx={{ display: 'block', lineHeight: 1.2, mb: 0.5 }}>
              {config.label}
            </Typography>
            <Typography variant="caption" color={isAlert ? 'inherit' : 'textSecondary'}>
              {room || "--"}
            </Typography>
          </Box>
          <Box sx={{ 
            p: 1, 
            borderRadius: '12px', 
            bgcolor: isAlert ? 'rgba(255,255,255,0.2)' : `${config.color}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            {Icon && <Icon size={24} style={{ color: isAlert ? '#fff' : config.color }} />}
          </Box>
        </Box>

        {/* Value + Trend */}
        <Box sx={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5 }}>
            <Typography variant="h4" fontWeight="800">
              {value ?? "--"}
            </Typography>
            <Typography variant="body2" color={isAlert ? 'inherit' : 'textSecondary'} fontWeight="bold">
              {config.unit}
            </Typography>
          </Box>
          
          {/* Trend indicator */}
          {!isAlert && trendStr && (
            <Typography variant="caption" fontWeight="bold" sx={{ color: trendColor, display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
              {trendIcon} {Math.abs(parseFloat(trendStr)).toFixed(1)} {config.unit}
            </Typography>
          )}
        </Box>

        {/* Alert badge */}
        {isAlert && (
          <Chip 
            label="⚠ VƯỢT NGƯỠNG" 
            size="small" 
            color="error" 
            sx={{ fontWeight: 'bold', mt: 1 }}
          />
        )}
      </CardContent>

      {/* Mini Chart (Sparkline) at the bottom */}
      <Box sx={{ width: '100%', height: 60, mt: 'auto', position: 'relative', bottom: -5 }}>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`color${type}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isAlert ? '#fff' : config.color} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={isAlert ? '#fff' : config.color} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke={isAlert ? '#fff' : config.color} 
                strokeWidth={2}
                fillOpacity={1} 
                fill={`url(#color${type})`} 
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <Box sx={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography variant="caption" color="textSecondary" sx={{ opacity: 0.5 }}>Chưa có dữ liệu</Typography>
          </Box>
        )}
      </Box>
    </Card>
  );
}

export default SensorCard;