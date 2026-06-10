import { useEffect, useState, useRef } from "react";
import { MdCheckCircle, MdCancel, MdWarning, MdRefresh, MdFilterList, MdPhotoCamera, MdClose } from "react-icons/md";
import useStore from "../store";
import {
  Box, Typography, Button, Card, CardContent, Grid, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, LinearProgress, useTheme, Alert,
  Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress, IconButton,
  Switch
} from "@mui/material";

const FACE_CONFIDENCE_THRESHOLD = 0.6;

const antispoofText = (label) => {
  if (label === "LIVE") return "Mặt thật";
  if (label === "SPOOF") return "Giả mạo";
  if (label === "UNCERTAIN") return "Không chắc";
  if (label === "DISABLED") return "Bỏ qua fake/real";
  if (label === "NO_FACE") return "Không thấy mặt";
  if (label === "ERROR") return "Lỗi fake/real";
  return label || "--";
};

const antispoofChipColor = (label) => {
  if (label === "LIVE") return "success";
  if (label === "UNCERTAIN") return "warning";
  if (label === "DISABLED") return "default";
  return "error";
};

const antispoofTextColor = (label) => {
  if (label === "LIVE") return "success.main";
  if (label === "UNCERTAIN") return "warning.main";
  if (label === "DISABLED") return "text.secondary";
  return "error.main";
};

const deniedReasonText = (reason) => {
  if (reason === "SPOOF") return "Phát hiện giả mạo";
  if (reason === "NO_FACE") return "Không thấy mặt";
  if (reason === "ANTISPOOF_UNCERTAIN") return "Ảnh chưa đủ chắc, hãy thử lại";
  if (reason === "ANTISPOOF_ERROR") return "Lỗi kiểm tra fake/real";
  if (reason === "UNKNOWN") return "Không nhận diện được";
  return reason || "";
};

const verificationSeverity = (result) => {
  if (result.result === "GRANTED") return "success";
  if (result.denied_reason === "ANTISPOOF_UNCERTAIN") return "warning";
  return "error";
};

function Access() {
  const theme = useTheme();
  const { accessLogs, fetchAccessLogs } = useStore();
  const [filter, setFilter] = useState("ALL");
  const [dateFilter, setDateFilter] = useState("");
  const [liveImage, setLiveImage] = useState(null);
  const [selectedLogId, setSelectedLogId] = useState(null);
  const [antispoofEnabled, setAntispoofEnabled] = useState(true);
  const [antispoofSaving, setAntispoofSaving] = useState(false);

  // Camera state & ref
  const [showCameraDialog, setShowCameraDialog] = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const videoRef = useRef(null);

  const startCamera = async () => {
    setVerificationResult(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 320, height: 320, facingMode: "user" } 
      });
      setCameraStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Không thể truy cập camera laptop/điện thoại của bạn. Vui lòng đảm bảo trình duyệt đã được cấp quyền camera và trang web chạy trên kết nối bảo mật (HTTPS hoặc localhost).");
      setShowCameraDialog(false);
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      setCameraStream(null);
    }
  };

  const handleOpenDialog = () => {
    setShowCameraDialog(true);
    setTimeout(startCamera, 100);
  };

  const handleCloseDialog = () => {
    stopCamera();
    setShowCameraDialog(false);
    setVerificationResult(null);
  };

  const fetchAntispoofSetting = async () => {
    try {
      const response = await fetch("/api/access/antispoof-setting");
      if (response.ok) {
        const data = await response.json();
        setAntispoofEnabled(Boolean(data.enabled));
      }
    } catch (err) {
      console.error("Error loading fake/real setting:", err);
    }
  };

  const handleAntispoofToggle = async (event) => {
    const nextEnabled = event.target.checked;
    const previousEnabled = antispoofEnabled;
    setAntispoofEnabled(nextEnabled);
    setAntispoofSaving(true);

    try {
      const response = await fetch("/api/access/antispoof-setting", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: nextEnabled }),
      });

      if (!response.ok) {
        throw new Error("Could not save fake/real setting");
      }

      const data = await response.json();
      setAntispoofEnabled(Boolean(data.enabled));
    } catch (err) {
      console.error("Error saving fake/real setting:", err);
      setAntispoofEnabled(previousEnabled);
      alert("Không thể lưu trạng thái fake/real. Hãy thử lại.");
    } finally {
      setAntispoofSaving(false);
    }
  };

  const captureAndVerify = async () => {
    if (!videoRef.current) return;
    setVerifying(true);
    setVerificationResult(null);
    
    try {
      const canvas = document.createElement("canvas");
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      const ctx = canvas.getContext("2d");
      // Flip canvas to match mirror effect of video
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
      
      canvas.toBlob(async (blob) => {
        if (!blob) {
          setVerifying(false);
          return;
        }
        
        const formData = new FormData();
        formData.append("image", blob, "capture.jpg");
        
        try {
          const response = await fetch("/api/access/recognize", {
            method: "POST",
            body: formData,
          });
          
          if (response.ok) {
            const data = await response.json();
            setVerificationResult(data);
            fetchAccessLogs(); // refresh the logs list behind the modal
          } else {
            setVerificationResult({ error: "Xác thực không thành công. Hãy thử lại." });
          }
        } catch (err) {
          console.error("Verification error:", err);
          setVerificationResult({ error: "Lỗi kết nối máy chủ khi xác thực" });
        } finally {
          setVerifying(false);
        }
      }, "image/jpeg", 0.95);
    } catch (err) {
      console.error("Capture error:", err);
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchAccessLogs();
    fetchAntispoofSetting();
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("/api/access/latest-image");
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          setLiveImage((prev) => {
            if (prev) URL.revokeObjectURL(prev);
            return url;
          });
        }
      } catch (e) {
      }
    }, 1000);

    return () => {
      clearInterval(interval);
      if (liveImage) URL.revokeObjectURL(liveImage);
    };
  }, []);

  const latestLog = accessLogs[0];
  const displayLog = selectedLogId ? accessLogs.find(l => l.id === selectedLogId) || latestLog : latestLog;

  const filtered = accessLogs.filter((l) => {
    if (filter !== "ALL" && l.result !== filter) return false;
    if (dateFilter) {
      const logDate = new Date(l.timestamp).toLocaleDateString("en-CA");
      if (logDate !== dateFilter) return false;
    }
    return true;
  });

  const grantedCount = accessLogs.filter((l) => l.result === "GRANTED").length;
  const deniedCount = accessLogs.filter((l) => l.result === "DENIED").length;
  const alertCount = accessLogs.filter((l) => l.is_alert).length;

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: { xs: 'flex-start', md: 'center' },
        gap: 2,
        flexDirection: { xs: 'column', md: 'row' },
        mb: 4
      }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Lịch sử truy cập</Typography>
          <Typography variant="body2" color="textSecondary">
            Lịch sử nhận diện khuôn mặt tại cửa và các cảnh báo.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
          <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            px: 1.5,
            py: 0.5,
            minHeight: 40,
            border: `1px solid ${theme.palette.divider}`,
            borderRadius: 1,
            bgcolor: 'background.paper'
          }}>
            <Typography variant="body2" fontWeight="bold" sx={{ whiteSpace: 'nowrap' }}>
              Fake/real
            </Typography>
            <Chip
              label={antispoofEnabled ? "Bật" : "Tắt"}
              color={antispoofEnabled ? "success" : "default"}
              size="small"
              sx={{ borderRadius: 1, fontWeight: 'bold' }}
            />
            <Switch
              checked={antispoofEnabled}
              onChange={handleAntispoofToggle}
              disabled={antispoofSaving}
              color="success"
              size="small"
              inputProps={{ "aria-label": "Bật tắt fake/real" }}
            />
          </Box>
          <Button 
            variant="contained" 
            color="primary"
            startIcon={<MdPhotoCamera />}
            onClick={handleOpenDialog}
            sx={{ fontWeight: 'bold' }}
          >
            Xác thực khuôn mặt (Cam)
          </Button>
          <Button 
            variant="outlined" 
            startIcon={<MdRefresh />}
            onClick={fetchAccessLogs}
            sx={{ fontWeight: 'bold' }}
          >
            Làm mới
          </Button>
        </Box>
      </Box>

      {/* Live Widget */}
      <Card sx={{ mb: 4,  border: `1px solid ${theme.palette.divider}`, boxShadow: 'none' }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {(!selectedLogId || (latestLog && selectedLogId === latestLog.id)) ? (
                <>
                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: 'error.main', animation: 'pulse 2s infinite' }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="error">
                    LIVE RECOGNITION
                  </Typography>
                </>
              ) : (
                <>
                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: 'primary.main' }} />
                  <Typography variant="subtitle2" fontWeight="bold" color="primary">
                    CHI TIẾT LỊCH SỬ
                  </Typography>
                  <Button size="small" onClick={() => setSelectedLogId(null)} sx={{ ml: 2, fontSize: '0.7rem' }}>
                    Quay lại Live
                  </Button>
                </>
              )}
            </Box>
            <Typography variant="caption" color="textSecondary">
              {(!selectedLogId || (latestLog && selectedLogId === latestLog.id)) ? "Cập nhật mỗi 1 giây" : "Chế độ xem lịch sử"}
            </Typography>
          </Box>

          <Grid container spacing={4} sx={{ alignItems: 'center' }}>
            {/* Live Camera Feed */}
            <Grid xs={12} sm={4} md={3} sx={{ display: 'flex', justifyContent: 'center' }}>
              <Box sx={{ width: 160, height: 160, borderRadius: 1, overflow: 'hidden', bgcolor: 'black', border: `1px solid ${theme.palette.divider}` }}>
                {selectedLogId && selectedLogId !== latestLog?.id ? (
                  <img src={`/api/access/image/${selectedLogId}`} alt="Snapshot" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : liveImage ? (
                  <img src={liveImage} alt="Live" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'text.secondary' }}>
                    <Typography variant="caption">Chờ kết nối camera...</Typography>
                  </Box>
                )}
              </Box>
            </Grid>

            {/* Latest Result */}
            <Grid xs={12} sm={8} md={9}>
              {displayLog ? (
                <Grid container spacing={3}>
                  <Grid xs={12} sm={6} md={3}>
                    <Typography variant="caption" color="textSecondary" display="block">👤 Nhân vật</Typography>
                    <Typography variant="subtitle1" fontWeight="bold" color={displayLog.matched_name ? 'textPrimary' : 'error'}>
                      {displayLog.matched_name || "Không nhận ra"}
                    </Typography>
                  </Grid>

                  <Grid xs={12} sm={6} md={3}>
                    <Typography variant="caption" color="textSecondary" display="block">📊 Độ chính xác</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="subtitle1" fontWeight="bold" color={displayLog.confidence >= FACE_CONFIDENCE_THRESHOLD ? 'success.main' : 'error.main'}>
                        {(displayLog.confidence * 100).toFixed(1)}%
                      </Typography>
                      <Box sx={{ flex: 1, ml: 1 }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={displayLog.confidence * 100} 
                          color={displayLog.confidence >= FACE_CONFIDENCE_THRESHOLD ? 'success' : 'error'}
                          sx={{ height: 6, borderRadius: 1 }}
                        />
                      </Box>
                    </Box>
                  </Grid>

                  <Grid xs={12} sm={6} md={3}>
                    <Typography variant="caption" color="textSecondary" display="block">⚠️ Kết quả</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                      <Chip 
                        icon={displayLog.result === "GRANTED" ? <MdCheckCircle /> : <MdCancel />} 
                        label={displayLog.result === "GRANTED" ? "CHO VÀO" : "TỪ CHỐI"} 
                        color={displayLog.result === "GRANTED" ? "success" : "error"}
                        variant="outlined"
                        size="small"
                        sx={{ fontWeight: 'bold', borderRadius: 1 }}
                      />
                      {displayLog.is_alert && (
                        <Chip 
                          icon={<MdWarning />} 
                          label="Còi" 
                          color="error" 
                          size="small"
                          sx={{ fontWeight: 'bold', borderRadius: 1 }}
                        />
                      )}
                      {displayLog.antispoof_label && (
                        <Chip
                          label={antispoofText(displayLog.antispoof_label)}
                          color={antispoofChipColor(displayLog.antispoof_label)}
                          variant="outlined"
                          size="small"
                          sx={{ fontWeight: 'bold', borderRadius: 1 }}
                        />
                      )}
                    </Box>
                    {displayLog.denied_reason && (
                      <Typography variant="caption" color="error" display="block" sx={{ mt: 0.5 }}>
                        {deniedReasonText(displayLog.denied_reason)}
                      </Typography>
                    )}
                  </Grid>

                  <Grid xs={12} sm={6} md={3}>
                    <Typography variant="caption" color="textSecondary" display="block">🕐 Thời gian</Typography>
                    <Typography variant="subtitle2" fontWeight="bold" mt={0.5}>
                      {new Date(displayLog.timestamp).toLocaleString("vi-VN")}
                    </Typography>
                  </Grid>
                </Grid>
              ) : (
                <Typography color="textSecondary">Chưa có lịch sử nhận diện.</Typography>
              )}
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Cảnh báo Alert */}
      {alertCount > 0 && (
        <Alert severity="error" icon={<MdWarning fontSize="inherit" />} sx={{ mb: 4,  fontWeight: 'bold' }}>
          Đã phát hiện {alertCount} lần người lạ (Còi cảnh báo đã được kích hoạt).
        </Alert>
      )}

      {/* Thống kê nhỏ */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: 2, mb: 4 }}>
        {[
          { label: "Tổng số lượt", value: accessLogs.length, color: 'text.primary', bgcolor: 'background.paper' },
          { label: "Đã cho vào", value: grantedCount, color: 'success.main', bgcolor: 'success.light' },
          { label: "Từ chối", value: deniedCount, color: 'error.main', bgcolor: 'error.light' },
        ].map((stat, idx) => (
          <Box sx={{ gridColumn: { xs: 'span 12', sm: 'span 4' } }} key={idx}>
            <Card sx={{ border: `1px solid ${theme.palette.divider}`, boxShadow: 'none', height: '100%' }}>
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Typography variant="caption" color="textSecondary">{stat.label}</Typography>
                <Typography variant="h5" fontWeight="bold" sx={{ color: stat.color }}>{stat.value}</Typography>
              </CardContent>
            </Card>
          </Box>
        ))}
      </Box>

      {/* Bảng Logs */}
      <Card sx={{ border: `1px solid ${theme.palette.divider}`, boxShadow: 'none' }}>
        {/* Bộ lọc */}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${theme.palette.divider}`, flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <MdFilterList size={20} color={theme.palette.text.secondary} />
            <Box sx={{ display: 'flex', gap: 1 }}>
              {[
                { key: "ALL", label: "Tất cả", color: 'primary' },
                { key: "GRANTED", label: "Cho vào", color: 'success' },
                { key: "DENIED", label: "Từ chối", color: 'error' }
              ].map((f) => (
                <Button
                  key={f.key}
                  variant={filter === f.key ? "contained" : "outlined"}
                  color={f.color}
                  size="small"
                  onClick={() => setFilter(f.key)}
                  disableElevation
                  sx={{ fontWeight: filter === f.key ? 'bold' : 'normal' }}
                >
                  {f.label}
                </Button>
              ))}
            </Box>
          </Box>
          <TextField
            type="date"
            size="small"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            sx={{ '& .MuiOutlinedInput-root': {  } }}
          />
        </Box>

        {/* Table Container */}
        <TableContainer>
          <Table sx={{ minWidth: 650 }} aria-label="access logs table">
            <TableHead sx={{ bgcolor: 'background.default' }}>
              <TableRow>
                <TableCell width={80}><strong>Ảnh</strong></TableCell>
                <TableCell><strong>Người</strong></TableCell>
                <TableCell><strong>Độ chính xác</strong></TableCell>
                <TableCell><strong>Kết quả</strong></TableCell>
                <TableCell align="right"><strong>Thời gian</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} align="center" sx={{ py: 6 }}>
                    <Typography color="textSecondary">Không có dữ liệu phù hợp.</Typography>
                  </TableCell>
                </TableRow>
              )}
              {filtered.map((log) => (
                <TableRow 
                  key={log.id}
                  onClick={() => setSelectedLogId(log.id)}
                  sx={{ 
                    cursor: 'pointer',
                    bgcolor: selectedLogId === log.id ? 'action.selected' : 'inherit',
                    '&:hover': { bgcolor: 'action.hover' } 
                  }}
                >
                  {/* Ảnh */}
                  <TableCell>
                    {log.image_path ? (
                      <Box 
                        component="img"
                        src={`/api/access/image/${log.id}`}
                        alt="face"
                        sx={{ width: 40, height: 40, borderRadius: 1, objectFit: 'cover', border: `1px solid ${theme.palette.divider}` }}
                        onError={(e) => {
                          e.target.style.display = "none";
                          e.target.nextElementSibling.style.display = "flex";
                        }}
                      />
                    ) : null}
                    <Box 
                      sx={{ 
                        width: 40, height: 40, borderRadius: 1, bgcolor: 'action.selected', 
                        display: log.image_path ? 'none' : 'flex', alignItems: 'center', justifyContent: 'center',
                        color: 'text.disabled'
                      }}
                    >
                      ?
                    </Box>
                  </TableCell>

                  {/* Người */}
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold" color={log.matched_name ? 'textPrimary' : 'error'}>
                      {log.matched_name || "Không nhận ra"}
                    </Typography>
                    {log.is_alert && (
                      <Typography variant="caption" color="error" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <MdWarning /> Đã hú còi
                      </Typography>
                    )}
                    {log.antispoof_label && (
                      <Typography
                        variant="caption"
                        color={antispoofTextColor(log.antispoof_label)}
                        display="block"
                      >
                        Fake/real: {antispoofText(log.antispoof_label)}
                        {log.antispoof_label !== "DISABLED" && log.antispoof_score != null ? ` (${(log.antispoof_score * 100).toFixed(1)}%)` : ""}
                      </Typography>
                    )}
                  </TableCell>

                  {/* Độ chính xác */}
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body2" fontWeight="bold" color={log.result === 'GRANTED' ? 'success.main' : 'error.main'}>
                        {log.confidence ? `${(log.confidence * 100).toFixed(1)}%` : "--"}
                      </Typography>
                      <Box sx={{ width: 60 }}>
                        <LinearProgress 
                          variant="determinate" 
                          value={log.confidence ? log.confidence * 100 : 0} 
                          color={log.result === 'GRANTED' ? 'success' : 'error'}
                          sx={{ height: 4, borderRadius: 1 }}
                        />
                      </Box>
                    </Box>
                  </TableCell>

                  {/* Kết quả */}
                  <TableCell>
                    <Chip 
                      icon={log.result === "GRANTED" ? <MdCheckCircle /> : <MdCancel />} 
                      label={log.result === "GRANTED" ? "Cho vào" : "Từ chối"} 
                      color={log.result === "GRANTED" ? "success" : "error"}
                      variant="outlined"
                      size="small"
                      sx={{ borderRadius: 1, fontWeight: 'bold' }}
                    />
                  </TableCell>

                  {/* Thời gian */}
                  <TableCell align="right">
                    <Typography variant="body2" color="textPrimary">
                      {new Date(log.timestamp).toLocaleTimeString("vi-VN")}
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      {new Date(log.timestamp).toLocaleDateString("vi-VN")}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Camera Dialog */}
      <Dialog 
        open={showCameraDialog} 
        onClose={handleCloseDialog}
        maxWidth="xs"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
            overflow: 'hidden'
          }
        }}
      >
        <DialogTitle sx={{ m: 0, p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" fontWeight="bold">Xác thực khuôn mặt</Typography>
          <IconButton
            aria-label="close"
            onClick={handleCloseDialog}
            sx={{
              color: (theme) => theme.palette.grey[500],
            }}
          >
            <MdClose />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            {/* Camera Preview Box */}
            <Box 
              sx={{ 
                width: '100%', 
                aspectRatio: '1/1', 
                maxWidth: 320,
                borderRadius: 2, 
                overflow: 'hidden', 
                bgcolor: 'black', 
                position: 'relative',
                border: `1px solid ${theme.palette.divider}`,
                boxShadow: theme.shadows[3]
              }}
            >
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform: 'scaleX(-1)' // Mirror for natural look
                }}
              />
              
              {verifying && (
                <Box 
                  sx={{ 
                    position: 'absolute', 
                    top: 0, 
                    left: 0, 
                    width: '100%', 
                    height: '100%', 
                    bgcolor: 'rgba(0,0,0,0.6)', 
                    display: 'flex', 
                    flexDirection: 'column',
                    alignItems: 'center', 
                    justifyContent: 'center',
                    gap: 1,
                    color: 'white',
                    zIndex: 2
                  }}
                >
                  <CircularProgress color="inherit" />
                  <Typography variant="body2" fontWeight="medium">Đang xác thực...</Typography>
                </Box>
              )}
            </Box>

            {/* Results Display */}
            {verificationResult && (
              <Box sx={{ width: '100%' }}>
                {verificationResult.error ? (
                  <Alert severity="error" sx={{ borderRadius: 2 }}>
                    {verificationResult.error}
                  </Alert>
                ) : (
                  <Alert 
                    severity={verificationSeverity(verificationResult)}
                    icon={verificationResult.result === "GRANTED" ? <MdCheckCircle fontSize="inherit" /> : <MdCancel fontSize="inherit" />}
                    sx={{ borderRadius: 2 }}
                  >
                    <Typography variant="subtitle2" fontWeight="bold">
                      {verificationResult.result === "GRANTED" ? "ĐÃ CẤP QUYỀN TRUY CẬP" : "TỪ CHỐI TRUY CẬP"}
                    </Typography>
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2">
                        👤 Người: <strong>{verificationResult.matched_name || "Không nhận dạng được"}</strong>
                      </Typography>
                      {verificationResult.confidence !== undefined && (
                        <Typography variant="body2">
                          📊 Độ tin cậy: <strong>{(verificationResult.confidence * 100).toFixed(1)}%</strong>
                        </Typography>
                      )}
                      {verificationResult.antispoof && (
                        <Typography variant="body2">
                          Fake/real: <strong>{antispoofText(verificationResult.antispoof.label)}</strong>
                          {verificationResult.antispoof.label !== "DISABLED" && verificationResult.antispoof.prob_spoof != null
                            ? ` (${(verificationResult.antispoof.prob_spoof * 100).toFixed(1)}% spoof)`
                            : ""}
                        </Typography>
                      )}
                      {verificationResult.denied_reason && (
                        <Typography variant="body2" color="error">
                          Lý do: <strong>{deniedReasonText(verificationResult.denied_reason)}</strong>
                        </Typography>
                      )}
                    </Box>
                  </Alert>
                )}
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button 
            onClick={handleCloseDialog} 
            color="inherit"
            variant="text"
            sx={{ fontWeight: 'bold' }}
            disabled={verifying}
          >
            Đóng
          </Button>
          <Button
            onClick={captureAndVerify}
            variant="contained"
            color="primary"
            startIcon={verifying ? <CircularProgress size={20} color="inherit" /> : <MdPhotoCamera />}
            disabled={verifying || !cameraStream}
            sx={{ fontWeight: 'bold' }}
          >
            {verifying ? "Đang xử lý..." : "Chụp & Xác thực"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Access;
