import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FcGoogle } from "react-icons/fc";
import { MdHome } from "react-icons/md";
import useStore from "../store";

function Login() {
  const user     = useStore((s) => s.user);
  const navigate = useNavigate();

  // Nếu đã đăng nhập thì redirect về dashboard
  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user]);

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
         style={{ background: "var(--bg)" }}>

      {/* Grid background */}
      <div className="fixed inset-0 pointer-events-none" style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: "40px 40px"
      }} />

      {/* Glow */}
      <div className="fixed pointer-events-none" style={{
        width: 600, height: 600, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(184,245,80,0.06) 0%, transparent 70%)",
        top: -200, right: -100,
      }} />

      {/* Card */}
      <div className="relative z-10 w-full max-w-md mx-4 rounded-sm animate-fade-in"
           style={{
             background: "var(--surface)",
             border: "1px solid rgba(255,255,255,0.07)",
             padding: "48px 44px",
           }}>

        {/* Badge */}
        <div className="inline-block mb-6 px-3 py-1 rounded-sm text-xs tracking-widest uppercase"
             style={{
               fontFamily: "var(--font-mono, monospace)",
               color: "var(--accent)",
               background: "rgba(184,245,80,0.1)",
               border: "1px solid rgba(184,245,80,0.25)",
             }}>
          System Access
        </div>

        {/* Title */}
        <div className="flex items-center gap-3 mb-2">
          <MdHome size={28} style={{ color: "var(--accent)" }} />
          <h1 className="text-2xl font-bold tracking-tight"
              style={{ fontFamily: "monospace", color: "var(--text)" }}>
            SmartHome
          </h1>
        </div>
        <p className="mb-8 text-sm" style={{ color: "var(--muted)" }}>
          Đăng nhập để quản lý thiết bị, cảm biến<br />và nhận diện khuôn mặt.
        </p>

        {/* Status row */}
        <div className="flex gap-3 mb-8">
          {[
            { label: "System", value: "ONLINE" },
            { label: "Auth",   value: "OAuth 2.0" },
            { label: "Mode",   value: "SECURE" },
          ].map((item) => (
            <div key={item.label} className="flex-1 rounded-sm p-3"
                 style={{
                   background: "rgba(255,255,255,0.03)",
                   border: "1px solid rgba(255,255,255,0.07)",
                 }}>
              <div className="text-xs mb-1 tracking-widest uppercase"
                   style={{ fontFamily: "monospace", color: "var(--muted)" }}>
                {item.label}
              </div>
              <div className="text-xs font-bold"
                   style={{ fontFamily: "monospace", color: "var(--accent)" }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>

        {/* Divider */}
        <div className="mb-6" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }} />

        {/* Google login button */}
        <a href="http://localhost:5000/login/google"
           className="flex items-center justify-center gap-3 w-full py-3 px-5 rounded-sm font-medium text-sm transition-all hover:opacity-85 active:scale-95"
           style={{
             background: "var(--text)",
             color: "#0d0f0f",
             textDecoration: "none",
           }}>
          <FcGoogle size={20} />
          Đăng nhập với Google
        </a>

        <p className="mt-6 text-center text-xs" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
          Chỉ dành cho thành viên trong gia đình
        </p>
      </div>
    </div>
  );
}

export default Login;