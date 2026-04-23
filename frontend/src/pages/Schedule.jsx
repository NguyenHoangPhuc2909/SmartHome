import { useEffect, useState } from "react";
import { MdAdd, MdDelete, MdToggleOn, MdToggleOff } from "react-icons/md";
import useStore from "../store";
import api from "../services/api";

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const DAY_LABEL = { mon: "T2", tue: "T3", wed: "T4", thu: "T5", fri: "T6", sat: "T7", sun: "CN" };

const roomLabel = {
  living_room: "Phòng khách",
  bedroom:     "Phòng ngủ",
  kitchen:     "Phòng bếp",
  bathroom:    "Phòng tắm",
  entrance:    "Cửa chính",
};

const defaultForm = {
  device_id: "",
  action:    1,
  hour:      18,
  minute:    0,
  days:      ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
  is_active: true,
};

function Schedule() {
  const { schedules, devices, fetchSchedules, fetchDevices } = useStore();
  const [showForm, setShowForm] = useState(false);
  const [form,     setForm]     = useState(defaultForm);
  const [error,    setError]    = useState("");

  useEffect(() => {
	fetchSchedules();
	fetchDevices();
  }, []);

  const toggleDay = (day) => {
	setForm((prev) => ({
	  ...prev,
	  days: prev.days.includes(day)
		? prev.days.filter((d) => d !== day)
		: [...prev.days, day],
	}));
  };

  const handleAdd = async () => {
	if (!form.device_id) return setError("Chọn thiết bị");
	if (form.days.length === 0) return setError("Chọn ít nhất 1 ngày");
	try {
	  await api.post("/api/schedules/", {
		...form,
		days: form.days.join(","),
	  });
	  setShowForm(false);
	  setForm(defaultForm);
	  fetchSchedules();
	} catch (e) {
	  setError("Lỗi thêm lịch");
	}
  };

  const handleToggle = async (id) => {
	try {
	  await api.post(`/api/schedules/${id}/toggle`);
	  fetchSchedules();
	} catch (e) {
	  setError("Lỗi cập nhật lịch");
	}
  };

  const handleDelete = async (id) => {
	if (!confirm("Xoá lịch này?")) return;
	try {
	  await api.delete(`/api/schedules/${id}`);
	  fetchSchedules();
	} catch (e) {
	  setError("Lỗi xoá lịch");
	}
  };

  const getDeviceName = (id) => devices.find((d) => d.id === id)?.name || `Device ${id}`;
  const getDeviceRoom = (id) => {
	const room = devices.find((d) => d.id === id)?.room;
	return roomLabel[room] || room || "";
  };

  return (
	<div className="pt-14 min-h-screen" style={{ background: "var(--bg)" }}>
	  <div className="max-w-4xl mx-auto px-6 py-8">

		{/* Header */}
		<div className="flex items-center justify-between mb-8">
		  <div>
			<h1 className="text-2xl font-bold" style={{ fontFamily: "monospace", color: "var(--text)" }}>
			  Schedules
			</h1>
			<p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
			  Lịch tự động bật/tắt thiết bị
			</p>
		  </div>
		  <button onClick={() => setShowForm(!showForm)}
				  className="flex items-center gap-2 px-4 py-2 rounded-sm text-xs font-medium transition-all hover:opacity-80"
				  style={{
					background: "var(--accent)",
					color: "#0d0f0f",
					border: "none",
					cursor: "pointer",
					fontFamily: "monospace",
				  }}>
			<MdAdd size={16} /> Thêm lịch
		  </button>
		</div>

		{/* Error */}
		{error && (
		  <div className="mb-4 px-4 py-3 rounded-sm text-xs"
			   style={{
				 background: "rgba(255,107,53,0.08)",
				 border: "1px solid rgba(255,107,53,0.3)",
				 color: "#ff6b35",
				 fontFamily: "monospace",
			   }}>
			{error}
		  </div>
		)}

		{/* Add form */}
		{showForm && (
		  <div className="rounded-sm p-6 mb-6"
			   style={{
				 background: "rgba(255,255,255,0.03)",
				 border: "1px solid rgba(255,255,255,0.1)",
			   }}>
			<div className="text-xs tracking-widest uppercase mb-4"
				 style={{ fontFamily: "monospace", color: "var(--muted)" }}>
			  Thêm lịch mới
			</div>

			<div className="grid grid-cols-2 gap-4 mb-4">
			  {/* Device */}
			  <div>
				<label className="text-xs mb-1 block" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
				  Thiết bị
				</label>
				<select
				  value={form.device_id}
				  onChange={(e) => setForm({ ...form, device_id: Number(e.target.value) })}
				  className="w-full px-3 py-2 rounded-sm text-sm outline-none"
				  style={{
					background: "rgba(255,255,255,0.05)",
					border: "1px solid rgba(255,255,255,0.1)",
					color: "var(--text)",
					fontFamily: "monospace",
				  }}>
				  <option value="">-- Chọn thiết bị --</option>
				  {devices.map((d) => (
					<option key={d.id} value={d.id}
							style={{ background: "var(--surface)" }}>
					  {d.name} ({roomLabel[d.room] || d.room})
					</option>
				  ))}
				</select>
			  </div>

			  {/* Action */}
			  <div>
				<label className="text-xs mb-1 block" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
				  Hành động
				</label>
				<div className="flex gap-2">
				  {[{ val: 1, label: "BẬT" }, { val: 0, label: "TẮT" }].map(({ val, label }) => (
					<button key={val}
							onClick={() => setForm({ ...form, action: val })}
							className="flex-1 py-2 rounded-sm text-xs font-medium transition-all"
							style={{
							  fontFamily: "monospace",
							  background: form.action === val
								? val === 1 ? "rgba(184,245,80,0.15)" : "rgba(255,107,53,0.15)"
								: "rgba(255,255,255,0.05)",
							  color: form.action === val
								? val === 1 ? "var(--accent)" : "#ff6b35"
								: "var(--muted)",
							  border: `1px solid ${form.action === val
								? val === 1 ? "rgba(184,245,80,0.3)" : "rgba(255,107,53,0.3)"
								: "rgba(255,255,255,0.07)"}`,
							  cursor: "pointer",
							}}>
					  {label}
					</button>
				  ))}
				</div>
			  </div>

			  {/* Hour */}
			  <div>
				<label className="text-xs mb-1 block" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
				  Giờ (0–23)
				</label>
				<input type="number" min={0} max={23}
					   value={form.hour}
					   onChange={(e) => setForm({ ...form, hour: Number(e.target.value) })}
					   className="w-full px-3 py-2 rounded-sm text-sm outline-none"
					   style={{
						 background: "rgba(255,255,255,0.05)",
						 border: "1px solid rgba(255,255,255,0.1)",
						 color: "var(--text)",
						 fontFamily: "monospace",
					   }} />
			  </div>

			  {/* Minute */}
			  <div>
				<label className="text-xs mb-1 block" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
				  Phút (0–59)
				</label>
				<input type="number" min={0} max={59}
					   value={form.minute}
					   onChange={(e) => setForm({ ...form, minute: Number(e.target.value) })}
					   className="w-full px-3 py-2 rounded-sm text-sm outline-none"
					   style={{
						 background: "rgba(255,255,255,0.05)",
						 border: "1px solid rgba(255,255,255,0.1)",
						 color: "var(--text)",
						 fontFamily: "monospace",
					   }} />
			  </div>
			</div>

			{/* Days */}
			<div className="mb-4">
			  <label className="text-xs mb-2 block" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
				Ngày trong tuần
			  </label>
			  <div className="flex gap-2">
				{DAYS.map((day) => (
				  <button key={day}
						  onClick={() => toggleDay(day)}
						  className="flex-1 py-1.5 rounded-sm text-xs font-medium transition-all"
						  style={{
							fontFamily: "monospace",
							background: form.days.includes(day) ? "rgba(184,245,80,0.12)" : "rgba(255,255,255,0.04)",
							color: form.days.includes(day) ? "var(--accent)" : "var(--muted)",
							border: `1px solid ${form.days.includes(day) ? "rgba(184,245,80,0.3)" : "rgba(255,255,255,0.07)"}`,
							cursor: "pointer",
						  }}>
					{DAY_LABEL[day]}
				  </button>
				))}
			  </div>
			</div>

			{/* Submit */}
			<div className="flex gap-2 justify-end">
			  <button onClick={() => { setShowForm(false); setError(""); }}
					  className="px-4 py-2 rounded-sm text-xs transition-all hover:opacity-80"
					  style={{
						background: "rgba(255,255,255,0.05)",
						color: "var(--muted)",
						border: "1px solid rgba(255,255,255,0.07)",
						cursor: "pointer",
						fontFamily: "monospace",
					  }}>
				Huỷ
			  </button>
			  <button onClick={handleAdd}
					  className="px-4 py-2 rounded-sm text-xs font-medium transition-all hover:opacity-80"
					  style={{
						background: "var(--accent)",
						color: "#0d0f0f",
						border: "none",
						cursor: "pointer",
						fontFamily: "monospace",
					  }}>
				Lưu lịch
			  </button>
			</div>
		  </div>
		)}

		{/* Schedule list */}
		<div className="flex flex-col gap-2">
		  {schedules.length === 0 && (
			<div className="text-sm text-center py-12" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
			  Chưa có lịch nào
			</div>
		  )}
		  {schedules.map((s) => (
			<div key={s.id}
				 className="rounded-sm px-4 py-3 flex items-center gap-4 transition-all"
				 style={{
				   background: s.is_active ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.01)",
				   border: `1px solid ${s.is_active ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.03)"}`,
				   opacity: s.is_active ? 1 : 0.5,
				 }}>

			  {/* Time */}
			  <div className="text-xl font-bold w-16 flex-shrink-0"
				   style={{ fontFamily: "monospace", color: s.is_active ? "var(--text)" : "var(--muted)" }}>
				{String(s.hour).padStart(2, "0")}:{String(s.minute).padStart(2, "0")}
			  </div>

			  {/* Action badge */}
			  <div className="px-2 py-0.5 rounded-sm text-xs font-medium flex-shrink-0"
				   style={{
					 fontFamily: "monospace",
					 background: s.action === 1 ? "rgba(184,245,80,0.1)" : "rgba(255,107,53,0.1)",
					 color: s.action === 1 ? "var(--accent)" : "#ff6b35",
					 border: `1px solid ${s.action === 1 ? "rgba(184,245,80,0.25)" : "rgba(255,107,53,0.25)"}`,
				   }}>
				{s.action === 1 ? "BẬT" : "TẮT"}
			  </div>

			  {/* Device + room */}
			  <div className="flex-1">
				<div className="text-sm" style={{ color: "var(--text)" }}>
				  {getDeviceName(s.device_id)}
				</div>
				<div className="text-xs mt-0.5" style={{ color: "var(--muted)", fontFamily: "monospace" }}>
				  {getDeviceRoom(s.device_id)}
				</div>
			  </div>

			  {/* Days */}
			  <div className="flex gap-1">
				{DAYS.map((day) => (
				  <span key={day} className="text-xs px-1.5 py-0.5 rounded-sm"
						style={{
						  fontFamily: "monospace",
						  background: s.days.includes(day) ? "rgba(255,255,255,0.08)" : "transparent",
						  color: s.days.includes(day) ? "var(--text)" : "rgba(255,255,255,0.15)",
						}}>
					{DAY_LABEL[day]}
				  </span>
				))}
			  </div>

			  {/* Toggle + Delete */}
			  <div className="flex items-center gap-1 flex-shrink-0">
				<button onClick={() => handleToggle(s.id)}
						style={{ background: "none", border: "none", cursor: "pointer",
								 color: s.is_active ? "var(--accent)" : "var(--muted)" }}>
				  {s.is_active ? <MdToggleOn size={26} /> : <MdToggleOff size={26} />}
				</button>
				<button onClick={() => handleDelete(s.id)}
						className="p-1.5 rounded-sm transition-all hover:opacity-80"
						style={{ color: "#ff6b35", background: "rgba(255,107,53,0.08)", border: "none", cursor: "pointer" }}>
				  <MdDelete size={15} />
				</button>
			  </div>
			</div>
		  ))}
		</div>

	  </div>
	</div>
  );
}

export default Schedule;