import { WiThermometer, WiHumidity } from "react-icons/wi";
import { MdLightMode, MdOutlineGasMeter } from "react-icons/md";
import { Card, CardContent, Typography, Box, Chip } from '@mui/material';

const sensorConfig = {
  temp:  { label: "Nhiệt độ",  unit: "°C",  icon: WiThermometer,    color: "#ff6b6b" },
  humi:  { label: "Độ ẩm",     unit: "%",   icon: WiHumidity,       color: "#4ecdc4" },
  light: { label: "Ánh sáng",  unit: "lux", icon: MdLightMode,      color: "#ffd93d" },
  gas:   { label: "Khí gas",   unit: "ppm", icon: MdOutlineGasMeter, color: "#ff6b35" },
};

function SensorCard({ type, value, room, selected, onClick }) {
  const config  = sensorConfig[type] || {};
  const Icon    = config.icon;
  const isAlert = type === "gas" && value !== "--" && value > 500;

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
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: 3,
        }
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="overline" color={isAlert ? 'inherit' : 'textSecondary'} fontWeight="bold">
            {config.label}
          </Typography>
          {Icon && <Icon size={24} style={{ color: isAlert ? '#fff' : config.color }} />}
        </Box>

        {/* Value */}
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5, mb: 1 }}>
          <Typography variant="h4" fontWeight="bold">
            {value ?? "--"}
          </Typography>
          <Typography variant="body2" color={isAlert ? 'inherit' : 'textSecondary'}>
            {config.unit}
          </Typography>
        </Box>

        {/* Room */}
        <Typography variant="caption" display="block" color={isAlert ? 'inherit' : 'textSecondary'} sx={{ mb: isAlert ? 1 : 0 }}>
          {room || "--"}
        </Typography>

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
    </Card>
  );
}

export default SensorCard;