import { NavLink, useNavigate } from "react-router-dom";
import { MdHome, MdFaceRetouchingNatural, MdSchedule, MdLock } from "react-icons/md";
import useStore from "../store";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: MdHome },
  { to: "/dataset",   label: "Dataset",   icon: MdFaceRetouchingNatural },
  { to: "/schedule",  label: "Schedule",  icon: MdSchedule },
  { to: "/access",    label: "Access",    icon: MdLock },
];

function Navbar() {
  const user     = useStore((s) => s.user);
  const navigate = useNavigate();

  const handleLogout = () => {
    window.location.href = "http://localhost:5000/auth/logout";
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-14"
         style={{
           background: "rgba(20,23,24,0.85)",
           borderBottom: "1px solid rgba(255,255,255,0.07)",
           backdropFilter: "blur(12px)",
         }}>

      {/* Logo */}
      <div className="flex items-center gap-2">
        <MdHome size={20} style={{ color: "var(--accent)" }} />
        <span className="text-sm font-bold tracking-widest uppercase"
              style={{ fontFamily: "monospace", color: "var(--text)" }}>
          SmartHome
        </span>
      </div>

      {/* Nav links */}
      <div className="flex items-center gap-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to}
            className="flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs tracking-wide transition-all"
            style={({ isActive }) => ({
              fontFamily: "monospace",
              color:      isActive ? "var(--accent)" : "var(--muted)",
              background: isActive ? "rgba(184,245,80,0.08)" : "transparent",
              border:     isActive ? "1px solid rgba(184,245,80,0.2)" : "1px solid transparent",
            })}>
            <Icon size={14} />
            {label}
          </NavLink>
        ))}
      </div>

      {/* User + logout */}
      <div className="flex items-center gap-3">
        {user?.avatar && (
          <img src={user.avatar} alt={user.name}
               className="w-7 h-7 rounded-full"
               style={{ border: "1px solid rgba(255,255,255,0.1)" }} />
        )}
        <span className="text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
          {user?.name}
        </span>
        <button onClick={handleLogout}
                className="text-xs px-3 py-1.5 rounded-sm transition-all hover:opacity-80"
                style={{
                  fontFamily: "monospace",
                  color:      "var(--muted)",
                  border:     "1px solid rgba(255,255,255,0.07)",
                  background: "transparent",
                }}>
          Logout
        </button>
      </div>
    </nav>
  );
}

export default Navbar;