import { useEffect, useState } from "react";
import { MdAdd, MdDelete } from "react-icons/md";
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

const defaultForm = {
  device_id: "",
  action:    1,
  hour:      18,
  minute:    0,
  days:      ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
  is_active: true,
};

function Schedule() {
  const theme = useTheme();
  const { schedules, devices, fetchSchedules, fetchDevices } = useStore();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(defaultForm);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSchedules();
    fetchDevices();
  }, []);

  const handleDaysChange = (event, newDays) => {
    setForm({ ...form, days: newDays });
  };

  const handleAdd = async () => {
    if (!form.device_id) return setError("Vui lòng chọn thiết bị");
    if (form.days.length === 0) return setError("Vui lòng chọn ít nhất 1 ngày");
    try {
      await api.post("/api/schedules/", {
        ...form,
        days: form.days.join(","),
      });
      setShowForm(false);
      setForm(defaultForm);
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

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Lịch trình</Typography>
          <Typography variant="body2" color="textSecondary">
            Hẹn giờ tự động bật/tắt thiết bị theo lịch.
          </Typography>
        </Box>
        <Button 
          variant="contained" 
          color="primary" 
          startIcon={<MdAdd />}
          onClick={() => setShowForm(!showForm)}
          disableElevation
          sx={{ fontWeight: 'bold' }}
        >
          Thêm lịch
        </Button>
      </Box>

      {/* Error Banner */}
      {error && (
        <Alert severity="error" onClose={() => setError("")} sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Add Form */}
      {showForm && (
        <Card sx={{ mb: 4,  border: `1px solid ${theme.palette.divider}`, boxShadow: 'none' }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight="bold" mb={3} color="primary">THÊM LỊCH MỚI</Typography>
            
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 3, mb: 3 }}>
              {/* Thiết bị */}
              <Box>
                <TextField
                  select
                  fullWidth
                  label="Thiết bị"
                  value={form.device_id}
                  onChange={(e) => setForm({ ...form, device_id: e.target.value })}
                  size="small"
                >
                  <MenuItem value=""><em>-- Chọn thiết bị --</em></MenuItem>
                  {devices.map((d) => (
                    <MenuItem key={d.id} value={d.id}>
                      {d.name} ({roomLabel[d.room] || d.room})
                    </MenuItem>
                  ))}
                </TextField>
              </Box>

              {/* Hành động */}
              <Box>
                <Box sx={{ display: 'flex', gap: 1, height: '40px' }}>
                  <Button 
                    variant={form.action === 1 ? "contained" : "outlined"} 
                    color="primary"
                    onClick={() => setForm({ ...form, action: 1 })}
                    sx={{ flex: 1,  fontWeight: 'bold' }}
                    disableElevation
                  >
                    BẬT
                  </Button>
                  <Button 
                    variant={form.action === 0 ? "contained" : "outlined"} 
                    color="error"
                    onClick={() => setForm({ ...form, action: 0 })}
                    sx={{ flex: 1,  fontWeight: 'bold' }}
                    disableElevation
                  >
                    TẮT
                  </Button>
                </Box>
              </Box>

              {/* Giờ */}
              <Box>
                <TextField
                  fullWidth
                  type="number"
                  label="Giờ (0-23)"
                  InputProps={{ inputProps: { min: 0, max: 23 } }}
                  value={form.hour}
                  onChange={(e) => setForm({ ...form, hour: Number(e.target.value) })}
                  size="small"
                />
              </Box>

              {/* Phút */}
              <Box>
                <TextField
                  fullWidth
                  type="number"
                  label="Phút (0-59)"
                  InputProps={{ inputProps: { min: 0, max: 59 } }}
                  value={form.minute}
                  onChange={(e) => setForm({ ...form, minute: Number(e.target.value) })}
                  size="small"
                />
              </Box>
            </Box>

            {/* Ngày lặp lại */}
            <Typography variant="body2" color="textSecondary" mb={1} fontWeight="bold">Lặp lại các ngày:</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 4 }}>
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
                    sx={{ minWidth: 48, p: 1 }}
                  >
                    {DAY_LABEL[day]}
                  </Button>
                );
              })}
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
              <Button onClick={() => { setShowForm(false); setError(""); }} color="inherit">
                Hủy bỏ
              </Button>
              <Button onClick={handleAdd} variant="contained" color="primary" disableElevation sx={{ fontWeight: 'bold' }}>
                Lưu lịch
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Danh sách lịch */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {schedules.length === 0 && (
          <Typography color="textSecondary" align="center" sx={{ py: 8 }}>
            Chưa có lịch hẹn giờ nào. Nhấn "Thêm lịch" để bắt đầu.
          </Typography>
        )}

        {schedules.map((s) => (
          <Card 
            key={s.id} 
            sx={{ border: `1px solid ${theme.palette.divider}`,
              boxShadow: 'none',
              opacity: s.is_active ? 1 : 0.6,
              transition: '0.3s',
              bgcolor: s.is_active ? 'background.paper' : 'action.hover'
            }}
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
                  <Typography variant="subtitle2" fontWeight="bold" color="textPrimary">
                    {getDeviceName(s.device_id)}
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
                      onChange={() => handleToggle(s.id)} 
                      color="primary"
                    />
                    <IconButton onClick={() => handleDelete(s.id)} color="error" sx={{ borderRadius: 1 }}>
                      <MdDelete />
                    </IconButton>
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

    </Box>
  );
}

export default Schedule;