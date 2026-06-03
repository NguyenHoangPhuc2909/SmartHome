import { useState } from 'react';
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
} from '@mui/icons-material';
import useStore from '../store';

const drawerWidth = 260;

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
  const [anchorEl, setAnchorEl] = useState(null);
  const [notiAnchorEl, setNotiAnchorEl] = useState(null);
  const [lastReadId, setLastReadId] = useState(null);

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
      setLastReadId(activeAlerts[0].id);
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
    <div>
      <Toolbar sx={{ display: 'flex', alignItems: 'center', gap: 2, px: 2 }}>
        <Avatar sx={{ bgcolor: theme.palette.primary.main, width: 32, height: 32 }}>
          <DashboardIcon sx={{ fontSize: 20 }} />
        </Avatar>
        <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold', color: theme.palette.primary.main }}>
          SmartHome
        </Typography>
      </Toolbar>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Typography variant="overline" color="textSecondary" sx={{ ml: 2, fontWeight: 'bold' }}>
          Điều hướng
        </Typography>
        <List>
          {menuItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <ListItem key={item.text} disablePadding sx={{ px: 1.5, mb: 0.5 }}>
                <ListItemButton
                  selected={isActive}
                  onClick={() => handleNavigation(item.path)}
                  sx={{
                    borderRadius: '8px',
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
                  <ListItemIcon sx={{ minWidth: 40, color: isActive ? theme.palette.primary.main : 'text.secondary' }}>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText 
                    primary={item.text} 
                    primaryTypographyProps={{ 
                      fontWeight: isActive ? 600 : 500,
                      fontSize: '0.9rem'
                    }} 
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>
    </div>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Top App Bar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          bgcolor: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(10px)',
          borderBottom: 'none',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          color: 'text.primary',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          
          <Box sx={{ flexGrow: 1 }} />
          
          {/* Notifications */}
          <IconButton onClick={handleNotiOpen} sx={{ mr: 2 }}>
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

          {/* User Profile */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" color="textSecondary" sx={{ display: { xs: 'none', sm: 'block' } }}>
              {user?.name || 'Admin'}
            </Typography>
            <IconButton onClick={handleMenuOpen} size="small">
              <Avatar sx={{ width: 32, height: 32, bgcolor: theme.palette.primary.main }}>
                {user?.name?.charAt(0) || 'A'}
              </Avatar>
            </IconButton>
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleMenuClose}
              transformOrigin={{ horizontal: 'right', vertical: 'top' }}
              anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
              <MenuItem onClick={handleLogout}>
                <ListItemIcon>
                  <LogoutIcon fontSize="small" />
                </ListItemIcon>
                Đăng xuất
              </MenuItem>
            </Menu>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Sidebar Navigation */}
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
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
              width: drawerWidth,
              borderRight: 'none',
              boxShadow: '2px 0 12px rgba(0,0,0,0.05)'
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
        sx={{ flexGrow: 1, p: 3, width: { sm: `calc(100% - ${drawerWidth}px)` }, mt: '64px' }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}

export default Layout;
