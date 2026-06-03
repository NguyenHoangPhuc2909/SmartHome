import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1877F2', // Facebook Blue
    },
    secondary: {
      main: '#42b72a', // Facebook Green (dùng cho nút Đăng ký mới)
    },
    background: {
      default: '#F0F2F5', // Facebook Gray BG
      paper: '#ffffff',
    },
    text: {
      primary: '#0f172a', // slate-900 (rất đậm, gần như đen)
      secondary: '#334155', // slate-700 (xám đậm hơn)
    },
    success: {
      main: '#10b981',
    },
    warning: {
      main: '#f59e0b',
    },
    error: {
      main: '#ef4444',
    },
    info: {
      main: '#3b82f6',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
    },
    h2: {
      fontWeight: 700,
    },
    h3: {
      fontWeight: 700,
    },
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
    button: {
      textTransform: 'none', // modern buttons don't uppercase all text
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 12, // Bo góc nhẹ nhàng (modern rounded corners)
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: 'none', // Tắt shadow để giao diện phẳng hơn nếu muốn, hoặc giữ shadow
          border: '1px solid #cbd5e1', // Viền đậm hơn (slate-300) để phân chia rõ ràng
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8, // Nút bấm bo góc nhẹ
        },
      },
    },
  },
});

export default theme;
