import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import useStore from "./store";

import Login    from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Dataset  from "./pages/Dataset";
import Schedule from "./pages/Schedule";
import Access   from "./pages/Access";
import Navbar   from "./components/Navbar";

function PrivateRoute({ children }) {
  const user = useStore((s) => s.user);
  if (user === null) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const fetchUser = useStore((s) => s.fetchUser);
  const user      = useStore((s) => s.user);

  useEffect(() => {
    fetchUser();
  }, []);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      {user && <Navbar />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/dataset"   element={<PrivateRoute><Dataset /></PrivateRoute>} />
        <Route path="/schedule"  element={<PrivateRoute><Schedule /></PrivateRoute>} />
        <Route path="/access"    element={<PrivateRoute><Access /></PrivateRoute>} />
        <Route path="*"          element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </div>
  );
}