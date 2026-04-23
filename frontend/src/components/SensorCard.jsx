import { WiThermometer } from "react-icons/wi";
import { WiHumidity } from "react-icons/wi";
import { MdLightMode, MdOutlineGasMeter } from "react-icons/md";

const sensorConfig = {
  temp:  { label: "Nhiệt độ",  unit: "°C",  icon: WiThermometer,    color: "#ff6b6b" },
  humi:  { label: "Độ ẩm",     unit: "%",   icon: WiHumidity,       color: "#4ecdc4" },
  light: { label: "Ánh sáng",  unit: "lux", icon: MdLightMode,      color: "#ffd93d" },
  gas:   { label: "Khí gas",   unit: "ppm", icon: MdOutlineGasMeter, color: "#ff6b35" },
};

function SensorCard({ type, value, room }) {
  const config  = sensorConfig[type] || {};
  const Icon    = config.icon;
  const isAlert = type === "gas" && value !== "--" && value > 500;

  return (
    <div className="rounded-sm p-4 flex flex-col gap-2 transition-all"
         style={{
           background: isAlert ? "rgba(255,107,53,0.08)" : "rgba(255,255,255,0.03)",
           border: `1px solid ${isAlert ? "rgba(255,107,53,0.4)" : "rgba(255,255,255,0.07)"}`,
         }}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs tracking-widest uppercase"
              style={{ fontFamily: "monospace", color: "var(--muted)" }}>
          {config.label}
        </span>
        {Icon && <Icon size={20} style={{ color: config.color }} />}
      </div>

      {/* Value */}
      <div className="flex items-end gap-1">
        <span className="text-3xl font-bold"
              style={{ fontFamily: "monospace", color: isAlert ? "#ff6b35" : "var(--text)" }}>
          {value ?? "--"}
        </span>
        <span className="text-sm mb-1" style={{ color: "var(--muted)" }}>
          {config.unit}
        </span>
      </div>

      {/* Room */}
      <div className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
        {room || "--"}
      </div>

      {/* Alert badge */}
      {isAlert && (
        <div className="text-xs px-2 py-0.5 rounded-sm self-start"
             style={{
               background: "rgba(255,107,53,0.15)",
               color: "#ff6b35",
               border: "1px solid rgba(255,107,53,0.3)",
               fontFamily: "monospace",
             }}>
          ⚠ VƯỢT NGƯỠNG
        </div>
      )}
    </div>
  );
}

export default SensorCard;