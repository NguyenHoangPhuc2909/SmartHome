import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MdHome, MdLock, MdPerson, MdArrowForward } from "react-icons/md";
import useStore from "../store";

function Login() {
  const { user, login, register } = useStore();
  const navigate = useNavigate();

  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Nếu đã đăng nhập thì redirect về dashboard
  useEffect(() => {
    if (user) navigate("/dashboard");
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isRegister) {
        await register(username, password, name);
        // Sau khi đăng ký thành công thì tự động login luôn hoặc chuyển sang tab login
        await login(username, password);
      } else {
        await login(username, password);
      }
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.error || "Đã xảy ra lỗi, vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

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

      {/* Glow effects */}
      <div className="fixed pointer-events-none" style={{
        width: 600, height: 600, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(184,245,80,0.06) 0%, transparent 70%)",
        top: -200, right: -100,
      }} />
      <div className="fixed pointer-events-none" style={{
        width: 400, height: 400, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(2,132,199,0.05) 0%, transparent 70%)",
        bottom: -100, left: -100,
      }} />

      {/* Card */}
      <div className="relative z-10 w-full max-w-md mx-4 rounded-sm animate-fade-in"
           style={{
             background: "var(--surface)",
             border: "1px solid rgba(255,255,255,0.07)",
             padding: "48px 40px",
             boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)"
           }}>

        {/* Badge */}
        <div className="inline-block mb-6 px-3 py-1 rounded-sm text-xs tracking-widest uppercase"
             style={{
               fontFamily: "monospace",
               color: "var(--accent)",
               background: "rgba(184,245,80,0.1)",
               border: "1px solid rgba(184,245,80,0.25)",
             }}>
          {isRegister ? "User Registration" : "System Access"}
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
          {isRegister 
            ? "Tạo tài khoản mới để bắt đầu quản lý ngôi nhà của bạn." 
            : "Đăng nhập bằng tài khoản nội bộ để tiếp tục."}
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div className="relative">
              <MdPerson className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted)" }} />
              <input
                type="text"
                placeholder="Họ và tên"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full py-3 pl-10 pr-4 rounded-sm text-sm outline-none transition-all"
                style={{
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.07)",
                  color: "var(--text)",
                }}
              />
            </div>
          )}

          <div className="relative">
            <MdPerson className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted)" }} />
            <input
              type="text"
              required
              placeholder="Tên đăng nhập"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full py-3 pl-10 pr-4 rounded-sm text-sm outline-none transition-all focus:border-accent"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                color: "var(--text)",
              }}
            />
          </div>

          <div className="relative">
            <MdLock className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted)" }} />
            <input
              type="password"
              required
              placeholder="Mật khẩu"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full py-3 pl-10 pr-4 rounded-sm text-sm outline-none transition-all focus:border-accent"
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                color: "var(--text)",
              }}
            />
          </div>

          {error && (
            <p className="text-xs text-red-400 font-medium" style={{ fontFamily: "monospace" }}>
              ⚠️ {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex items-center justify-center gap-2 w-full py-3 px-5 rounded-sm font-bold text-xs tracking-widest uppercase transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50"
            style={{
              background: "var(--accent)",
              color: "#0d0f0f",
              border: "none",
            }}
          >
            {loading ? "Processing..." : isRegister ? "Tạo tài khoản" : "Đăng nhập"}
            {!loading && <MdArrowForward size={16} />}
          </button>
        </form>

        <div className="mt-8 pt-6 text-center" style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
          <button
            onClick={() => {
              setIsRegister(!isRegister);
              setError("");
            }}
            className="text-xs transition-all hover:opacity-80"
            style={{ color: "var(--muted)", background: "transparent", border: "none", cursor: "pointer", fontFamily: "monospace" }}
          >
            {isRegister ? "Đã có tài khoản? Đăng nhập ngay" : "Chưa có tài khoản? Đăng ký tại đây"}
          </button>
        </div>

        <p className="mt-6 text-center text-[10px] uppercase tracking-[0.2em]" style={{ color: "var(--muted)", opacity: 0.5, fontFamily: "monospace" }}>
          Local Network Access Only
        </p>
      </div>
    </div>
  );
}

export default Login;