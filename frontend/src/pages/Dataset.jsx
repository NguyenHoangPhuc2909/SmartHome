import { useEffect, useState } from "react";
import { MdAdd, MdDelete, MdEdit, MdCheck, MdClose, MdCameraAlt, MdStopCircle } from "react-icons/md";
import useStore from "../store";
import api from "../services/api";

function Dataset() {
  const { datasets, fetchDatasets } = useStore();
  const [newName, setNewName] = useState("");
  const [editId, setEditId] = useState(null);
  const [editName, setEditName] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [activeDs, setActiveDs] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { fetchDatasets(); }, []);

  useEffect(() => {
    if (!capturing) return;
    const interval = setInterval(() => {
      fetchDatasets();
    }, 1500);
    return () => clearInterval(interval);
  }, [capturing]);

  const handleAdd = async () => {
    if (!newName.trim()) return;
    try {
      await api.post("/api/datasets/", { name: newName.trim() });
      setNewName("");
      fetchDatasets();
    } catch (e) {
      setError(e.response?.data?.error || "Lỗi thêm dataset");
    }
  };

  const handleRename = async (id) => {
    if (!editName.trim()) return;
    try {
      await api.put(`/api/datasets/${id}`, { name: editName.trim() });
      setEditId(null);
      fetchDatasets();
    } catch (e) {
      setError(e.response?.data?.error || "Lỗi đổi tên");
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Xoá dataset này?")) return;
    try {
      await api.delete(`/api/datasets/${id}`);
      fetchDatasets();
    } catch (e) {
      setError("Lỗi xoá dataset");
    }
  };

  const handleStartCapture = async (ds) => {
    try {
      await api.post("/api/datasets/capture/start", { name: ds.name });
      setActiveDs(ds);
      setCapturing(true);
    } catch (e) {
      setError("Lỗi bắt đầu chụp");
    }
  };

  const handleStopCapture = async () => {
    try {
      await api.post("/api/datasets/capture/stop");
      setCapturing(false);
      setActiveDs(null);
      fetchDatasets();
    } catch (e) {
      setCapturing(false);
      setActiveDs(null);
    }
  };

  return (
    <div className="pt-14 min-h-screen" style={{ background: "var(--bg)" }}>
      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold" style={{ fontFamily: "monospace", color: "var(--text)" }}>
            Face Dataset
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Quản lý dataset khuôn mặt để nhận diện mở cửa
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-sm flex items-center justify-between"
            style={{ background: "rgba(255,107,53,0.08)", border: "1px solid rgba(255,107,53,0.3)" }}>
            <span className="text-xs" style={{ color: "#ff6b35", fontFamily: "monospace" }}>{error}</span>
            <button onClick={() => setError("")} style={{ color: "#ff6b35", background: "none", border: "none", cursor: "pointer" }}>
              <MdClose size={16} />
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Left — danh sách dataset */}
          <div>
            {/* Add form */}
            <div className="flex gap-2 mb-4">
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
                placeholder="Tên người..."
                className="flex-1 px-3 py-2 rounded-sm text-sm outline-none"
                style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "var(--text)",
                  fontFamily: "monospace",
                }}
              />
              <button onClick={handleAdd}
                className="px-4 py-2 rounded-sm flex items-center gap-1 text-xs font-medium transition-all hover:opacity-80"
                style={{
                  background: "var(--accent)",
                  color: "#0d0f0f",
                  border: "none",
                  cursor: "pointer",
                  fontFamily: "monospace",
                }}>
                <MdAdd size={16} /> Thêm
              </button>
            </div>

            {/* Dataset list */}
            <div className="flex flex-col gap-2">
              {datasets.length === 0 && (
                <div className="text-sm text-center py-8" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                  Chưa có dataset nào
                </div>
              )}
              {datasets.map((ds) => (
                <div key={ds.id}
                  className="rounded-sm p-4 flex items-center justify-between transition-all"
                  style={{
                    background: activeDs?.id === ds.id ? "rgba(184,245,80,0.05)" : "rgba(255,255,255,0.03)",
                    border: `1px solid ${activeDs?.id === ds.id ? "rgba(184,245,80,0.3)" : "rgba(255,255,255,0.07)"}`,
                  }}>

                  {/* Name + info */}
                  <div className="flex-1 mr-3">
                    {editId === ds.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleRename(ds.id)}
                          className="flex-1 px-2 py-1 rounded-sm text-xs outline-none"
                          style={{
                            background: "rgba(255,255,255,0.08)",
                            border: "1px solid rgba(255,255,255,0.15)",
                            color: "var(--text)",
                            fontFamily: "monospace",
                          }}
                          autoFocus
                        />
                        <button onClick={() => handleRename(ds.id)} style={{ color: "var(--accent)", background: "none", border: "none", cursor: "pointer" }}>
                          <MdCheck size={16} />
                        </button>
                        <button onClick={() => setEditId(null)} style={{ color: "var(--muted)", background: "none", border: "none", cursor: "pointer" }}>
                          <MdClose size={16} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="text-sm font-medium" style={{ color: "var(--text)" }}>{ds.name}</div>
                        <div className="text-xs mt-0.5" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                          {ds.photo_count} ảnh
                          {activeDs?.id === ds.id && capturing && (
                            <span style={{ color: "var(--accent)", marginLeft: 6 }}>
                              ● đang chụp
                            </span>
                          )}
                          · {new Date(ds.created_at).toLocaleDateString("vi-VN")}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Actions */}
                  {editId !== ds.id && (
                    <div className="flex items-center gap-1">
                      <button onClick={() => handleStartCapture(ds)}
                        className="p-1.5 rounded-sm transition-all hover:opacity-80"
                        style={{ color: "var(--accent)", background: "rgba(184,245,80,0.08)", border: "none", cursor: "pointer" }}>
                        <MdCameraAlt size={15} />
                      </button>
                      <button onClick={() => { setEditId(ds.id); setEditName(ds.name); }}
                        className="p-1.5 rounded-sm transition-all hover:opacity-80"
                        style={{ color: "var(--muted)", background: "rgba(255,255,255,0.05)", border: "none", cursor: "pointer" }}>
                        <MdEdit size={15} />
                      </button>
                      <button onClick={() => handleDelete(ds.id)}
                        className="p-1.5 rounded-sm transition-all hover:opacity-80"
                        style={{ color: "#ff6b35", background: "rgba(255,107,53,0.08)", border: "none", cursor: "pointer" }}>
                        <MdDelete size={15} />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Right — webcam */}
          <div>
            <div className="rounded-sm overflow-hidden"
              style={{ border: "1px solid rgba(255,255,255,0.07)", background: "rgba(255,255,255,0.02)" }}>

              {/* Webcam header */}
              <div className="px-4 py-3 flex items-center justify-between"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                <div>
                  <span className="text-xs font-medium" style={{ fontFamily: "monospace", color: "var(--text)" }}>
                    {capturing ? `Đang chụp: ${activeDs?.name}` : "Camera"}
                  </span>
                  {capturing && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "#ff6b35" }} />
                      <span className="text-xs" style={{ color: "#ff6b35", fontFamily: "monospace" }}>LIVE</span>
                    </div>
                  )}
                </div>
                {capturing && (
                  <button onClick={handleStopCapture}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-sm text-xs transition-all hover:opacity-80"
                    style={{
                      background: "rgba(255,107,53,0.12)",
                      color: "#ff6b35",
                      border: "1px solid rgba(255,107,53,0.3)",
                      cursor: "pointer",
                      fontFamily: "monospace",
                    }}>
                    <MdStopCircle size={14} /> Dừng
                  </button>
                )}
              </div>

              {/* Video */}
              <div className="relative aspect-video flex items-center justify-center"
                style={{ background: "#000" }}>
                <img
                  src="http://localhost:5000/api/datasets/stream"
                  alt="camera"
                  className="w-full h-full object-cover"
                  style={{ display: capturing ? "block" : "none" }}
                />
                {!capturing && (
                  <div className="text-xs text-center" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                    <MdCameraAlt size={32} style={{ margin: "0 auto 8px", opacity: 0.3 }} />
                    Chọn dataset và nhấn chụp để bắt đầu
                  </div>
                )}
              </div>

              {/* Instructions */}
              {capturing && (
                <div className="px-4 py-3">
                  <div className="text-xs mb-2" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                    Hướng dẫn chụp 5 góc:
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {["Thẳng", "Trái", "Phải", "Lên", "Xuống"].map((angle) => (
                      <span key={angle} className="text-xs px-2 py-0.5 rounded-sm"
                        style={{
                          fontFamily: "monospace",
                          background: "rgba(184,245,80,0.08)",
                          color: "var(--accent)",
                          border: "1px solid rgba(184,245,80,0.2)",
                        }}>
                        {angle}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default Dataset;