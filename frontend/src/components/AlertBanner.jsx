import { MdWarning, MdClose } from "react-icons/md";

function AlertBanner({ alerts, onDismiss }) {
  if (!alerts || alerts.length === 0) return null;

  return (
    <div className="rounded-sm p-4 mb-6 flex items-start justify-between gap-4"
         style={{
           background: "rgba(255,107,53,0.08)",
           border: "1px solid rgba(255,107,53,0.4)",
         }}>

      <div className="flex items-start gap-3">
        <MdWarning size={20} style={{ color: "#ff6b35", flexShrink: 0, marginTop: 1 }} />
        <div>
          <div className="text-sm font-medium mb-1" style={{ color: "#ff6b35", fontFamily: "monospace" }}>
            CẢNH BÁO HỆ THỐNG
          </div>
          <div className="flex flex-col gap-1">
            {alerts.map((alert, i) => (
              <div key={i} className="text-xs" style={{ color: "rgba(255,107,53,0.8)" }}>
                {alert.is_alert && alert.result === "DENIED"
                  ? `⚠ Phát hiện người lạ tại cửa — ${new Date(alert.timestamp).toLocaleTimeString("vi-VN")}`
                  : `⚠ ${alert.message || "Cảnh báo không xác định"}`
                }
              </div>
            ))}
          </div>
        </div>
      </div>

      {onDismiss && (
        <button onClick={onDismiss}
                className="transition-opacity hover:opacity-70 flex-shrink-0"
                style={{ color: "#ff6b35", background: "none", border: "none", cursor: "pointer" }}>
          <MdClose size={18} />
        </button>
      )}
    </div>
  );
}

export default AlertBanner;