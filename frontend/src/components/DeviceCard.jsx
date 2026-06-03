import { MdLightbulb, MdLightbulbOutline, MdLock, MdLockOpen } from "react-icons/md";
import { PiFan } from "react-icons/pi";
import { BsBellFill, BsBell } from "react-icons/bs";
import { Card, CardContent, Typography, Box, Chip, Button } from '@mui/material';

const typeConfig = {
  light: { iconOn: MdLightbulb,     iconOff: MdLightbulbOutline, color: "#f59e0b" }, // amber-500
  fan:   { iconOn: PiFan,           iconOff: PiFan,              color: "#10b981" }, // emerald-500
  alarm: { iconOn: BsBellFill,      iconOff: BsBell,             color: "#ef4444" }, // red-500
  door:  { iconOn: MdLockOpen,      iconOff: MdLock,             color: "#3b82f6" }, // blue-500
};

const modeColor = {
  Manual:   "default",
  AI:       "primary",
  Schedule: "secondary",
  Alert:    "error",
  Auto:     "primary",
};

const roomLabel = {
  living_room: "Phòng khách",
  bedroom:     "Phòng ngủ",
  kitchen:     "Phòng bếp",
  bathroom:    "Phòng tắm",
  entrance:    "Cửa chính",
};

const modeLabel = {
  Manual:   "Thủ công",
  AI:       "Trí tuệ nhân tạo",
  Schedule: "Lịch trình",
  Alert:    "Cảnh báo",
  Auto:     "Tự động",
};

function DeviceCard({ device, onToggle, aiMode }) {
  const config   = typeConfig[device.type] || typeConfig.light;
  const isOn     = device.status === 1;
  const Icon     = isOn ? config.iconOn : config.iconOff;
  const modeChipColor = modeColor[device.mode] || "default";
  const disabled = aiMode && device.type !== "door";

  return (
    <Card 
      sx={{ 
        height: '100%',
        opacity: disabled ? 0.7 : 1,
        transition: '0.3s',
        border: isOn ? `1px solid ${config.color}` : '1px solid #cbd5e1',
        bgcolor: isOn ? `${config.color}08` : 'background.paper',
        '&:hover': {
          transform: disabled ? 'none' : 'translateY(-2px)',
          boxShadow: disabled ? 0 : 2,
        }
      }}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Icon size={24} style={{ color: isOn ? config.color : '#94a3b8' }} />
          <Chip 
            label={modeLabel[device.mode || "Manual"] || device.mode} 
            size="small" 
            color={modeChipColor}
            variant="outlined"
            sx={{ fontWeight: 'bold', fontSize: '0.7rem' }}
          />
        </Box>

        {/* Name + room */}
        <Box sx={{ mb: 2, minHeight: 45 }}>
          <Typography variant="body2" fontWeight="bold" noWrap>
            {device.name}
          </Typography>
          <Typography variant="caption" color="textSecondary" display="block">
            {roomLabel[device.room] || device.room}
          </Typography>
        </Box>

        {/* Toggle button */}
        <Button
          fullWidth
          variant={isOn ? "contained" : "outlined"}
          disabled={disabled}
          onClick={() => !disabled && onToggle(device.id, device.status)}
          sx={{ 
            bgcolor: isOn && !disabled ? config.color : undefined,
            color: isOn && !disabled ? '#fff' : (isOn && disabled ? 'action.disabled' : 'text.primary'),
            borderColor: isOn ? 'transparent' : 'divider',
            '&:hover': {
              bgcolor: isOn ? `${config.color}dd` : 'action.hover',
            }
          }}
        >
          {isOn ? "BẬT" : "TẮT"}
        </Button>
      </CardContent>
    </Card>
  );
}

export default DeviceCard;