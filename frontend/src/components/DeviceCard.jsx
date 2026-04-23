import { MdLightbulb, MdLightbulbOutline } from "react-icons/md";
import { PiFan } from "react-icons/pi";
import { BsBellFill, BsBell } from "react-icons/bs";
import { MdLock, MdLockOpen } from "react-icons/md";

const typeConfig = {
  light: { iconOn: MdLightbulb,     iconOff: MdLightbulbOutline, color: "#ffd93d" },
  fan:   { iconOn: PiFan,           iconOff: PiFan,              color: "#4ecdc4" },
  alarm: { iconOn: BsBellFill,      iconOff: BsBell,             color: "#ff6b35" },
  door:  { iconOn: MdLockOpen,      iconOff: MdLock,             color: "#b8f550" },
};

const modeColor = {
  Manual:   { bg: "rgba(255,255,255,0.08)", color: "#f0f0ec" },
  AI:       { bg: "rgba(184,245,80,0.12)",  color: "#b8f550" },
  Schedule: { bg: "rgba(78,205,196,0.12)",  color: "#4ecdc4" },
  Alert:    { bg: "rgba(255,107,53,0.12)",  color: "#ff6b35" },
  Auto:     { bg: "rgba(184,245,80,0.12)",  color: "#b8f550" },
};

const roomLabel = {
  living_room: "Phòng khách",
  bedroom:     "Phòng ngủ",
  kitchen:     "Phòng bếp",
  bathroom:    "Phòng tắm",
  entrance:    "Cửa chính",
};

function DeviceCard({ device, onToggle, aiMode }) {
  const config   = typeConfig[device.type] || typeConfig.light;
  const isOn     = device.status === 1;
  const Icon     = isOn ? config.iconOn : config.iconOff;
  const modeCfg  = modeColor[device.mode] || modeColor.Manual;
  const disabled = aiMode && device.type !== "door";

  return (
    <div className="rounded-sm p-4 flex flex-col gap-3 transition-all"
         style={{
           background: isOn ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.02)",
           border: `1px solid ${isOn ? "rgba(255,255,255,0.15)" : "rgba(255,255,255,0.07)"}`,
           opacity: disabled ? 0.6 : 1,
         }}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <Icon size={24} style={{ color: isOn ? config.color : "var(--muted)" }} />
        {/* Mode badge */}
        <span className="text-xs px-2 py-0.5 rounded-sm"
              style={{
                fontFamily: "monospace",
                background: modeCfg.bg,
                color:      modeCfg.color,
                border:     `1px solid ${modeCfg.color}33`,
              }}>
          {device.mode || "Manual"}
        </span>
      </div>

      {/* Name + room */}
      <div>
        <div className="text-sm font-medium" style={{ color: "var(--text)" }}>
          {device.name}
        </div>
        <div className="text-xs mt-0.5" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
          {roomLabel[device.room] || device.room}
        </div>
      </div>

      {/* Toggle button */}
      <button
        onClick={() => !disabled && onToggle(device.id, device.status)}
        disabled={disabled}
        className="w-full py-2 rounded-sm text-xs font-medium tracking-wide transition-all"
        style={{
          fontFamily: "monospace",
          background: isOn
            ? disabled ? "rgba(255,255,255,0.05)" : `${config.color}22`
            : "rgba(255,255,255,0.05)",
          color:   isOn ? config.color : "var(--muted)",
          border:  `1px solid ${isOn ? `${config.color}44` : "rgba(255,255,255,0.07)"}`,
          cursor:  disabled ? "not-allowed" : "pointer",
        }}>
        {isOn ? "● BẬT" : "○ TẮT"}
      </button>
    </div>
  );
}

export default DeviceCard;