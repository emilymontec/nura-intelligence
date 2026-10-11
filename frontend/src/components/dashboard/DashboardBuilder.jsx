import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../../contexts/AuthContext";
import {
  Plus, Sparkles, Trash2, GripVertical, LayoutGrid, X, Loader2,
} from "lucide-react";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from "chart.js";
import { Line, Bar, Scatter } from "react-chartjs-2";
import HeatmapChart from "../analytics/HeatmapChart";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

const API_BASE = import.meta.env.VITE_API_URL || "";

async function getAuthHeaders(refreshAccessToken) {
  let accessToken = localStorage.getItem("accessToken");
  if (!accessToken) return {};
  try {
    const payload = JSON.parse(atob(accessToken.split(".")[1]));
    if (Date.now() >= payload.exp * 1000) accessToken = await refreshAccessToken();
  } catch {
    accessToken = await refreshAccessToken();
  }
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

function KpiWidget({ widget }) {
  return (
    <div className="h-full flex flex-col justify-center gap-1">
      <span className="text-white/40 text-[10px] uppercase tracking-wide truncate">{widget.title}</span>
      <strong className="text-white text-xl font-light">{String(widget.source?.value ?? "—")}</strong>
    </div>
  );
}

function ChartWidget({ widget }) {
  const chart = widget.source || {};

  if (widget.chart_type === "distribution" && chart.data) {
    const data = {
      labels: chart.data.slice(0, 20).map((_, i) => `#${i + 1}`),
      datasets: [{ label: widget.title, data: chart.data.slice(0, 20), borderColor: "#4F7BFF", backgroundColor: "rgba(79,123,255,0.1)", fill: true }],
    };
    return <Line data={data} options={chartOptions} />;
  }
  if (widget.chart_type === "categorical" && chart.labels) {
    const data = {
      labels: chart.labels,
      datasets: [{ label: widget.title, data: chart.values, backgroundColor: "rgba(108,77,255,0.5)", borderColor: "#6C4DFF" }],
    };
    return <Bar data={data} options={chartOptions} />;
  }
  if (widget.chart_type === "scatter" && chart.points) {
    const data = { datasets: [{ label: widget.title, data: chart.points, backgroundColor: "rgba(79,123,255,0.6)" }] };
    return <Scatter data={data} options={chartOptions} />;
  }
  if (widget.chart_type === "heatmap" && chart.labels && chart.cells) {
    return (
      <div style={{ transform: "scale(0.65)", transformOrigin: "top left" }}>
        <HeatmapChart labels={chart.labels} cells={chart.cells} />
      </div>
    );
  }
  return <div className="text-white/30 text-[11px]">Sin datos para este gráfico.</div>;
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#999", font: { size: 9 } } },
    y: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#999", font: { size: 9 } } },
  },
};

export default function DashboardBuilder() {
  const { refreshAccessToken } = useAuth();
  const getHeaders = useCallback(getAuthHeaders(refreshAccessToken), [refreshAccessToken]);

  const [dashboards, setDashboards] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [layout, setLayout] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [showAiPicker, setShowAiPicker] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  const dragIndex = useRef(null);

  const active = dashboards.find((d) => d.id === activeId) || null;

  const fetchDashboards = useCallback(async () => {
    setLoading(true);
    try {
      const headers = await getHeaders();
      const res = await fetch(`${API_BASE}/dashboards`, { headers });
      if (res.ok) {
        const data = await res.json();
        setDashboards(data);
        if (data.length && !activeId) {
          setActiveId(data[0].id);
          setLayout(data[0].layout || []);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getHeaders]);

  useEffect(() => { fetchDashboards(); }, [fetchDashboards]);

  useEffect(() => {
    if (active) setLayout(active.layout || []);
  }, [activeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchDatasets = useCallback(async () => {
    try {
      const headers = await getHeaders();
      const res = await fetch(`${API_BASE}/datasets?status=valid`, { headers });
      if (res.ok) setDatasets(await res.json());
    } catch (e) {
      console.error(e);
    }
  }, [getHeaders]);

  const handleCreateDashboard = async () => {
    setError("");
    try {
      const headers = await getHeaders();
      const res = await fetch(`${API_BASE}/dashboards`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ name: `Dashboard ${dashboards.length + 1}`, layout: [] }),
      });
      if (res.ok) {
        const d = await res.json();
        setDashboards((prev) => [d, ...prev]);
        setActiveId(d.id);
        setLayout([]);
      }
    } catch (e) {
      setError("No se pudo crear el dashboard.");
    }
  };

  const handleDeleteDashboard = async (id) => {
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/dashboards/${id}/`, { method: "DELETE", headers });
      setDashboards((prev) => prev.filter((d) => d.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setLayout([]);
      }
    } catch (e) {
      setError("No se pudo eliminar el dashboard.");
    }
  };

  const persistLayout = async (newLayout) => {
    if (!activeId) return;
    setSaving(true);
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/dashboards/${activeId}/`, {
        method: "PATCH",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ layout: newLayout }),
      });
      setDashboards((prev) => prev.map((d) => (d.id === activeId ? { ...d, layout: newLayout } : d)));
    } catch (e) {
      setError("No se pudo guardar el orden del dashboard.");
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveWidget = (widgetId) => {
    const newLayout = layout.filter((w) => w.id !== widgetId);
    setLayout(newLayout);
    persistLayout(newLayout);
  };

  // --- Drag & drop (reordenamiento nativo HTML5) ---
  const handleDragStart = (index) => { dragIndex.current = index; };
  const handleDragOver = (e) => e.preventDefault();
  const handleDrop = (index) => {
    const from = dragIndex.current;
    if (from === null || from === index) return;
    const newLayout = [...layout];
    const [moved] = newLayout.splice(from, 1);
    newLayout.splice(index, 0, moved);
    setLayout(newLayout);
    persistLayout(newLayout);
    dragIndex.current = null;
  };

  const handleGenerateAI = async (datasetId) => {
    setGenerating(true);
    setError("");
    try {
      const headers = await getHeaders();
      const res = await fetch(`${API_BASE}/dashboards/generate-ai/`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, dashboard_id: activeId || undefined }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "No se pudo generar el dashboard con IA.");
      }
      const d = await res.json();
      setDashboards((prev) => {
        const exists = prev.some((x) => x.id === d.id);
        return exists ? prev.map((x) => (x.id === d.id ? d : x)) : [d, ...prev];
      });
      setActiveId(d.id);
      setLayout(d.layout || []);
      setShowAiPicker(false);
    } catch (e) {
      setError(e.message || "No se pudo generar el dashboard con IA.");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div className="text-white/60 font-mono text-xs p-4">Cargando dashboards...</div>;
  }

  return (
    <div className="space-y-4 font-mono text-xs">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg text-white font-light">// dashboards_armables</h2>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowAiPicker(true); fetchDatasets(); }}
            className="px-3 py-2 rounded-lg bg-nura-purple/20 border border-nura-purple/30 text-nura-purple hover:bg-nura-purple/30 transition-all text-[11px] flex items-center gap-2"
          >
            <Sparkles className="w-3.5 h-3.5" /> Generar con IA
          </button>
          <button
            onClick={handleCreateDashboard}
            className="px-3 py-2 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-[11px] flex items-center gap-2"
          >
            <Plus className="w-3.5 h-3.5" /> Nuevo dashboard
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-[11px]">{error}</div>
      )}

      {/* Tabs de dashboards */}
      {dashboards.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {dashboards.map((d) => (
            <div
              key={d.id}
              onClick={() => setActiveId(d.id)}
              className={`shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg border cursor-pointer transition-all text-[11px] ${
                activeId === d.id
                  ? "bg-white/10 border-nura-electric/40 text-white"
                  : "bg-white/[0.02] border-white/10 text-white/40 hover:text-white/70"
              }`}
            >
              <LayoutGrid className="w-3 h-3" />
              <span className="max-w-[160px] truncate">{d.name}</span>
              {d.is_ai_generated && <Sparkles className="w-3 h-3 text-nura-purple" />}
              <button
                onClick={(e) => { e.stopPropagation(); handleDeleteDashboard(d.id); }}
                className="text-white/20 hover:text-red-400"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Grid de widgets */}
      {!activeId && (
        <div className="border-2 border-dashed border-nura-border rounded-xl p-12 text-center text-white/30">
          Crea un dashboard nuevo o generá uno automáticamente con IA a partir de un dataset ya analizado.
        </div>
      )}

      {activeId && layout.length === 0 && (
        <div className="border-2 border-dashed border-nura-border rounded-xl p-12 text-center text-white/30">
          Este dashboard está vacío. Generalo con IA desde un dataset para poblarlo con KPIs y gráficos.
        </div>
      )}

      {activeId && layout.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {layout.map((widget, index) => (
            <div
              key={widget.id}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(index)}
              className={`pure-glass rounded-xl p-4 relative group ${widget.kind === "kpi" ? "h-28" : "h-56"}`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5 text-white/30 cursor-grab active:cursor-grabbing">
                  <GripVertical className="w-3.5 h-3.5" />
                  {widget.kind !== "kpi" && <span className="text-[10px] truncate max-w-[140px]">{widget.title}</span>}
                </div>
                <button
                  onClick={() => handleRemoveWidget(widget.id)}
                  className="opacity-0 group-hover:opacity-100 text-white/20 hover:text-red-400 transition-opacity"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className={widget.kind === "kpi" ? "h-[calc(100%-20px)]" : "h-[calc(100%-24px)]"}>
                {widget.kind === "kpi" ? <KpiWidget widget={widget} /> : <ChartWidget widget={widget} />}
              </div>
            </div>
          ))}
        </div>
      )}

      {saving && <p className="text-white/30 text-[10px]">Guardando orden...</p>}

      {/* Picker de dataset para generación IA */}
      {showAiPicker && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={() => setShowAiPicker(false)}>
          <div className="pure-glass rounded-xl p-5 max-w-md w-full space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="text-white text-sm font-light flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-nura-purple" /> Generar dashboard con IA
              </h3>
              <button onClick={() => setShowAiPicker(false)} className="text-white/40 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-white/40 text-[11px]">Elegí un dataset ya analizado; Nura arma el dashboard con sus KPIs y gráficos automáticamente.</p>
            <div className="max-h-64 overflow-y-auto space-y-1.5">
              {datasets.length === 0 && (
                <p className="text-white/30 text-[11px] py-4 text-center">No hay datasets disponibles todavía.</p>
              )}
              {datasets.map((ds) => (
                <button
                  key={ds.id}
                  disabled={generating}
                  onClick={() => handleGenerateAI(ds.id)}
                  className="w-full text-left px-3 py-2 rounded-lg bg-white/[0.03] border border-white/10 hover:border-nura-purple/40 text-white/70 hover:text-white transition-all text-[11px] flex items-center justify-between disabled:opacity-50"
                >
                  <span className="truncate">{ds.file_name}</span>
                  {generating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
