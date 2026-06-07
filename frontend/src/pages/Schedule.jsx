import { useEffect, useState } from "react";
import { MdAdd, MdDelete, MdAccessTime, MdLightbulb, MdLock } from "react-icons/md";
import { PiFan } from "react-icons/pi";
import { BsBellFill } from "react-icons/bs";
import useStore from "../store";
import api from "../services/api";
import {
  Box, Typography, Button, Card, CardContent, Grid, TextField, 
  MenuItem, Switch, IconButton, Alert, ToggleButton, ToggleButtonGroup,
  useTheme
} from "@mui/material";

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const DAY_LABEL = { mon: "T2", tue: "T3", wed: "T4", thu: "T5", fri: "T6", sat: "T7", sun: "CN" };

const roomLabel = {
  living_room: "Phòng khách",
  bedroom:     "Phòng ngủ",
  kitchen:     "Phòng bếp",
  bathroom:    "Phòng tắm",
  entrance:    "Cửa chính",
};

const deviceIcon = {
  light: MdLightbulb,
  fan: PiFan,
  alarm: BsBellFill,
  door: MdLock,
};

const defaultForm = {
  device_id: "",
  actionMode: 1, // 1 = Bật, 0 = Tắt, 2 = Bật và Tắt
  onHour: 18,
  onMinute: 0,
  offHour: 22,
  offMinute: 0,
  days: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
};

function Schedule() {
  const theme = useTheme();
  const { schedules, devices, fetchSchedules, fetchDevices } = useStore();
  const [form, setForm] = useState(defaultForm);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [editId, setEditId] = useState(null);

  useEffect(() => {
    fetchSchedules();
    fetchDevices();
  }, []);

  const handleDaysChange = (event, newDays) => {
    setForm({ ...form, days: newDays });
  };

  const handleReset = () => {
    setForm(defaultForm);
    setError("");
    setSuccess("");
    setEditId(null);
  }

  const handleAdd = async () => {
    setError("");
    setSuccess("");
    if (!form.device_id) return setError("Vui lòng chọn thiết bị");
    if (form.days.length === 0) return setError("Vui lòng chọn ít nhất 1 ngày");
    
    try {
      const daysStr = form.days.join(",");

      if (form.actionMode === 1 || form.actionMode === 2) {
        if (form.onHour === "" || form.onMinute === "") return setError("Vui lòng nhập giờ bật hợp lệ");
        // Tạo lịch Bật
        await api.post("/api/schedules/", {
          device_id: form.device_id,
          action: 1,
          hour: Number(form.onHour),
          minute: Number(form.onMinute),
          days: daysStr,
          is_active: true
        });
      }

      if (form.actionMode === 0 || form.actionMode === 2) {
        if (form.offHour === "" || form.offMinute === "") return setError("Vui lòng nhập giờ tắt hợp lệ");
        // Tạo lịch Tắt
        await api.post("/api/schedules/", {
          device_id: form.device_id,
          action: 0,
          hour: Number(form.offHour),
          minute: Number(form.offMinute),
          days: daysStr,
          is_active: true
        });
      }

      if (editId) {
        // Xoá lịch cũ nếu đang ở chế độ chỉnh sửa
        await api.delete(`/api/schedules/${editId}`);
      }

      setForm(defaultForm);
      setEditId(null);
      setSuccess(editId ? "Cập nhật lịch thành công!" : "Lưu lịch thành công!");
      setTimeout(() => setSuccess(""), 3000);
      fetchSchedules();
    } catch (e) {
      setError("Lỗi thêm lịch. Vui lòng thử lại.");
    }
  };

  const handleToggle = async (id) => {
    try {
      await api.post(`/api/schedules/${id}/toggle`);
      fetchSchedules();
    } catch (e) {
      setError("Lỗi cập nhật lịch");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Bạn có chắc chắn muốn xoá lịch này?")) return;
    try {
      await api.delete(`/api/schedules/${id}`);
      fetchSchedules();
    } catch (e) {
      setError("Lỗi xoá lịch");
    }
  };

  const getDeviceName = (id) => devices.find((d) => d.id === id)?.name || `Thiết bị ${id}`;
  const getDeviceRoom = (id) => {
    const room = devices.find((d) => d.id === id)?.room;
    return roomLabel[room] || room || "";
  };
  const getDeviceIcon = (id) => {
    const type = devices.find((d) => d.id === id)?.type;
    const Icon = deviceIcon[type] || MdLightbulb;
    return <Icon size={16} />;
  };

  const handleEdit = (s) => {
    setEditId(s.id);
    setForm({
      device_id: s.device_id,
      actionMode: s.action,
      onHour: s.action === 1 ? s.hour : 18,
      onMinute: s.action === 1 ? s.minute : 0,
      offHour: s.action === 0 ? s.hour : 22,
      offMinute: s.action === 0 ? s.minute : 0,
      days: s.days.split(",").filter(Boolean),
    });
    // Cuộn lên đầu trang (chỗ Form) trên mobile
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="bold">Lịch trình</Typography>
        <Typography variant="body2" color="textSecondary">
          Hẹn giờ tự động bật/tắt thiết bị theo lịch.
        </Typography>
      </Box>

      {error && <Alert severity="error" onClose={() => setError("")} sx={{ mb: 3 }}>{error}</Alert>}
      {success && <Alert severity="success" onClose={() => setSuccess("")} sx={{ mb: 3 }}>{success}</Alert>}

      <Grid container spacing={4}>
        {/* Cột Trái: Form */}
        <Grid xs={12} md={5}>
          <Card sx={{ border: `1px solid ${editId ? theme.palette.primary.main : theme.palette.divider}`, boxShadow: editId ? '0 0 0 2px rgba(25, 118, 210, 0.2)' : 'none', position: 'sticky', top: 20, transition: '0.3s' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle1" fontWeight="bold" mb={3} color="primary">
                {editId ? "CHỈNH SỬA LỊCH" : "THIẾT LẬP LỊCH"}
              </Typography>
              
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {/* Thiết bị */}
                <TextField
                  select
                  fullWidth
                  label="Thiết bị"
                  value={form.device_id}
                  onChange={(e) => setForm({ ...form, device_id: e.target.value })}
                  size="small"
                >
                  <MenuItem value=""><em>-- Chọn thiết bị --</em></MenuItem>
                  {devices.map((d) => {
                    const Icon = deviceIcon[d.type] || MdLightbulb;
                    return (
                      <MenuItem key={d.id} value={d.id}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Icon size={18} />
                          {d.name} ({roomLabel[d.room] || d.room})
                        </Box>
                      </MenuItem>
                    );
                  })}
                </TextField>

                {/* Hành động */}
                <Box>
                  <Typography variant="body2" color="textSecondary" mb={1} fontWeight="bold">Hành động:</Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button 
                      variant={form.actionMode === 1 ? "contained" : "outlined"} 
                      color="primary"
                      onClick={() => setForm({ ...form, actionMode: 1 })}
                      sx={{ flex: 1, fontWeight: 'bold' }}
                      disableElevation
                    >
                      BẬT
                    </Button>
                    <Button 
                      variant={form.actionMode === 0 ? "contained" : "outlined"} 
                      color="error"
                      onClick={() => setForm({ ...form, actionMode: 0 })}
                      sx={{ flex: 1, fontWeight: 'bold' }}
                      disableElevation
                    >
                      TẮT
                    </Button>
                    <Button 
                      variant={form.actionMode === 2 ? "contained" : "outlined"} 
                      color="info"
                      onClick={() => setForm({ ...form, actionMode: 2 })}
                      sx={{ flex: 1, fontWeight: 'bold', whiteSpace: 'nowrap' }}
                      disableElevation
                    >
                      BẬT & TẮT
                    </Button>
                  </Box>
                </Box>

                {/* Giờ Bật */}
                {(form.actionMode === 1 || form.actionMode === 2) && (
                  <Box sx={{ bgcolor: 'primary.50', p: 2, borderRadius: 2 }}>
                    <Typography variant="body2" color="primary.main" mb={2} fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <MdAccessTime /> Giờ Bật
                    </Typography>
                    <Grid container spacing={2} sx={{ pt: 1 }}>
                      <Grid xs={6}>
                        <TextField
                          fullWidth type="number" label="Giờ (0-23)"
                          inputProps={{ min: 0, max: 23 }}
                          value={form.onHour === "" ? "" : form.onHour}
                          onChange={(e) => {
                            let val = e.target.value;
                            if (val !== "") {
                              val = Math.max(0, Math.min(23, Number(val)));
                            }
                            setForm({ ...form, onHour: val });
                          }}
                          size="small" sx={{ bgcolor: '#fff' }}
                        />
                      </Grid>
                      <Grid xs={6}>
                        <TextField
                          fullWidth type="number" label="Phút (0-59)"
                          inputProps={{ min: 0, max: 59 }}
                          value={form.onMinute === "" ? "" : form.onMinute}
                          onChange={(e) => {
                            let val = e.target.value;
                            if (val !== "") {
                              val = Math.max(0, Math.min(59, Number(val)));
                            }
                            setForm({ ...form, onMinute: val });
                          }}
                          size="small" sx={{ bgcolor: '#fff' }}
                        />
                      </Grid>
                    </Grid>
                  </Box>
                )}

                {/* Giờ Tắt */}
                {(form.actionMode === 0 || form.actionMode === 2) && (
                  <Box sx={{ bgcolor: 'error.50', p: 2, borderRadius: 2 }}>
                    <Typography variant="body2" color="error.main" mb={2} fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <MdAccessTime /> Giờ Tắt
                    </Typography>
                    <Grid container spacing={2} sx={{ pt: 1 }}>
                      <Grid xs={6}>
                        <TextField
                          fullWidth type="number" label="Giờ (0-23)"
                          inputProps={{ min: 0, max: 23 }}
                          value={form.offHour === "" ? "" : form.offHour}
                          onChange={(e) => {
                            let val = e.target.value;
                            if (val !== "") {
                              val = Math.max(0, Math.min(23, Number(val)));
                            }
                            setForm({ ...form, offHour: val });
                          }}
                          size="small" sx={{ bgcolor: '#fff' }}
                        />
                      </Grid>
                      <Grid xs={6}>
                        <TextField
                          fullWidth type="number" label="Phút (0-59)"
                          inputProps={{ min: 0, max: 59 }}
                          value={form.offMinute === "" ? "" : form.offMinute}
                          onChange={(e) => {
                            let val = e.target.value;
                            if (val !== "") {
                              val = Math.max(0, Math.min(59, Number(val)));
                            }
                            setForm({ ...form, offMinute: val });
                          }}
                          size="small" sx={{ bgcolor: '#fff' }}
                        />
                      </Grid>
                    </Grid>
                  </Box>
                )}

                {/* Ngày lặp lại */}
                <Box>
                  <Typography variant="body2" color="textSecondary" mb={1} fontWeight="bold">Lặp lại các ngày:</Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {DAYS.map((day) => {
                      const isSelected = form.days.includes(day);
                      return (
                        <Button
                          key={day}
                          variant={isSelected ? "contained" : "outlined"}
                          color="primary"
                          disableElevation
                          onClick={() => {
                            const newDays = isSelected 
                              ? form.days.filter(d => d !== day) 
                              : [...form.days, day];
                            handleDaysChange(null, newDays);
                          }}
                          sx={{ minWidth: 42, p: 0.5, py: 1 }}
                        >
                          {DAY_LABEL[day]}
                        </Button>
                      );
                    })}
                  </Box>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
                  <Button onClick={handleReset} color="inherit">
                    Xoá Trắng
                  </Button>
                  <Button onClick={handleAdd} variant="contained" color="primary" disableElevation sx={{ fontWeight: 'bold' }}>
                    {editId ? "Cập nhật" : "Lưu lịch"}
                  </Button>
                </Box>

              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Cột Phải: Danh sách lịch */}
        <Grid xs={12} md={7}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {schedules.length === 0 && (
              <Typography color="textSecondary" align="center" sx={{ py: 8 }}>
                Chưa có lịch hẹn giờ nào. Thiết lập lịch ở bên trái để bắt đầu.
              </Typography>
            )}

            {schedules.map((s) => (
              <Card 
                key={s.id} 
                sx={{ border: `1px solid ${editId === s.id ? theme.palette.primary.main : theme.palette.divider}`,
                  boxShadow: 'none',
                  opacity: s.is_active ? 1 : 0.6,
                  transition: '0.2s',
                  bgcolor: s.is_active ? (editId === s.id ? 'primary.50' : 'background.paper') : 'action.hover',
                  cursor: 'pointer',
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: s.is_active ? 'action.hover' : 'action.selected'
                  }
                }}
                onClick={() => handleEdit(s)}
              >
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: 2, alignItems: 'center' }}>
                    {/* Giờ */}
                    <Box sx={{ gridColumn: { xs: 'span 3', sm: 'span 2' }, textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight="bold" color={s.is_active ? "textPrimary" : "textSecondary"}>
                        {String(s.hour).padStart(2, "0")}:{String(s.minute).padStart(2, "0")}
                      </Typography>
                    </Box>

                    {/* BẬT/TẮT */}
                    <Box sx={{ gridColumn: { xs: 'span 3', sm: 'span 2' }, textAlign: 'center' }}>
                      <Typography 
                        variant="caption" 
                        fontWeight="bold" 
                        sx={{ 
                          bgcolor: s.action === 1 ? 'primary.light' : 'error.light',
                          color: s.action === 1 ? 'primary.main' : 'error.main',
                          px: 1.5, py: 0.5, borderRadius: 1, display: 'inline-block'
                        }}
                      >
                        {s.action === 1 ? "BẬT" : "TẮT"}
                      </Typography>
                    </Box>

                    {/* Info thiết bị */}
                    <Box sx={{ gridColumn: { xs: 'span 12', sm: 'span 5' } }}>
                      <Typography variant="subtitle2" fontWeight="bold" color="textPrimary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {getDeviceIcon(s.device_id)} {getDeviceName(s.device_id)}
                      </Typography>
                      <Typography variant="caption" color="textSecondary" display="block" mb={0.5}>
                        {getDeviceRoom(s.device_id)}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {DAYS.map((day) => (
                          <Typography 
                            key={day} 
                            variant="caption" 
                            sx={{ 
                              px: 0.8, py: 0.2, 
                              bgcolor: s.days.includes(day) ? 'primary.main' : 'transparent',
                              color: s.days.includes(day) ? 'primary.contrastText' : 'text.disabled',
                              borderRadius: 1,
                              fontSize: '0.65rem',
                              fontWeight: s.days.includes(day) ? 'bold' : 'normal'
                            }}
                          >
                            {DAY_LABEL[day]}
                          </Typography>
                        ))}
                      </Box>
                    </Box>

                    {/* Actions */}
                    <Box sx={{ gridColumn: { xs: 'span 12', sm: 'span 3' } }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: { xs: 'flex-start', sm: 'flex-end' }, gap: 1 }}>
                        <Switch 
                          checked={s.is_active} 
                          onChange={(e) => { e.stopPropagation(); handleToggle(s.id); }} 
                          color="primary"
                        />
                        <IconButton onClick={(e) => { e.stopPropagation(); handleDelete(s.id); }} color="error" sx={{ borderRadius: 1 }}>
                          <MdDelete />
                        </IconButton>
                      </Box>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Schedule;