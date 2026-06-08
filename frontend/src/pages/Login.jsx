import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MdHome } from "react-icons/md";
import useStore from "../store";
import { 
  Box, 
  Container, 
  Grid, 
  Typography, 
  Card, 
  CardContent, 
  TextField, 
  Button, 
  Divider, 
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Alert
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import HomeImage from '../assets/home.jpg';

function Login() {
  const { user, login, register } = useStore();
  const navigate = useNavigate();

  // Login state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  // Register state (Modal)
  const [openRegister, setOpenRegister] = useState(false);
  const [regName, setRegName] = useState("");
  const [regUsername, setRegUsername] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regError, setRegError] = useState("");
  const [regLoading, setRegLoading] = useState(false);

  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user, navigate]);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setLoginError("");
    setLoginLoading(true);

    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      setLoginError(err.response?.data?.error || "Sai tên đăng nhập hoặc mật khẩu.");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setRegError("");
    setRegLoading(true);

    try {
      await register(regUsername, regPassword, regName);
      await login(regUsername, regPassword);
      setOpenRegister(false);
      navigate("/dashboard");
    } catch (err) {
      setRegError(err.response?.data?.error || "Đăng ký thất bại, vui lòng thử lại.");
    } finally {
      setRegLoading(false);
    }
  };

  const closeRegisterModal = () => {
    if (regLoading) return;
    setOpenRegister(false);
    setRegError("");
    setRegName("");
    setRegUsername("");
    setRegPassword("");
  };

  return (
    <>
      <Grid container component="main" sx={{ height: '100vh' }}>
      {/* Phần bên trái: Form */}
      <Grid 
        size={{ xs: 12, md: 6 }}
        sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center', 
          p: 4, 
          bgcolor: '#fbfbfb' 
        }}
      >
        <Box sx={{ width: '100%', maxWidth: 400 }}>
          <Typography variant="h4" fontWeight="500" sx={{ mb: 1, color: '#333' }}>
            Đăng nhập
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 4 }}>
            SmartHome giúp bạn kết nối và quản lý mọi thiết bị.
          </Typography>

          <form onSubmit={handleLoginSubmit}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
              <Box>
                <Typography variant="body2" fontWeight="500" sx={{ mb: 0.5, color: '#555' }}>
                  Tên đăng nhập
                </Typography>
                <TextField
                  fullWidth
                  required
                  placeholder="Nhập tên đăng nhập"
                  variant="outlined"
                  size="small"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  sx={{ bgcolor: '#fff', '& .MuiOutlinedInput-root': { borderRadius: 1 } }}
                />
              </Box>
              <Box>
                <Typography variant="body2" fontWeight="500" sx={{ mb: 0.5, color: '#555' }}>
                  Mật khẩu
                </Typography>
                <TextField
                  fullWidth
                  required
                  type="password"
                  placeholder="Nhập mật khẩu"
                  variant="outlined"
                  size="small"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  sx={{ bgcolor: '#fff', '& .MuiOutlinedInput-root': { borderRadius: 1 } }}
                />
              </Box>

              {loginError && (
                <Typography variant="body2" color="error" align="center">
                  {loginError}
                </Typography>
              )}

              <Button 
                type="submit" 
                variant="contained" 
                color="primary"
                disabled={loginLoading}
                fullWidth
                disableElevation
                sx={{ 
                  py: 1.2, 
                  fontWeight: 'bold',
                  textTransform: 'none',
                  borderRadius: 1
                }}
              >
                {loginLoading ? "Đang đăng nhập..." : "Đăng nhập"}
              </Button>

              <Button 
                variant="outlined"
                color="primary"
                onClick={() => setOpenRegister(true)}
                fullWidth
                sx={{ 
                  py: 1, 
                  fontWeight: 'bold',
                  textTransform: 'none',
                  borderRadius: 1
                }}
              >
                Tạo tài khoản mới
              </Button>
            </Box>
          </form>
        </Box>
      </Grid>

      {/* Phần bên phải: Hình ảnh */}
      <Grid 
        size={{ xs: 12, md: 6 }}
        sx={{ 
          display: { xs: 'none', md: 'block' },
          backgroundImage: `url(${HomeImage})`,
          backgroundRepeat: 'no-repeat',
          backgroundColor: (t) => t.palette.mode === 'light' ? t.palette.grey[50] : t.palette.grey[900],
          backgroundSize: 'contain',
          backgroundPosition: 'center',
        }} 
      />
    </Grid>

      {/* Modal Đăng Ký */}
      <Dialog 
        open={openRegister} 
        onClose={closeRegisterModal}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Typography variant="h5" fontWeight="bold">Đăng ký</Typography>
            <Typography variant="body2" color="textSecondary">Nhanh chóng và dễ dàng.</Typography>
          </Box>
          <IconButton onClick={closeRegisterModal} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <Divider />
        <DialogContent>
          <form id="register-form" onSubmit={handleRegisterSubmit}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                fullWidth
                required
                placeholder="Họ và tên"
                variant="outlined"
                size="small"
                value={regName}
                onChange={(e) => setRegName(e.target.value)}
              />
              <TextField
                fullWidth
                required
                placeholder="Tên đăng nhập"
                variant="outlined"
                size="small"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
              />
              <TextField
                fullWidth
                required
                type="password"
                placeholder="Mật khẩu mới"
                variant="outlined"
                size="small"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
              />
              {regError && (
                <Alert severity="error" sx={{ mt: 1 }}>{regError}</Alert>
              )}
            </Box>
          </form>
        </DialogContent>
        <DialogActions sx={{ justifyContent: 'center', pb: 3, pt: 1 }}>
          <Button 
            type="submit" 
            form="register-form"
            variant="contained" 
            color="primary" 
            disabled={regLoading}
            sx={{ 
              width: '50%', 
              fontWeight: 'bold', 
              fontSize: '1rem', 
              textTransform: 'none'
            }}
          >
            {regLoading ? "Đang xử lý..." : "Đăng ký"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default Login;