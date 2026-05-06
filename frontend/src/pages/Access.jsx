import { useEffect, useState } from "react";
import { MdCheckCircle, MdCancel, MdWarning, MdFilterList, MdRefresh } from "react-icons/md";
import useStore from "../store";

function Access() {
  const { accessLogs, fetchAccessLogs } = useStore();
  const [filter, setFilter] = useState("ALL");   // ALL | GRANTED | DENIED
  const [dateFilter, setDateFilter] = useState("");
  const [liveImage, setLiveImage] = useState(null);

  // Fetch access logs mỗi 5 giây
  useEffect(() => {
    fetchAccessLogs();
    const interval = setInterval(fetchAccessLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch ảnh live mỗi 1 giây
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("/api/access/latest-image");
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          // Revoke URL cũ để không rò rỉ memory
          setLiveImage((prev) => {
            if (prev) URL.revokeObjectURL(prev);
            return url;
          });
        }
      } catch (e) {
        // Silent fail — không hiển thị lỗi nếu chưa có ảnh
      }
    }, 1000);

    return () => {
      clearInterval(interval);
      if (liveImage) URL.revokeObjectURL(liveImage);
    };
  }, []);

  const latestLog = accessLogs[0];

  const filtered = accessLogs.filter((l) => {
    if (filter !== "ALL" && l.result !== filter) return false;
    if (dateFilter) {
      const logDate = new Date(l.timestamp).toLocaleDateString("en-CA"); // YYYY-MM-DD
      if (logDate !== dateFilter) return false;
    }
    return true;
  });

  const grantedCount = accessLogs.filter((l) => l.result === "GRANTED").length;
  const deniedCount = accessLogs.filter((l) => l.result === "DENIED").length;
  const alertCount = accessLogs.filter((l) => l.is_alert).length;

  return (
    <div className="pt-14 min-h-screen" style={{ background: "var(--bg)" }}>
      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Header + Live Widget */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Left: Title */}
          <div className="lg:col-span-2">
            <h1 className="text-2xl font-bold" style={{ fontFamily: "monospace", color: "var(--text)" }}>
              Access Logs
            </h1>
            <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
              Lịch sử nhận diện khuôn mặt tại cửa
            </p>
          </div>

          {/* Right: Refresh Button */}
          <div className="flex justify-end">
            <button onClick={fetchAccessLogs}
              className="flex items-center gap-2 px-3 py-2 rounded-sm text-xs transition-all hover:opacity-80"
              style={{
                background: "rgba(255,255,255,0.05)",
                color: "var(--muted)",
                border: "1px solid rgba(255,255,255,0.07)",
                cursor: "pointer",
                fontFamily: "monospace",
              }}>
              <MdRefresh size={14} /> Làm mới
            </button>
          </div>
        </div>

        {/* Live Recognition Widget */}
        <div className="rounded-sm p-6 mb-8"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.1)",
          }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: "#ff6b35" }} />
              <span className="text-xs font-bold tracking-widest"
                style={{ color: "#ff6b35", fontFamily: "monospace" }}>
                🔴 LIVE RECOGNITION
              </span>
            </div>
            <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
              Cập nhật mỗi 1 giây
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Image Preview */}
            <div className="md:col-span-1">
              {liveImage ? (
                <img src={liveImage} alt="latest" className="w-full h-40 rounded-sm object-cover"
                  style={{ border: "1px solid rgba(255,255,255,0.1)" }} />
              ) : (
                <div className="w-full h-40 rounded-sm flex items-center justify-center"
                  style={{ background: "#000", border: "1px solid rgba(255,255,255,0.1)" }}>
                  <span style={{ color: "var(--muted)", fontSize: "12px", fontFamily: "monospace" }}>
                    Chờ ảnh từ ESP32...
                  </span>
                </div>
              )}
            </div>

            {/* Recognition Results */}
            <div className="md:col-span-2">
              {latestLog ? (
                <div className="space-y-3">
                  {/* Name */}
                  <div>
                    <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                      👤 Nhân vật
                    </span>
                    <div className="text-sm font-medium mt-1"
                      style={{
                        color: latestLog.matched_name ? "var(--text)" : "#ff6b35",
                        fontFamily: "monospace"
                      }}>
                      {latestLog.matched_name || "Không nhận ra"}
                    </div>
                  </div>

                  {/* Confidence */}
                  <div>
                    <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                      📊 Độ tự tin
                    </span>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm font-bold"
                        style={{
                          color: latestLog.confidence >= 0.65 ? "#b8f550" : "#ff6b35",
                          fontFamily: "monospace"
                        }}>
                        {(latestLog.confidence * 100).toFixed(1)}%
                      </span>
                      <div className="flex-1 h-2 rounded-full"
                        style={{ background: "rgba(255,255,255,0.08)" }}>
                        <div className="h-2 rounded-full transition-all"
                          style={{
                            width: `${(latestLog.confidence) * 100}%`,
                            background: latestLog.confidence >= 0.65 ? "#b8f550" : "#ff6b35",
                          }} />
                      </div>
                    </div>
                  </div>

                  {/* Result */}
                  <div>
                    <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                      ⚠️ Kết quả
                    </span>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm"
                        style={{
                          background: latestLog.result === "GRANTED" ? "rgba(184,245,80,0.1)" : "rgba(255,107,53,0.1)",
                          border: `1px solid ${latestLog.result === "GRANTED" ? "rgba(184,245,80,0.3)" : "rgba(255,107,53,0.3)"}`,
                        }}>
                        {latestLog.result === "GRANTED"
                          ? <MdCheckCircle size={14} style={{ color: "#b8f550" }} />
                          : <MdCancel size={14} style={{ color: "#ff6b35" }} />
                        }
                        <span className="text-xs font-bold"
                          style={{
                            fontFamily: "monospace",
                            color: latestLog.result === "GRANTED" ? "#b8f550" : "#ff6b35",
                          }}>
                          {latestLog.result === "GRANTED" ? "✓ CHO VÀO" : "✗ TỪ CHỐI"}
                        </span>
                      </div>
                      {latestLog.is_alert && (
                        <div className="flex items-center gap-1 px-2 py-1 rounded-sm"
                          style={{
                            background: "rgba(255,107,53,0.1)",
                            border: "1px solid rgba(255,107,53,0.2)",
                          }}>
                          <MdWarning size={12} style={{ color: "#ff6b35" }} />
                          <span className="text-xs" style={{ color: "#ff6b35", fontFamily: "monospace" }}>
                            Còi
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Timestamp */}
                  <div>
                    <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                      🕐 Thời gian
                    </span>
                    <div className="text-xs mt-1" style={{ color: "var(--text)", fontFamily: "monospace" }}>
                      {new Date(latestLog.timestamp).toLocaleString("vi-VN")}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-40"
                  style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                  <span className="text-sm">Chưa có bản ghi nào</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: "Tổng", value: accessLogs.length, color: "var(--text)", bg: "rgba(255,255,255,0.03)" },
            { label: "Cho vào", value: grantedCount, color: "#b8f550", bg: "rgba(184,245,80,0.05)" },
            { label: "Từ chối", value: deniedCount, color: "#ff6b35", bg: "rgba(255,107,53,0.05)" },
          ].map((stat) => (
            <div key={stat.label} className="rounded-sm p-4"
              style={{ background: stat.bg, border: "1px solid rgba(255,255,255,0.07)" }}>
              <div className="text-xs mb-1" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                {stat.label}
              </div>
              <div className="text-2xl font-bold" style={{ fontFamily: "monospace", color: stat.color }}>
                {stat.value}
              </div>
            </div>
          ))}
        </div>

        {/* Alert count */}
        {alertCount > 0 && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-sm mb-6"
            style={{
              background: "rgba(255,107,53,0.08)",
              border: "1px solid rgba(255,107,53,0.3)",
            }}>
            <MdWarning size={16} style={{ color: "#ff6b35" }} />
            <span className="text-xs" style={{ color: "#ff6b35", fontFamily: "monospace" }}>
              {alertCount} lần phát hiện người lạ — còi đã được kích hoạt
            </span>
          </div>
        )}

        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <MdFilterList size={16} style={{ color: "var(--muted)" }} />
          <div className="flex gap-1">
            {["ALL", "GRANTED", "DENIED"].map((f) => (
              <button key={f} onClick={() => setFilter(f)}
                className="px-3 py-1 rounded-sm text-xs transition-all"
                style={{
                  fontFamily: "monospace",
                  background: filter === f ? "rgba(255,255,255,0.08)" : "transparent",
                  color: filter === f
                    ? f === "GRANTED" ? "#b8f550" : f === "DENIED" ? "#ff6b35" : "var(--text)"
                    : "var(--muted)",
                  border: `1px solid ${filter === f ? "rgba(255,255,255,0.15)" : "transparent"}`,
                  cursor: "pointer",
                }}>
                {f === "ALL" ? "Tất cả" : f === "GRANTED" ? "Cho vào" : "Từ chối"}
              </button>
            ))}
          </div>

          {/* Date filter */}
          <input type="date"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="ml-auto px-3 py-1 rounded-sm text-xs outline-none"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "var(--text)",
              fontFamily: "monospace",
              colorScheme: "dark",
            }} />
        </div>

        {/* Table */}
        <div className="rounded-sm overflow-hidden"
          style={{ border: "1px solid rgba(255,255,255,0.07)" }}>

          {/* Table header */}
          <div className="grid grid-cols-5 px-4 py-2"
            style={{
              background: "rgba(255,255,255,0.03)",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
            }}>
            {["Ảnh", "Người", "Confidence", "Kết quả", "Thời gian"].map((h) => (
              <div key={h} className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                {h}
              </div>
            ))}
          </div>

          {/* Rows */}
          {filtered.length === 0 && (
            <div className="text-sm text-center py-12" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
              Không có dữ liệu
            </div>
          )}

          {filtered.map((log) => (
            <div key={log.id}
              className="grid grid-cols-5 items-center px-4 py-3 transition-all hover:bg-white/5"
              style={{
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                background: log.is_alert ? "rgba(255,107,53,0.04)" : "transparent",
              }}>

              {/* Ảnh */}
              <div>
                {log.image_path ? (
                  <img src={`/api/access/image/${log.id}`}
                    alt="face"
                    className="w-10 h-10 rounded-sm object-cover"
                    style={{ border: "1px solid rgba(255,255,255,0.1)" }}
                    onError={(e) => {
                      e.target.style.display = "none";
                      e.target.nextElementSibling.style.display = "flex";
                    }} />
                ) : null}
                <div className="w-10 h-10 rounded-sm flex items-center justify-center"
                  style={{ background: "rgba(255,255,255,0.05)", color: "var(--muted)", display: log.image_path ? "none" : "flex" }}>
                  ?
                </div>
              </div>

              {/* Người */}
              <div>
                <div className="text-sm" style={{ color: log.matched_name ? "var(--text)" : "var(--muted)" }}>
                  {log.matched_name || "Không nhận ra"}
                </div>
                {log.is_alert && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <MdWarning size={10} style={{ color: "#ff6b35" }} />
                    <span className="text-xs" style={{ color: "#ff6b35", fontFamily: "monospace" }}>
                      Còi kích hoạt
                    </span>
                  </div>
                )}
              </div>

              {/* Confidence */}
              <div>
                <div className="text-sm font-medium"
                  style={{
                    fontFamily: "monospace",
                    color: log.confidence >= 0.65 ? "#b8f550" : "#ff6b35",
                  }}>
                  {log.confidence ? `${(log.confidence * 100).toFixed(1)}%` : "--"}
                </div>
                {/* Progress bar */}
                <div className="mt-1 h-1 rounded-full w-20"
                  style={{ background: "rgba(255,255,255,0.08)" }}>
                  <div className="h-1 rounded-full transition-all"
                    style={{
                      width: `${(log.confidence || 0) * 100}%`,
                      background: log.confidence >= 0.65 ? "#b8f550" : "#ff6b35",
                    }} />
                </div>
              </div>

              {/* Kết quả */}
              <div>
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-sm self-start w-fit"
                  style={{
                    background: log.result === "GRANTED" ? "rgba(184,245,80,0.1)" : "rgba(255,107,53,0.1)",
                    border: `1px solid ${log.result === "GRANTED" ? "rgba(184,245,80,0.25)" : "rgba(255,107,53,0.25)"}`,
                  }}>
                  {log.result === "GRANTED"
                    ? <MdCheckCircle size={12} style={{ color: "#b8f550" }} />
                    : <MdCancel size={12} style={{ color: "#ff6b35" }} />
                  }
                  <span className="text-xs font-medium"
                    style={{
                      fontFamily: "monospace",
                      color: log.result === "GRANTED" ? "#b8f550" : "#ff6b35",
                    }}>
                    {log.result === "GRANTED" ? "Cho vào" : "Từ chối"}
                  </span>
                </div>
              </div>

              {/* Thời gian */}
              <div className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                <div>{new Date(log.timestamp).toLocaleDateString("vi-VN")}</div>
                <div>{new Date(log.timestamp).toLocaleTimeString("vi-VN")}</div>
              </div>

            </div>
          ))}
        </div>

      </div>
    </div>
  );
}

export default Access;