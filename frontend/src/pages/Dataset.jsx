import { useEffect, useState, useRef, useCallback } from "react";
import {
  MdAdd, MdDelete, MdEdit, MdCheck, MdClose,
  MdCameraAlt, MdStopCircle,
} from "react-icons/md";
import useStore from "../store";
import api from "../services/api";

// URL stream đi qua Vite proxy thay vì hardcode localhost:5000
const STREAM_URL = "/api/datasets/stream";

function Dataset() {
  const { datasets, fetchDatasets } = useStore();
  const [newName, setNewName] = useState("");
  const [editId, setEditId] = useState(null);
  const [editName, setEditName] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [activeDs, setActiveDs] = useState(null);
  const [error, setError] = useState("");
  const [confirmId, setConfirmId] = useState(null); // thay confirm() popup

  const pollRef = useRef(null);

  // ── Cleanup khi unmount ──────────────────────────────────────────────────
  useEffect(() => {
    fetchDatasets();
    return () => {
      stopPoll();
      // Dừng capture phía server nếu đang chạy
      api.post("/api/datasets/capture/stop").catch(() => { });
    };
  }, []);

  // ── Polling photo_count khi đang capture ────────────────────────────────
  const startPoll = useCallback(() => {
    stopPoll();
    pollRef.current = setInterval(() => fetchDatasets(), 1500);
  }, [fetchDatasets]);

  const stopPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  // ── Thêm dataset ─────────────────────────────────────────────────────────
  const handleAdd = async () => {
    const name = newName.trim();
    if (!name) return;
    try {
      await api.post("/api/datasets/", { name });
      setNewName("");
      fetchDatasets();
    } catch (e) {
      setError(e.response?.data?.error || "Lỗi thêm dataset");
    }
  };

  // ── Đổi tên ──────────────────────────────────────────────────────────────
  const handleRename = async (id) => {
    const name = editName.trim();
    if (!name) return;
    try {
      await api.put(`/api/datasets/${id}`, { name });
      setEditId(null);
      fetchDatasets();
    } catch (e) {
      setError(e.response?.data?.error || "Lỗi đổi tên");
    }
  };

  // ── Xoá dataset ──────────────────────────────────────────────────────────
  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/datasets/${id}`);
      setConfirmId(null);
      // Nếu đang capture dataset này thì reset UI
      if (activeDs?.id === id) {
        setCapturing(false);
        setActiveDs(null);
        stopPoll();
      }
      fetchDatasets();
    } catch (e) {
      setError("Lỗi xoá dataset");
    }
  };

  // ── Bắt đầu chụp ─────────────────────────────────────────────────────────
  const handleStartCapture = async (ds) => {
    try {
      await api.post("/api/datasets/capture/start", { name: ds.name });
      setActiveDs(ds);
      setCapturing(true);
      startPoll();
    } catch (e) {
      setError(e.response?.data?.error || "Lỗi bắt đầu chụp");
    }
  };

  // ── Dừng chụp ────────────────────────────────────────────────────────────
  const handleStopCapture = async () => {
    try {
      await api.post("/api/datasets/capture/stop");
    } catch (_) {
      // bỏ qua lỗi mạng
    } finally {
      setCapturing(false);
      setActiveDs(null);
      stopPoll();
      fetchDatasets();
    }
  };

  // ── Tính tổng ảnh đã chụp cho dataset đang active ────────────────────────
  const activePhotoCount = activeDs
    ? (datasets.find((d) => d.id === activeDs.id)?.photo_count ?? 0)
    : 0;

  return (
    <div className="pt-14 min-h-screen" style={{ background: "var(--bg)" }}>
      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold"
            style={{ fontFamily: "monospace", color: "var(--text)" }}>
            Face Dataset
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Quản lý dataset khuôn mặt để nhận diện mở cửa
          </p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-sm flex items-center justify-between"
            style={{
              background: "rgba(255,107,53,0.08)",
              border: "1px solid rgba(255,107,53,0.3)",
            }}>
            <span className="text-xs" style={{ color: "#ff6b35", fontFamily: "monospace" }}>
              {error}
            </span>
            <button onClick={() => setError("")}
              style={{ color: "#ff6b35", background: "none", border: "none", cursor: "pointer" }}>
              <MdClose size={16} />
            </button>
          </div>
        )}

        {/* Confirm xoá */}
        {confirmId && (
          <div className="mb-4 px-4 py-3 rounded-sm flex items-center justify-between"
            style={{
              background: "rgba(255,107,53,0.08)",
              border: "1px solid rgba(255,107,53,0.3)",
            }}>
            <span className="text-xs" style={{ color: "#ff6b35", fontFamily: "monospace" }}>
              Xác nhận xoá dataset này? Tất cả ảnh sẽ bị xoá vĩnh viễn.
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => handleDelete(confirmId)}
                className="px-3 py-1 rounded-sm text-xs"
                style={{
                  background: "rgba(255,107,53,0.2)",
                  color: "#ff6b35",
                  border: "1px solid rgba(255,107,53,0.4)",
                  cursor: "pointer",
                  fontFamily: "monospace",
                }}>
                Xoá
              </button>
              <button
                onClick={() => setConfirmId(null)}
                className="px-3 py-1 rounded-sm text-xs"
                style={{
                  background: "rgba(255,255,255,0.05)",
                  color: "var(--muted)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  cursor: "pointer",
                  fontFamily: "monospace",
                }}>
                Huỷ
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* ── Danh sách dataset ───────────────────────────────────────── */}
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
                <div className="text-sm text-center py-8"
                  style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                  Chưa có dataset nào
                </div>
              )}

              {datasets.map((ds) => (
                <div key={ds.id}
                  className="rounded-sm p-4 flex items-center justify-between transition-all"
                  style={{
                    background: activeDs?.id === ds.id
                      ? "rgba(184,245,80,0.05)"
                      : "rgba(255,255,255,0.03)",
                    border: `1px solid ${activeDs?.id === ds.id
                        ? "rgba(184,245,80,0.3)"
                        : "rgba(255,255,255,0.07)"
                      }`,
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
                        <button onClick={() => handleRename(ds.id)}
                          style={{ color: "var(--accent)", background: "none", border: "none", cursor: "pointer" }}>
                          <MdCheck size={16} />
                        </button>
                        <button onClick={() => setEditId(null)}
                          style={{ color: "var(--muted)", background: "none", border: "none", cursor: "pointer" }}>
                          <MdClose size={16} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="text-sm font-medium" style={{ color: "var(--text)" }}>
                          {ds.name}
                        </div>
                        <div className="text-xs mt-0.5"
                          style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                          {ds.photo_count} ảnh
                          {activeDs?.id === ds.id && capturing && (
                            <span style={{ color: "var(--accent)", marginLeft: 6 }}>
                              ● đang chụp
                            </span>
                          )}
                          {" · "}{new Date(ds.created_at).toLocaleDateString("vi-VN")}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Actions */}
                  {editId !== ds.id && (
                    <div className="flex items-center gap-1">
                      {/* Nút chụp — disable khi đang capture dataset khác */}
                      <button
                        onClick={() =>
                          capturing && activeDs?.id === ds.id
                            ? handleStopCapture()
                            : handleStartCapture(ds)
                        }
                        disabled={capturing && activeDs?.id !== ds.id}
                        className="p-1.5 rounded-sm transition-all hover:opacity-80"
                        style={{
                          color: capturing && activeDs?.id === ds.id ? "#ff6b35" : "var(--accent)",
                          background: capturing && activeDs?.id === ds.id
                            ? "rgba(255,107,53,0.1)"
                            : "rgba(184,245,80,0.08)",
                          border: "none",
                          cursor: capturing && activeDs?.id !== ds.id ? "not-allowed" : "pointer",
                          opacity: capturing && activeDs?.id !== ds.id ? 0.4 : 1,
                        }}>
                        {capturing && activeDs?.id === ds.id
                          ? <MdStopCircle size={15} />
                          : <MdCameraAlt size={15} />}
                      </button>
                      <button
                        onClick={() => { setEditId(ds.id); setEditName(ds.name); }}
                        disabled={capturing}
                        className="p-1.5 rounded-sm transition-all hover:opacity-80"
                        style={{
                          color: "var(--muted)",
                          background: "rgba(255,255,255,0.05)",
                          border: "none",
                          cursor: capturing ? "not-allowed" : "pointer",
                          opacity: capturing ? 0.4 : 1,
                        }}>
                        <MdEdit size={15} />
                      </button>
                      <button
                        onClick={() => setConfirmId(ds.id)}
                        disabled={capturing}
                        className="p-1.5 rounded-sm transition-all hover:opacity-80"
                        style={{
                          color: "#ff6b35",
                          background: "rgba(255,107,53,0.08)",
                          border: "none",
                          cursor: capturing ? "not-allowed" : "pointer",
                          opacity: capturing ? 0.4 : 1,
                        }}>
                        <MdDelete size={15} />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* ── Webcam ─────────────────────────────────────────────────── */}
          <div>
            <div className="rounded-sm overflow-hidden"
              style={{
                border: "1px solid rgba(255,255,255,0.07)",
                background: "rgba(255,255,255,0.02)",
              }}>

              {/* Header */}
              <div className="px-4 py-3 flex items-center justify-between"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                <div>
                  <span className="text-xs font-medium"
                    style={{ fontFamily: "monospace", color: "var(--text)" }}>
                    {capturing ? `Đang chụp: ${activeDs?.name}` : "Camera"}
                  </span>
                  {capturing && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <div className="w-1.5 h-1.5 rounded-full animate-pulse"
                        style={{ background: "#ff6b35" }} />
                      <span className="text-xs"
                        style={{ color: "#ff6b35", fontFamily: "monospace" }}>
                        LIVE · {activePhotoCount}/25 ảnh
                      </span>
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
                {/* Luôn render <img> khi đang capture — tránh reload src */}
                <img
                  src={capturing ? STREAM_URL : undefined}
                  alt="camera"
                  className="w-full h-full object-cover"
                  style={{ display: capturing ? "block" : "none" }}
                />
                {!capturing && (
                  <div className="text-xs text-center"
                    style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                    <MdCameraAlt size={32}
                      style={{ margin: "0 auto 8px", opacity: 0.3 }} />
                    Chọn dataset và nhấn <MdCameraAlt style={{ display: "inline" }} /> để bắt đầu
                  </div>
                )}
              </div>

              {/* Hướng dẫn góc */}
              {capturing && (
                <div className="px-4 py-3">
                  <div className="text-xs mb-2"
                    style={{ color: "var(--muted)", fontFamily: "monospace" }}>
                    Hướng dẫn chụp 5 góc (5 ảnh/góc):
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {[
                      { key: "Thang", label: "Thẳng" },
                      { key: "Trai", label: "Trái" },
                      { key: "Phai", label: "Phải" },
                      { key: "Len", label: "Lên" },
                      { key: "Xuong", label: "Xuống" },
                    ].map(({ key, label }) => (
                      <span key={key} className="text-xs px-2 py-0.5 rounded-sm"
                        style={{
                          fontFamily: "monospace",
                          background: "rgba(184,245,80,0.08)",
                          color: "var(--accent)",
                          border: "1px solid rgba(184,245,80,0.2)",
                        }}>
                        {label}
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