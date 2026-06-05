import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  Menu,
  MenuItem,
  useTheme,
  Badge,
  Popover,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Science as DatasetIcon,
  Schedule as ScheduleIcon,
  Security as AccessIcon,
  ExitToApp as LogoutIcon,
  Sensors as SensorsIcon,
  Notifications as NotificationsIcon,
  ChevronLeft as ChevronLeftIcon,
  MenuOpen as MenuOpenIcon,
} from '@mui/icons-material';
import useStore from '../store';

const drawerWidth = 260;
const collapsedDrawerWidth = 84;

const menuItems = [
  { text: 'Tổng quan', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Cảm biến', icon: <SensorsIcon />, path: '/sensors' },
  { text: 'Dữ liệu khuôn mặt', icon: <DatasetIcon />, path: '/dataset' },
  { text: 'Lịch trình', icon: <ScheduleIcon />, path: '/schedule' },
  { text: 'Truy cập', icon: <AccessIcon />, path: '/access' },
];

function Layout() {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const user = useStore((s) => s.user);
  const logout = useStore((s) => s.logout);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const [notiAnchorEl, setNotiAnchorEl] = useState(null);
  const [lastReadId, setLastReadId] = useState(() => {
    const saved = localStorage.getItem('lastReadAlertId');
    return saved ? parseInt(saved, 10) : null;
  });
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const accessLogs = useStore((s) => s.accessLogs || []);
  const activeAlerts = accessLogs
    .filter(log => log.is_alert && log.result === "DENIED")
    .slice(0, 10); // Lấy tối đa 10 cái gần nhất

  // Tính số lượng thông báo chưa đọc
  let unreadCount = 0;
  for (let log of activeAlerts) {
    if (log.id === lastReadId) break;
    unreadCount++;
  }

  const getGreeting = () => {
    const hour = currentTime.getHours();
    if (hour >= 5 && hour < 12) return 'Chào buổi sáng';
    if (hour >= 12 && hour < 18) return 'Chào buổi chiều';
    if (hour >= 18 && hour < 22) return 'Chào buổi tối';
    return 'Chúc ngủ ngon';
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleNotiOpen = (event) => {
    setNotiAnchorEl(event.currentTarget);
    // Khi bấm vào chuông, đánh dấu là đã xem thông báo mới nhất -> số đếm về 0
    if (activeAlerts.length > 0) {
      const topId = activeAlerts[0].id;
      setLastReadId(topId);
      localStorage.setItem('lastReadAlertId', topId);
    }
  };

  const handleNotiClose = () => {
    setNotiAnchorEl(null);
  };

  const handleLogout = async () => {
    handleMenuClose();
    await logout();
    navigate('/login');
  };

  const handleNavigation = (path) => {
    navigate(path);
    setMobileOpen(false);
  };

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflowX: 'hidden' }}>
      <Box>
        <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', px: isCollapsed ? 1 : 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                bgcolor: 'success.main', color: 'white',
                width: 36, height: 36, borderRadius: '10px',
                boxShadow: '0 4px 10px rgba(16, 185, 129, 0.3)'
              }}
            >
              <DashboardIcon sx={{ fontSize: 22 }} />
            </Box>
            {!isCollapsed && (
              <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>
                SmartHome
              </Typography>
            )}
          </Box>
        </Toolbar>
        <Divider />
      </Box>

      <Box sx={{ p: isCollapsed ? 1 : 2, flexGrow: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {!isCollapsed && (
          <Typography variant="overline" color="textSecondary" sx={{ ml: 2, fontWeight: 'bold' }}>
            Điều hướng
          </Typography>
        )}
        <List sx={{ mt: isCollapsed ? 2 : 0 }}>
          {menuItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <ListItem key={item.text} disablePadding sx={{ px: isCollapsed ? 0 : 1.5, mb: 1, justifyContent: 'center' }}>
                <ListItemButton
                  selected={isActive}
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '8px',
                    minHeight: 48,
                    justifyContent: isCollapsed ? 'center' : 'initial',
                    px: 2.5,
                    '&.Mui-selected': {
                      backgroundColor: `${theme.palette.primary.main}15`,
                      color: theme.palette.primary.main,
                      '& .MuiListItemIcon-root': {
                        color: theme.palette.primary.main,
                      },
                      '&:hover': {
                        backgroundColor: `${theme.palette.primary.main}25`,
                      }
                    },
                  }}
                >
                  <ListItemIcon sx={{
                    minWidth: 0,
                    mr: isCollapsed ? 0 : 2,
                    justifyContent: 'center',
                    color: isActive ? theme.palette.primary.main : 'text.secondary'
                  }}>
                    {item.icon}
                  </ListItemIcon>
                  {!isCollapsed && (
                    <ListItemText
                      primary={item.text}
                      primaryTypographyProps={{
                        fontWeight: isActive ? 600 : 500,
                        fontSize: '0.9rem'
                      }}
                    />
                  )}
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* User Profile at Bottom */}
      <Box sx={{ p: isCollapsed ? 1 : 2, pb: 2 }}>
        <Box
          onClick={(e) => {
            if (isCollapsed) handleMenuOpen(e);
          }}
          sx={{
            px: isCollapsed ? 1 : 1.5,
            py: isCollapsed ? 1 : 0.75,
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: isCollapsed ? 'center' : 'flex-start',
            gap: isCollapsed ? 0 : 1.25,
            borderRadius: isCollapsed ? '24px' : '50px',
            bgcolor: 'background.paper',
            border: `1px solid ${theme.palette.divider}`,
            boxShadow: '0 4px 15px rgba(0,0,0,0.03)',
            transition: 'all 0.3s ease',
            cursor: isCollapsed ? 'pointer' : 'default',
            '&:hover': isCollapsed ? { bgcolor: 'action.hover' } : {}
          }}
        >
          <Avatar sx={{ width: 34, height: 34, bgcolor: theme.palette.primary.main, fontWeight: 'bold', fontSize: '0.9rem' }}>
            {user?.name?.charAt(0) || 'N'}
          </Avatar>
          {!isCollapsed && (
            <>
              <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                <Typography variant="body2" fontWeight="bold" color="text.primary" noWrap>
                  {user?.name || 'Người dùng'}
                </Typography>
                <Typography variant="caption" color="textSecondary" noWrap sx={{ display: 'block', mt: -0.5, fontSize: '0.7rem' }}>
                  Người dùng
                </Typography>
              </Box>
              <IconButton size="small" onClick={handleLogout} sx={{ color: 'text.secondary', '&:hover': { color: 'error.main' }, mr: -0.5 }}>
                <LogoutIcon fontSize="1.1rem" />
              </IconButton>
            </>
          )}
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Top App Bar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${isCollapsed ? collapsedDrawerWidth : drawerWidth}px)` },
          ml: { sm: `${isCollapsed ? collapsedDrawerWidth : drawerWidth}px` },
          bgcolor: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(10px)',
          borderBottom: 'none',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          color: 'text.primary',
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
      >
        <Toolbar>
          {/* Mobile toggle */}
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          {/* Desktop collapse toggle */}
          <IconButton
            color="inherit"
            onClick={() => setIsCollapsed(!isCollapsed)}
            sx={{ mr: 2, display: { xs: 'none', sm: 'flex' }, color: 'text.secondary' }}
          >
            {isCollapsed ? <MenuIcon /> : <MenuOpenIcon />}
          </IconButton>

          <Typography variant="subtitle1" fontWeight="bold" sx={{ color: 'text.primary', display: { xs: 'none', sm: 'block' } }}>
            {getGreeting()}, {user?.name || 'bạn'}! ✌︎
          </Typography>

          <Box sx={{ flexGrow: 1 }} />

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* ── Realtime Clock ── */}
            <Box
            sx={{
              display: { xs: 'none', md: 'flex' },
              alignItems: 'center',
              gap: 1.5,
              px: 2.5, py: 0.75,
              borderRadius: '50px',
              bgcolor: 'background.paper',
              border: `1px solid ${theme.palette.divider}`,
              boxShadow: '0 4px 15px rgba(0,0,0,0.03)',
            }}
          >
            {/* Chấm xanh nhấp nháy báo Live */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Box sx={{ position: 'absolute', width: 10, height: 10, borderRadius: '50%', bgcolor: 'success.main', opacity: 0.4, animation: 'pulse 2s infinite' }} />
              <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: 'success.main' }} />
            </Box>

            <Typography
              variant="subtitle1"
              fontWeight="800"
              sx={{
                color: 'text.primary',
                letterSpacing: 2,
                fontFamily: 'monospace',
                lineHeight: 1
              }}
            >
              {currentTime.toLocaleTimeString('en-GB')}
            </Typography>

            <Box sx={{ width: '1px', height: '16px', bgcolor: 'divider' }} />

            <Typography
              variant="caption"
              fontWeight="600"
              sx={{ color: 'text.secondary', textTransform: 'uppercase', lineHeight: 1 }}
            >
              {currentTime.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' })}
            </Typography>
          </Box>

          {/* Notifications */}
          <IconButton onClick={handleNotiOpen}>
            <Badge badgeContent={unreadCount} color="error">
              <NotificationsIcon />
            </Badge>
          </IconButton>

          <Popover
            open={Boolean(notiAnchorEl)}
            anchorEl={notiAnchorEl}
            onClose={handleNotiClose}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
            PaperProps={{ sx: { width: 340, mt: 1.5, borderRadius: 2, boxShadow: 3 } }}
          >
            <Box sx={{ p: 2, borderBottom: '1px solid #eee' }}>
              <Typography variant="subtitle1" fontWeight="bold">Thông báo</Typography>
            </Box>
            <List sx={{ p: 0, maxHeight: 360, overflowY: 'auto' }}>
              {activeAlerts.length === 0 ? (
                <Typography variant="body2" color="textSecondary" sx={{ p: 3, textAlign: 'center' }}>
                  Không có thông báo mới
                </Typography>
              ) : (
                activeAlerts.map(log => (
                  <ListItemButton
                    key={log.id}
                    onClick={() => { handleNotiClose(); handleNavigation('/access'); }}
                    sx={{ borderBottom: '1px solid #f5f5f5', p: 2, whiteSpace: 'normal' }}
                  >
                    <Box>
                      <Typography variant="body2" color="error" fontWeight="bold" gutterBottom>
                        ⚠ Cảnh báo người lạ xâm nhập
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        Lúc: {new Date(log.timestamp).toLocaleString("vi-VN")}
                      </Typography>
                    </Box>
                  </ListItemButton>
                ))
              )}
            </List>
          </Popover>

          {/* User Profile (Top Right) */}
            <Avatar sx={{ width: 34, height: 34, bgcolor: theme.palette.primary.main, fontSize: '0.9rem', fontWeight: 'bold' }}>
              {user?.name?.charAt(0) || 'A'}
            </Avatar>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Sidebar Navigation */}
      <Box
        component="nav"
        sx={{
          width: { sm: isCollapsed ? collapsedDrawerWidth : drawerWidth },
          flexShrink: { sm: 0 },
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
        aria-label="mailbox folders"
      >
        {/* Mobile Drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }} // Better open performance on mobile.
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              borderRight: 'none',
              boxShadow: '2px 0 12px rgba(0,0,0,0.05)'
            },
          }}
        >
          {drawer}
        </Drawer>

        {/* Desktop Drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: isCollapsed ? collapsedDrawerWidth : drawerWidth,
              borderRight: 'none',
              boxShadow: '2px 0 12px rgba(0,0,0,0.05)',
              transition: theme.transitions.create('width', {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
              }),
              overflowX: 'hidden'
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content Area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${isCollapsed ? collapsedDrawerWidth : drawerWidth}px)` },
          mt: '64px',
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
      >
        <Outlet />
      </Box>

      {/* User Profile Menu (when collapsed) */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        transformOrigin={{ horizontal: 'left', vertical: 'bottom' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        slotProps={{
          paper: {
            sx: {
              mt: -1,
              borderRadius: '12px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
              border: `1px solid ${theme.palette.divider}`,
              minWidth: 150
            }
          }
        }}
      >
        <MenuItem onClick={handleLogout} sx={{ color: 'error.main', fontWeight: 'bold' }}>
          <LogoutIcon sx={{ mr: 1.5, fontSize: '1.2rem' }} /> Đăng xuất
        </MenuItem>
      </Menu>
    </Box>
  );
}

export default Layout;
