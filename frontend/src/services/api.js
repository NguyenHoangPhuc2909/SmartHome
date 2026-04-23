import axios from "axios";

// Axios instance — tất cả request đều qua đây
const api = axios.create({
  baseURL: "/",           // dùng Vite proxy, không cần localhost:5000
  withCredentials: true,          // gửi session cookie
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor — tự redirect về /login nếu 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export default api;