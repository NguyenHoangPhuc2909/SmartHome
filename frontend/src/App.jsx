import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import useStore from "./store";

import Login    from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Dataset  from "./pages/Dataset";
import Schedule from "./pages/Schedule";
import Access   from "./pages/Access";
import Sensors  from "./pages/Sensors";
import Layout   from "./components/Layout";

function PrivateRoute({ children }) {
  const user = useStore((s) => s.user);
  if (user === null) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const fetchUser = useStore((s) => s.fetchUser);

  useEffect(() => {
    fetchUser();
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/dataset"   element={<Dataset />} />
        <Route path="/schedule"  element={<Schedule />} />
        <Route path="/access"    element={<Access />} />
        <Route path="/sensors"   element={<Sensors />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}