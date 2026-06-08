import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { io } from "socket.io-client";
import useStore from "./store";

import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Dataset from "./pages/Dataset";
import Schedule from "./pages/Schedule";
import Access from "./pages/Access";
import Sensors from "./pages/Sensors";
import Layout from "./components/Layout";

function PrivateRoute({ children }) {
  const user = useStore((s) => s.user);
  if (user === null) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const fetchUser = useStore((s) => s.fetchUser);
  const fetchDevices = useStore((s) => s.fetchDevices);
  const fetchAccessLogs = useStore((s) => s.fetchAccessLogs);

  useEffect(() => {
    fetchUser();

    // WebSocket connection directly to backend
    const socket = io("http://localhost:5000");

    socket.on("connect", () => {
      console.log("Socket.IO Connected to Backend!");
    });

    socket.on("refresh_devices", () => {
      console.log("Socket.IO Received: refresh_devices => Fetching new data...");
      fetchDevices();
    });

    socket.on("refresh_access_logs", () => {
      fetchAccessLogs();
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/dataset" element={<Dataset />} />
        <Route path="/schedule" element={<Schedule />} />
        <Route path="/access" element={<Access />} />
        <Route path="/sensors" element={<Sensors />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}