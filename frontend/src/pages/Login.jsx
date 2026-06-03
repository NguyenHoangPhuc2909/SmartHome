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
    <Box sx={{ 
      minHeight: '100vh', 
      bgcolor: 'background.default', 
      display: 'flex', 
      alignItems: 'center', 
      pt: { xs: 4, md: 0 },
      pb: { xs: 4, md: 0 } 
    }}>
      <Container maxWidth="sm" sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {/* Phần Logo và Slogan */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mb: 1 }}>
            <MdHome size={56} style={{ color: '#1877F2' }} />
            <Typography 
              variant="h3" 
              fontWeight="bold" 
              color="primary" 
              sx={{ ml: 1, letterSpacing: '-1px' }}
            >
              SmartHome
            </Typography>
          </Box>
          <Typography variant="h6" sx={{ lineHeight: 1.4, color: 'text.primary', fontWeight: 400 }}>
            SmartHome giúp bạn kết nối và quản lý mọi thiết bị.
          </Typography>
        </Box>

        {/* Phần Form Đăng nhập */}
        <Box sx={{ width: '100%', maxWidth: 400 }}>
          <Card sx={{ 
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            border: 'none' }}>
            <CardContent sx={{ p: { xs: 2.5, sm: 3 }, '&:last-child': { pb: 3 } }}>
              <form onSubmit={handleLoginSubmit}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    fullWidth
                    required
                    placeholder="Tên đăng nhập"
                    variant="outlined"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                  <TextField
                    fullWidth
                    required
                    type="password"
                    placeholder="Mật khẩu"
                    variant="outlined"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  
                  {loginError && (
                    <Typography variant="body2" color="error" align="center">
                      {loginError}
                    </Typography>
                  )}

                  <Button 
                    type="submit" 
                    variant="contained" 
                    color="primary" 
                    size="large"
                    disabled={loginLoading}
                    fullWidth
                    sx={{ py: 1.2, fontSize: '1.1rem', fontWeight: 'bold' }}
                  >
                    {loginLoading ? "Đang đăng nhập..." : "Đăng nhập"}
                  </Button>

                  <Typography variant="body2" color="primary" align="center" sx={{ cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}>
                    Quên mật khẩu?
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                    <Button 
                      variant="contained" 
                      color="secondary" 
                      size="large"
                      onClick={() => setOpenRegister(true)}
                      sx={{ 
                        py: 1.2, 
                        px: 4,
                        fontWeight: 'bold', 
                        fontSize: '1rem',
                        color: '#fff',
                        textTransform: 'none'
                      }}
                    >
                      Tạo tài khoản mới
                    </Button>
                  </Box>
                </Box>
              </form>
            </CardContent>
          </Card>
          <Typography variant="caption" display="block" align="center" color="textSecondary" sx={{ mt: 3 }}>
            <b>SmartHome</b> dành riêng cho hệ thống mạng nội bộ.
          </Typography>
        </Box>
      </Container>

      {/* Modal Đăng Ký */}
      <Dialog 
        open={openRegister} 
        onClose={closeRegisterModal}
        maxWidth="xs"
        fullWidth
        PaperProps={{ sx: {  } }}
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
            color="secondary" 
            disabled={regLoading}
            sx={{ 
              width: '50%', 
              fontWeight: 'bold', 
              fontSize: '1rem', 
              color: '#fff',
              textTransform: 'none'
            }}
          >
            {regLoading ? "Đang xử lý..." : "Đăng ký"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Login;