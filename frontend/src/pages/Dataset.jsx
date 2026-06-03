import { useEffect, useState, useRef, useCallback } from "react";
import {
  MdAdd, MdDelete, MdEdit, MdCheck, MdClose,
  MdCameraAlt, MdStopCircle,
} from "react-icons/md";
import useStore from "../store";
import api from "../services/api";
import {
  Box, Typography, Button, TextField, Card, CardContent,
  IconButton, Grid, Dialog, DialogTitle, DialogContent, DialogActions,
  List, ListItem, ListItemText, Divider, Alert, CircularProgress, useTheme
} from "@mui/material";

const STREAM_URL = "/api/datasets/stream";

function Dataset() {
  const theme = useTheme();
  const { datasets, fetchDatasets } = useStore();
  const [newName, setNewName] = useState("");
  const [editId, setEditId] = useState(null);
  const [editName, setEditName] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [activeDs, setActiveDs] = useState(null);
  const [error, setError] = useState("");
  const [confirmId, setConfirmId] = useState(null);

  const pollRef = useRef(null);

  useEffect(() => {
    fetchDatasets();
    return () => {
      stopPoll();
      api.post("/api/datasets/capture/stop").catch(() => { });
    };
  }, []);

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

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/datasets/${id}`);
      setConfirmId(null);
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

  const handleStopCapture = async () => {
    try {
      await api.post("/api/datasets/capture/stop");
    } catch (_) {
    } finally {
      setCapturing(false);
      setActiveDs(null);
      stopPoll();
      fetchDatasets();
    }
  };

  const activePhotoCount = activeDs
    ? (datasets.find((d) => d.id === activeDs.id)?.photo_count ?? 0)
    : 0;

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="bold">Dữ liệu khuôn mặt</Typography>
        <Typography variant="body2" color="textSecondary">
          Quản lý dữ liệu khuôn mặt để nhận diện mở cửa tự động.
        </Typography>
      </Box>

      {/* Error Banner */}
      {error && (
        <Alert severity="error" onClose={() => setError("")} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Dialog Xoá */}
      <Dialog open={!!confirmId} onClose={() => setConfirmId(null)} PaperProps={{ sx: {  } }}>
        <DialogTitle>Xác nhận xoá</DialogTitle>
        <DialogContent>
          <Typography>Xóa dữ liệu khuôn mặt này? Tất cả ảnh sẽ bị xóa vĩnh viễn và không thể khôi phục.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmId(null)} color="inherit">Huỷ</Button>
          <Button onClick={() => handleDelete(confirmId)} color="error" variant="contained" disableElevation>Xoá</Button>
        </DialogActions>
      </Dialog>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' }, gap: 4 }}>
        {/* Cột trái: Danh sách Dataset */}
        <Box>
          <Card sx={{ border: `1px solid ${theme.palette.divider}`, boxShadow: 'none' }}>
            <Box sx={{ display: 'flex', gap: 1, p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Tên người mới..."
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
              <Button 
                variant="contained" 
                color="primary" 
                disableElevation
                startIcon={<MdAdd />}
                onClick={handleAdd}
                sx={{  }}
              >
                Thêm
              </Button>
            </Box>

            <List disablePadding>
              {datasets.length === 0 && (
                <Typography color="textSecondary" align="center" sx={{ py: 4 }}>
                  Chưa có dữ liệu nào
                </Typography>
              )}
              {datasets.map((ds, index) => {
                const isActive = activeDs?.id === ds.id;
                return (
                  <Box key={ds.id}>
                    <ListItem 
                      sx={{ 
                        py: 2,
                        px: 3,
                        bgcolor: isActive ? `${theme.palette.primary.main}11` : 'transparent',
                        borderLeft: isActive ? `4px solid ${theme.palette.primary.main}` : '4px solid transparent',
                        transition: '0.2s'
                      }}
                    >
                      <Box sx={{ flex: 1 }}>
                        {editId === ds.id ? (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <TextField
                              size="small"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onKeyDown={(e) => e.key === "Enter" && handleRename(ds.id)}
                              autoFocus
                              fullWidth
                            />
                            <IconButton onClick={() => handleRename(ds.id)} color="primary" size="small"><MdCheck /></IconButton>
                            <IconButton onClick={() => setEditId(null)} size="small"><MdClose /></IconButton>
                          </Box>
                        ) : (
                          <>
                            <Typography variant="subtitle2" fontWeight="bold" color="textPrimary">
                              {ds.name}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              {ds.photo_count} ảnh 
                              {isActive && capturing && (
                                <span style={{ color: theme.palette.error.main, marginLeft: 8, fontWeight: 'bold' }}>
                                  ● Đang chụp
                                </span>
                              )}
                              {" · "}{new Date(ds.created_at).toLocaleDateString("vi-VN")}
                            </Typography>
                          </>
                        )}
                      </Box>

                      {editId !== ds.id && (
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <IconButton 
                            onClick={() => capturing && isActive ? handleStopCapture() : handleStartCapture(ds)}
                            disabled={capturing && !isActive}
                            color={capturing && isActive ? "error" : "primary"}
                            sx={{ bgcolor: capturing && isActive ? 'error.light' : 'primary.light', color: capturing && isActive ? 'error.main' : 'primary.main', borderRadius: 1 }}
                          >
                            {capturing && isActive ? <MdStopCircle /> : <MdCameraAlt />}
                          </IconButton>
                          <IconButton 
                            onClick={() => { setEditId(ds.id); setEditName(ds.name); }}
                            disabled={capturing}
                            sx={{ borderRadius: 1 }}
                          >
                            <MdEdit />
                          </IconButton>
                          <IconButton 
                            onClick={() => setConfirmId(ds.id)}
                            disabled={capturing}
                            color="error"
                            sx={{ borderRadius: 1 }}
                          >
                            <MdDelete />
                          </IconButton>
                        </Box>
                      )}
                    </ListItem>
                    {index < datasets.length - 1 && <Divider />}
                  </Box>
                );
              })}
            </List>
          </Card>
        </Box>

        {/* Cột phải: Webcam */}
        <Box>
          <Card sx={{ border: `1px solid ${theme.palette.divider}`, boxShadow: 'none',  overflow: 'hidden' }}>
            <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${theme.palette.divider}`, bgcolor: 'background.paper' }}>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold">
                  {capturing ? `Đang chụp: ${activeDs?.name}` : "Camera trực tiếp"}
                </Typography>
                {capturing && (
                  <Typography variant="caption" color="error" fontWeight="bold">
                    LIVE · Đã chụp {activePhotoCount}/25 ảnh
                  </Typography>
                )}
              </Box>
              {capturing && (
                <Button 
                  variant="outlined" 
                  color="error" 
                  size="small" 
                  startIcon={<MdStopCircle />}
                  onClick={handleStopCapture}
                  sx={{  }}
                >
                  Dừng
                </Button>
              )}
            </Box>

            <Box sx={{ position: 'relative', width: '100%', pt: '75%', bgcolor: '#000' }}>
              <img
                src={capturing ? STREAM_URL : undefined}
                alt="Camera feed"
                style={{
                  position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', objectFit: 'cover',
                  display: capturing ? 'block' : 'none'
                }}
              />
              {!capturing && (
                <Box sx={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'text.secondary' }}>
                  <MdCameraAlt size={48} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <Typography variant="body2">Chọn dữ liệu và nhấn máy ảnh để bắt đầu chụp</Typography>
                </Box>
              )}
            </Box>

            {capturing && (
              <Box sx={{ p: 2, bgcolor: 'background.default' }}>
                <Typography variant="caption" color="textSecondary" display="block" mb={1}>
                  Hướng dẫn xoay mặt để chụp đủ 5 góc (mỗi góc 5 ảnh):
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {["Thẳng", "Trái", "Phải", "Lên", "Xuống"].map((label) => (
                    <Box key={label} sx={{ px: 1.5, py: 0.5, border: `1px solid ${theme.palette.primary.main}`, color: 'primary.main', bgcolor: `${theme.palette.primary.main}15`, borderRadius: 1, fontSize: '0.75rem', fontWeight: 'bold' }}>
                      {label}
                    </Box>
                  ))}
                </Box>
              </Box>
            )}
          </Card>
        </Box>
      </Box>
    </Box>
  );
}

export default Dataset;