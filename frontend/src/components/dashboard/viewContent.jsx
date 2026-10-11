import { useState, useEffect } from "react";
import { useAuth } from "../../contexts/AuthContext";
import MetricCard from "./MetricCard";
import FileManager from "./FileManager";
import DashboardBuilder from "./DashboardBuilder";
import {
  LayoutDashboard,
  Database,
  MessageSquareText,
  FileText,
  User,
  SlidersHorizontal,
  Package,
  Plug,
  ShieldAlert,
  Network,
  KeyRound,
  ActivitySquare,
  ChevronsUpDown,
  LogOut,
  Search,
  Upload,
  Send,
  Download,
  AlertTriangle,
  TrendingUp,
  FileSpreadsheet,
  Lightbulb,
  FolderArchive,
  LayoutGrid,
} from "lucide-react";

async function getAuthHeaders(refreshAccessToken) {
  let accessToken = localStorage.getItem('accessToken');
  if (!accessToken) return {};
  
  try {
    const payload = JSON.parse(atob(accessToken.split('.')[1]));
    if (Date.now() >= payload.exp * 1000) {
      accessToken = await refreshAccessToken();
    }
  } catch (e) {
    accessToken = await refreshAccessToken();
  }
  
  return accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {};
}

export const NAV_SECTIONS = [
  {
    label: "01 // CORE_WORKSPACE",
    items: [
      { id: "dashboard", icon: LayoutDashboard, label: "panel_principal", accent: "electric" },
      { id: "datasets", icon: Database, label: "gestion_datos", accent: "electric" },
      { id: "archivos", icon: FolderArchive, label: "gestion_archivos", accent: "electric" },
    ],
  },
  {
    label: "02 // AI_ANALYTICS",
    items: [
      { id: "chat-inteligente", icon: MessageSquareText, label: "chat_inteligente", accent: "purple" },
      { id: "reportes-ia", icon: FileText, label: "reportes_ia", accent: "purple" },
      { id: "dashboards", icon: LayoutGrid, label: "dashboards_armables", accent: "purple" },
    ],
  },
  {
    label: "03 // MANAGEMENT",
    items: [
      { id: "mg-perfil", icon: User, label: "usuario_perfil", accent: "electric" },
      { id: "mg-configuracion", icon: SlidersHorizontal, label: "conf_sistema", accent: "electric" },
      { id: "mg-suscripcion", icon: Package, label: "asignacion_cuotas", accent: "electric" },
      { id: "mg-integraciones", icon: Plug, label: "integraciones_api", accent: "electric" },
    ],
  },
  {
    label: "04 // ADMIN_STAGE",
    reserved: true,
    items: [
      { id: "ad-usuarios", icon: ShieldAlert, label: "adm_usuarios", accent: "purple" },
      { id: "ad-empresas", icon: Network, label: "adm_organizaciones", accent: "purple" },
      { id: "ad-licencias", icon: KeyRound, label: "adm_licencias", accent: "purple" },
      { id: "ad-monitoreo", icon: ActivitySquare, label: "global_telemetria", accent: "purple" },
    ],
  },
];



function UploadCSV({ onUpload }) {
  return (
    <div
      className="flex-1 border-2 border-dashed border-nura-border rounded-xl bg-nura-gray/30 flex flex-col items-center justify-center gap-4 p-12 group hover:border-nura-electric/40 transition-colors cursor-pointer"
      onClick={() => document.getElementById("csv-input").click()}
    >
      <div className="w-16 h-16 rounded-full bg-white/[0.02] border border-white/[0.06] flex items-center justify-center">
        <Upload className="w-6 h-6 text-white/20 group-hover:text-nura-electric transition-colors" />
      </div>
      <p className="text-white/40 text-center max-w-xs text-xs">
        Arrastra tu archivo CSV aquí o haz clic para examinar
      </p>
      <p className="text-white/20 text-[10px]">Formatos: .csv hasta 50MB</p>
      <input id="csv-input" type="file" accept=".csv" className="hidden" onChange={onUpload} />
      <button className="mt-2 px-4 py-2 rounded bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white transition-all text-[11px]">
        examinar_archivos()
      </button>
    </div>
  );
}

function DataPreview({ filename, context }) {
  if (!context) return null;
  const cols = Object.keys(context.columns || {});
  const rows = context.preview || [];
  
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-white/60 font-mono text-xs">
          {filename} &middot; {context.summary?.rows || 0} filas &middot; {context.summary?.columns || 0} columnas
        </span>
        <span className="text-[10px] text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded font-mono">
          VALIDADO
        </span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-nura-border">
        <table className="w-full text-[11px] font-mono">
          <thead>
            <tr className="bg-nura-gray/80 border-b border-nura-border">
              {cols.map((c) => (
                <th key={c} className="text-left text-white/50 py-2 px-3 font-medium">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-nura-border/50 hover:bg-white/[0.01]">
                {cols.map((c, j) => (
                  <td key={j} className="text-white/70 py-2 px-3">{row[c]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ChatMessage({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-nura-purple/20 border border-nura-purple/30 flex items-center justify-center font-mono text-[10px] text-nura-purple flex-none">
          AI
        </div>
      )}
      <div
        className={`max-w-[75%] rounded-xl px-4 py-2.5 text-xs leading-relaxed ${
          isUser
            ? "bg-nura-electric/10 border border-nura-electric/20 text-white/80"
            : "bg-white/[0.03] border border-white/[0.06] text-white/70"
        }`}
      >
        {text}
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-full bg-white/5 border border-white/10 flex items-center justify-center font-mono text-[10px] text-white/60 flex-none">
          U
        </div>
      )}
    </div>
  );
}

export const VIEW_CONTENT = {
  dashboard: () => {
    const { refreshAccessToken } = useAuth();
    const [context, setContext] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      const fetchContext = async () => {
        const API_BASE = import.meta.env.VITE_API_URL || '';
        try {
          const headers = await getAuthHeaders(refreshAccessToken);
          const res = await fetch(`${API_BASE}/sessions/default/`, { headers });
          if (res.ok) {
            const data = await res.json();
            setContext(data.dataset_context);
          }
        } catch (e) {
          console.error(e);
        } finally {
          setLoading(false);
        }
      };
      fetchContext();
    }, [refreshAccessToken]);

    const healthScore = context?.health?.health_score || 0;
    const rows = context?.summary?.rows || 0;
    const cols = context?.summary?.columns || 0;

    return (
      <div className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-light text-white tracking-tight">Panel Principal</h1>
          <p className="text-xs text-white/40 font-mono">Resumen general del espacio de trabajo de analítica.</p>
        </div>
        {loading ? (
          <div className="text-white/60 font-mono text-xs">Cargando panel...</div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <MetricCard label="HEALTH_SCORE" value={healthScore.toFixed(0)} unit="%" barWidth={`${healthScore}%`} />
              <MetricCard label="REGISTROS" value={rows} unit="filas" barColor="bg-nura-electric" barWidth="60%" />
              <MetricCard label="COLUMNAS" value={cols} unit="columnas" />
            </div>
            {context && (
              <div className="pure-glass rounded-xl p-5">
                <div className="flex items-center justify-between border-b border-nura-border pb-3 mb-4 font-mono text-xs">
                  <span className="text-white/80">Dataset_Activo // {context.file_name || "Ninguno"}</span>
                  <span className="text-[10px] px-1.5 rounded bg-nura-electric/10 text-nura-electric">
                    CONECTADO
                  </span>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  },

  datasets: () => {
    const { refreshAccessToken } = useAuth();
    const [datasets, setDatasets] = useState([]);
    const [search, setSearch] = useState('');
    const [filterType, setFilterType] = useState('');
    const [filterStatus, setFilterStatus] = useState('');
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);

    const fetchDatasets = async () => {
      setLoading(true);
      const API_BASE = import.meta.env.VITE_API_URL || '';
      try {
        const headers = await getAuthHeaders(refreshAccessToken);
        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (filterType) params.append('type', filterType);
        if (filterStatus) params.append('status', filterStatus);
        
        const response = await fetch(`${API_BASE}/datasets?${params}`, { headers });
        const data = await response.json();
        setDatasets(data);
      } catch (error) {
        console.error('Error fetching datasets:', error);
      } finally {
        setLoading(false);
      }
    };

    useEffect(() => {
      fetchDatasets();
    }, [search, filterType, filterStatus, refreshAccessToken]);

    const handleUpload = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setUploading(true);
      
      const API_BASE = import.meta.env.VITE_API_URL || '';
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const headers = await getAuthHeaders(refreshAccessToken);
        const response = await fetch(`${API_BASE}/datasets`, {
          method: 'POST',
          headers,
          body: formData
        });
        if (response.ok) {
          fetchDatasets();
        }
      } catch (error) {
        console.error('Error uploading:', error);
      } finally {
        setUploading(false);
      }
    };

    const handleDelete = async (id) => {
      if (!window.confirm('¿Estás seguro de eliminar este dataset?')) return;
      
      const API_BASE = import.meta.env.VITE_API_URL || '';
      try {
        const headers = await getAuthHeaders(refreshAccessToken);
        await fetch(`${API_BASE}/datasets/${id}`, {
          method: 'DELETE',
          headers
        });
        fetchDatasets();
      } catch (error) {
        console.error('Error deleting:', error);
      }
    };

    const handleRename = async (id, newName) => {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      try {
        const headers = await getAuthHeaders(refreshAccessToken);
        headers['Content-Type'] = 'application/json';
        await fetch(`${API_BASE}/datasets/${id}`, {
          method: 'PUT',
          headers,
          body: JSON.stringify({ file_name: newName })
        });
        fetchDatasets();
      } catch (error) {
        console.error('Error renaming:', error);
      }
    };

    const handleActivate = async (id) => {
      const API_BASE = import.meta.env.VITE_API_URL || '';
      try {
        const headers = await getAuthHeaders(refreshAccessToken);
        headers['Content-Type'] = 'application/json';
        await fetch(`${API_BASE}/datasets/${id}/activate`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ session_id: 'default' })
        });
        alert('Dataset activado para chat!');
      } catch (error) {
        console.error('Error activating:', error);
      }
    };

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
      <div className="space-y-4 font-mono text-xs h-full flex flex-col">
        <div className="flex items-center justify-between">
          <h2 className="text-lg text-white font-light">// gestion_datos</h2>
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Buscar..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="px-3 py-1.5 rounded bg-white/5 border border-white/10 text-white/80 text-xs focus:outline-none focus:border-nura-electric/40"
            />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-1.5 rounded bg-white/5 border border-white/10 text-white/80 text-xs focus:outline-none focus:border-nura-electric/40"
            >
              <option value="">Todos los tipos</option>
              <option value="csv">CSV</option>
              <option value="xlsx">Excel</option>
              <option value="json">JSON</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-1.5 rounded bg-white/5 border border-white/10 text-white/80 text-xs focus:outline-none focus:border-nura-electric/40"
            >
              <option value="">Todos los estados</option>
              <option value="valid">Válido</option>
              <option value="invalid">Inválido</option>
              <option value="pending">Pendiente</option>
            </select>
          </div>
        </div>

        {/* Upload area */}
        <div
          className="border-2 border-dashed border-nura-border rounded-xl bg-nura-gray/30 flex flex-col items-center justify-center gap-3 p-6 group hover:border-nura-electric/40 transition-colors cursor-pointer"
          onClick={() => document.getElementById('dataset-upload').click()}
        >
          <input
            id="dataset-upload"
            type="file"
            accept=".csv,.xlsx,.json"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
          <Upload className="w-6 h-6 text-white/20 group-hover:text-nura-electric transition-colors" />
          <p className="text-white/40 text-center text-xs">
            {uploading ? 'Subiendo...' : 'Arrastra tus archivos aquí o haz clic para examinar'}
          </p>
          <p className="text-white/20 text-[10px]">Formatos: CSV, XLSX, JSON (máx. 50MB)</p>
        </div>

        {/* Datasets list */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-2 min-h-0 scrollbar-thin">
          {loading ? (
            <div className="text-white/60">Cargando datasets...</div>
          ) : datasets.length === 0 ? (
            <div className="text-white/40 text-center py-8">No hay datasets aún. Sube tu primer archivo!</div>
          ) : (
            datasets.map((dataset) => (
              <div
                key={dataset.id}
                className="pure-glass rounded-xl p-4 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 flex-1">
                  <FileSpreadsheet className="w-8 h-8 text-nura-electric/60" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={dataset.file_name}
                        onChange={(e) => handleRename(dataset.id, e.target.value)}
                        className="text-white font-medium text-sm bg-transparent border-none focus:outline-none focus:border-b focus:border-nura-electric/40"
                      />
                      <span className={`text-[10px] px-2 py-0.5 rounded ${
                        dataset.status === 'valid' ? 'bg-emerald-500/10 text-emerald-400' :
                        dataset.status === 'invalid' ? 'bg-red-500/10 text-red-400' :
                        'bg-yellow-500/10 text-yellow-400'
                      }`}>
                        {dataset.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-white/40 text-[10px] mt-1">
                      <span>{dataset.file_type.toUpperCase()}</span>
                      <span>{formatFileSize(dataset.file_size)}</span>
                      <span>{new Date(dataset.uploaded_at).toLocaleDateString()}</span>
                      {dataset.analysis_context?.summary && (
                        <span>{dataset.analysis_context.summary.rows} filas, {dataset.analysis_context.summary.columns} columnas</span>
                      )}
                    </div>
                    {dataset.validation_errors.length > 0 && (
                      <div className="text-red-400 text-[10px] mt-1">
                        {dataset.validation_errors.join(', ')}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {dataset.file_url && (
                    <a
                      href={dataset.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 rounded bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white transition-all text-[11px]"
                    >
                      Descargar
                    </a>
                  )}
                  {dataset.status === 'valid' && (
                    <button
                      onClick={() => handleActivate(dataset.id)}
                      className="px-3 py-1.5 rounded bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-[11px]"
                    >
                      Usar en Chat
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(dataset.id)}
                    className="px-3 py-1.5 rounded bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition-all text-[11px]"
                  >
                    Eliminar
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    );
  },

  archivos: () => <FileManager />,

  "chat-inteligente": () => {
    const { refreshAccessToken } = useAuth();
    const [messages, setMessages] = useState([
      { role: "assistant", text: "¡Hola! Soy el asistente de analítica. Puedo responder preguntas sobre tu dataset en lenguaje natural. ¿Qué deseas consultar?" },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [provider, setProvider] = useState("groq");

    const handleSend = async () => {
      if (!input.trim() || loading) return;
      const text = input;
      setMessages((prev) => [...prev, { role: "user", text }]);
      setInput("");
      setLoading(true);

      const API_BASE = import.meta.env.VITE_API_URL || '';
      try {
        const headers = await getAuthHeaders(refreshAccessToken);
        const response = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            ...headers
          },
          body: JSON.stringify({ message: text, session_id: 'default' })
        });
        const data = await response.json();
        setMessages((prev) => [...prev, { role: "assistant", text: data.response || "Error" }]);
      } catch (error) {
        console.error("Error sending message:", error);
        setMessages((prev) => [...prev, { role: "assistant", text: "Ocurrió un error al procesar tu solicitud." }]);
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="space-y-4 font-mono text-xs h-full flex flex-col">
        <div className="flex items-center justify-between">
          <h2 className="text-lg text-white font-light">// chat_inteligente</h2>
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-white/30 uppercase">Proveedor IA:</span>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="bg-nura-black border border-nura-border rounded px-2 py-1 text-white/80 text-[11px] outline-none cursor-pointer"
            >
              <option value="groq">Groq</option>
              <option value="cerebras">Cerebras</option>
              <option value="openrouter">OpenRouter</option>
            </select>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto space-y-3 pr-2 min-h-0 scrollbar-thin">
          {messages.map((msg, i) => (
            <ChatMessage key={i} role={msg.role} text={msg.text} />
          ))}
          {loading && (
            <div className="text-nura-purple text-[10px] animate-pulse">Escribiendo...</div>
          )}
        </div>
        <div className="flex gap-2 pt-2 border-t border-nura-border">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            disabled={loading}
            placeholder="Ej: ¿Cuáles fueron los productos más vendidos por categoría?..."
            className="flex-1 bg-white/5 border border-nura-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-[12px]"
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="px-4 rounded-lg bg-nura-purple/20 border border-nura-purple/30 text-nura-purple hover:bg-nura-purple/30 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  },

  "reportes-ia": () => {
    const { refreshAccessToken } = useAuth();
    const [context, setContext] = useState(null);
    const [loading, setLoading] = useState(true);
    const [exportingFormat, setExportingFormat] = useState(null); // 'pdf' | 'docx' | 'pptx' | null
    const [exportError, setExportError] = useState("");
    const [reportAudience, setReportAudience] = useState("executive"); // 'executive' | 'technical' | 'financial'

    useEffect(() => {
      const fetchContext = async () => {
        const API_BASE = import.meta.env.VITE_API_URL || '';
        try {
          const headers = await getAuthHeaders(refreshAccessToken);
          const res = await fetch(`${API_BASE}/sessions/default/`, { headers });
          if (res.ok) {
            const data = await res.json();
            setContext(data.dataset_context);
          }
        } catch (e) {
          console.error(e);
        } finally {
          setLoading(false);
        }
      };
      fetchContext();
    }, [refreshAccessToken]);

    const handleExportReport = async (format) => {
      setExportingFormat(format);
      setExportError("");
      const API_BASE = import.meta.env.VITE_API_URL || '';
      try {
        const headers = await getAuthHeaders(refreshAccessToken);
        const res = await fetch(`${API_BASE}/sessions/default/report/${format}/?audience=${reportAudience}`, { headers });
        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.error || `Error ${res.status} al generar el reporte`);
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `reporte_${(context?.file_name || 'dataset').replace(/\.[^/.]+$/, '')}_${reportAudience}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch (e) {
        setExportError(e.message || "No se pudo generar el reporte.");
      } finally {
        setExportingFormat(null);
      }
    };

    if (loading) return <div className="text-white/60 font-mono text-xs p-4">Cargando reporte IA...</div>;
    if (!context) return <div className="text-white/60 font-mono text-xs p-4">No hay datos para reportar. Sube un dataset primero.</div>;

    const riskLevel = context.health?.risk_level || "Desconocido";
    const healthScore = context.health?.health_score || 0;

    return (
      <div className="space-y-4 font-mono text-xs">
        <h2 className="text-lg text-white font-light">// reportes_ia</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="pure-glass rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 text-nura-electric text-[11px]">
              <FileText className="w-4 h-4" />
              <span>Resumen Ejecutivo</span>
            </div>
            <p className="text-white/60 leading-relaxed text-[11px] max-h-32 overflow-y-auto pr-2 scrollbar-thin">
              {context.response?.split("📝 Resumen Ejecutivo para ti:")[1] || 
              context.response || 
              `El archivo ${context.file_name} ha sido procesado. Contiene ${context.summary?.rows} filas y ${context.summary?.columns} columnas.`}
            </p>
          </div>
          <div className="pure-glass rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 text-amber-400 text-[11px]">
              <AlertTriangle className="w-4 h-4" />
              <span>Análisis de Riesgos (Score: {healthScore.toFixed(0)})</span>
            </div>
            <ul className="space-y-2 text-[11px]">
              <li className="flex gap-2 text-white/60">
                <span className="text-amber-400/60">&bull;</span>
                <span>Nivel de riesgo estimado: {riskLevel}</span>
              </li>
              {(context.anomalies?.missing_values || []).slice(0, 2).map((a, i) => (
                <li key={i} className="flex gap-2 text-white/60">
                  <span className="text-amber-400/60">&bull;</span>
                  <span>{a.column} tiene {a.missing} valores nulos.</span>
                </li>
              ))}
              {(!context.anomalies?.missing_values || context.anomalies.missing_values.length === 0) && (
                <li className="flex gap-2 text-emerald-400/80">
                  <span className="text-emerald-400/60">&bull;</span>
                  <span>No hay alertas críticas importantes.</span>
                </li>
              )}
            </ul>
          </div>
          <div className="pure-glass rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 text-emerald-400 text-[11px]">
              <Lightbulb className="w-4 h-4" />
              <span>Oportunidades y Variables Clave</span>
            </div>
            <ul className="space-y-2 text-[11px]">
              {(context.critical_variables || []).slice(0, 3).map((v, i) => (
                <li key={i} className="flex gap-2 text-white/60">
                  <span className="text-emerald-400/60">&bull;</span>
                  <span>Variable de alta influencia: {v.column}</span>
                </li>
              ))}
              {(!context.critical_variables || context.critical_variables.length === 0) && (
                <li className="flex gap-2 text-white/60">
                  <span className="text-emerald-400/60">&bull;</span>
                  <span>Requiere más datos correlacionados para identificar oportunidades.</span>
                </li>
              )}
            </ul>
          </div>
          <div className="pure-glass rounded-xl p-5 space-y-4 flex flex-col justify-between">
            <div className="flex items-center gap-2 text-nura-purple text-[11px]">
              <Download className="w-4 h-4" />
              <span>Exportar Reporte</span>
            </div>
            <p className="text-white/40 text-[10px] leading-relaxed">
              Genera un informe completo con resumen ejecutivo, análisis de riesgos,
              oportunidades y recomendaciones basadas en IA.
            </p>
            <div className="space-y-1.5">
              <span className="text-white/30 text-[10px] uppercase tracking-wide">Audiencia del reporte</span>
              <div className="flex gap-1.5">
                {[
                  { key: 'executive', label: 'Ejecutivo' },
                  { key: 'technical', label: 'Técnico' },
                  { key: 'financial', label: 'Financiero' },
                ].map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setReportAudience(opt.key)}
                    className={`flex-1 py-1.5 rounded-md text-[10px] border transition-all ${
                      reportAudience === opt.key
                        ? "bg-nura-electric/20 border-nura-electric/40 text-nura-electric"
                        : "bg-white/5 border-white/10 text-white/40 hover:text-white/60"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleExportReport('pdf')}
                disabled={exportingFormat !== null}
                className="flex-1 py-3 rounded-lg bg-nura-purple/20 border border-nura-purple/30 text-nura-purple hover:bg-nura-purple/30 transition-all text-[11px] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="w-4 h-4" />
                {exportingFormat === 'pdf' ? "Generando..." : "PDF"}
              </button>
              <button
                onClick={() => handleExportReport('docx')}
                disabled={exportingFormat !== null}
                className="flex-1 py-3 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-[11px] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FileText className="w-4 h-4" />
                {exportingFormat === 'docx' ? "Generando..." : "Word"}
              </button>
              <button
                onClick={() => handleExportReport('pptx')}
                disabled={exportingFormat !== null}
                className="flex-1 py-3 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-400 hover:bg-amber-500/30 transition-all text-[11px] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FileText className="w-4 h-4" />
                {exportingFormat === 'pptx' ? "Generando..." : "Slides"}
              </button>
            </div>
            {exportError && (
              <p className="text-red-400 text-[10px]">{exportError}</p>
            )}
          </div>
        </div>
      </div>
    );
  },

  "dashboards": DashboardBuilder,

  "mg-perfil": () => {
    const { user, getProfile, updateProfile, changePassword } = useAuth();
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [savingProfile, setSavingProfile] = useState(false);
    const [savingPassword, setSavingPassword] = useState(false);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');
    const [profileForm, setProfileForm] = useState({ user: { first_name: '', last_name: '' } });
    const [passwordForm, setPasswordForm] = useState({ old_password: '', new_password1: '', new_password2: '' });

    useEffect(() => {
      const fetchProfile = async () => {
        try {
          const data = await getProfile();
          setProfile(data);
          setProfileForm({
            user: {
              first_name: data?.user?.first_name || '',
              last_name: data?.user?.last_name || ''
            }
          });
        } catch (e) {
          console.error('Error fetching profile:', e);
        } finally {
          setLoading(false);
        }
      };
      fetchProfile();
    }, [getProfile]);

    const handleProfileSubmit = async (e) => {
      e.preventDefault();
      setSavingProfile(true);
      setMessage('');
      setMessageType('');
      try {
        const updated = await updateProfile(profileForm);
        setProfile(updated);
        setMessage('Perfil actualizado correctamente');
        setMessageType('success');
      } catch (error) {
        setMessage(error.message || 'Error al actualizar el perfil');
        setMessageType('error');
      } finally {
        setSavingProfile(false);
      }
    };

    const handlePasswordSubmit = async (e) => {
      e.preventDefault();
      setSavingPassword(true);
      setMessage('');
      setMessageType('');
      try {
        await changePassword(passwordForm.old_password, passwordForm.new_password1, passwordForm.new_password2);
        setMessage('Contraseña cambiada correctamente');
        setMessageType('success');
        setPasswordForm({ old_password: '', new_password1: '', new_password2: '' });
      } catch (error) {
        setMessage(error.message || 'Error al cambiar la contraseña');
        setMessageType('error');
      } finally {
        setSavingPassword(false);
      }
    };

    if (loading) {
      return (
        <div className="space-y-4 font-mono text-xs">
          <h2 className="text-lg text-white font-light">// usuario_perfil</h2>
          <div className="p-4 border border-nura-border rounded bg-nura-gray/60 text-white/40">
            Cargando perfil...
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-6 font-mono text-xs">
        <h2 className="text-lg text-white font-light">// usuario_perfil</h2>
        
        {message && (
          <div className={`p-3 rounded border ${messageType === 'success' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-red-500/30 bg-red-500/10 text-red-400'}`}>
            {message}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="pure-glass rounded-xl p-5 space-y-4">
            <h3 className="text-sm text-white font-medium mb-4">Información personal</h3>
            <form onSubmit={handleProfileSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-white/40 text-[10px] uppercase tracking-widest">Email</label>
                <input
                  type="email"
                  value={user?.email || ''}
                  disabled
                  className="w-full bg-white/5 border border-nura-border rounded-lg px-4 py-2.5 text-white/70 text-xs outline-none cursor-not-allowed"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-white/40 text-[10px] uppercase tracking-widest">Nombre</label>
                <input
                  type="text"
                  value={profileForm.user.first_name}
                  onChange={(e) => setProfileForm({ ...profileForm, user: { ...profileForm.user, first_name: e.target.value } })}
                  className="w-full bg-white/5 border border-nura-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-white/40 text-[10px] uppercase tracking-widest">Apellido</label>
                <input
                  type="text"
                  value={profileForm.user.last_name}
                  onChange={(e) => setProfileForm({ ...profileForm, user: { ...profileForm.user, last_name: e.target.value } })}
                  className="w-full bg-white/5 border border-nura-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-xs"
                />
              </div>
              <button
                type="submit"
                disabled={savingProfile}
                className="px-4 py-2.5 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all disabled:opacity-50 text-[11px]"
              >
                {savingProfile ? 'Guardando...' : 'guardar_cambios()'}
              </button>
            </form>
          </div>

          <div className="pure-glass rounded-xl p-5 space-y-4">
            <h3 className="text-sm text-white font-medium mb-4">Cambiar contraseña</h3>
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div className="space-y-1">
                <label className="block text-white/40 text-[10px] uppercase tracking-widest">Contraseña actual</label>
                <input
                  type="password"
                  value={passwordForm.old_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, old_password: e.target.value })}
                  className="w-full bg-white/5 border border-nura-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-white/40 text-[10px] uppercase tracking-widest">Nueva contraseña</label>
                <input
                  type="password"
                  value={passwordForm.new_password1}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password1: e.target.value })}
                  className="w-full bg-white/5 border border-nura-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-white/40 text-[10px] uppercase tracking-widest">Confirmar nueva contraseña</label>
                <input
                  type="password"
                  value={passwordForm.new_password2}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password2: e.target.value })}
                  className="w-full bg-white/5 border border-nura-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-xs"
                />
              </div>
              <button
                type="submit"
                disabled={savingPassword}
                className="px-4 py-2.5 rounded-lg bg-nura-purple/20 border border-nura-purple/30 text-nura-purple hover:bg-nura-purple/30 transition-all disabled:opacity-50 text-[11px]"
              >
                {savingPassword ? 'Cambiando...' : 'cambiar_contraseña()'}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  },
  "mg-configuracion": () => (
    <div className="space-y-4 font-mono text-xs">
      <h2 className="text-lg text-white font-light">// conf_sistema</h2>
      <div className="p-4 border border-nura-border rounded bg-nura-gray/60 text-white/40">
        Configuración del sistema
      </div>
    </div>
  ),
  "mg-suscripcion": () => (
    <div className="space-y-4 font-mono text-xs">
      <h2 className="text-lg text-white font-light">// asignacion_cuotas</h2>
      <div className="p-4 border border-nura-border rounded bg-nura-gray/60 text-white/40">
        Información de suscripción
      </div>
    </div>
  ),
  "mg-integraciones": () => (
    <div className="space-y-4 font-mono text-xs">
      <h2 className="text-lg text-white font-light">// integraciones_api</h2>
      <div className="p-4 border border-nura-border rounded bg-nura-gray/60 text-white/40">
        Integraciones API
      </div>
    </div>
  ),
  "ad-usuarios": () => (
    <div className="space-y-4 font-mono text-xs">
      <h2 className="text-lg text-white/40 font-light">
        // adm_usuarios{" "}
        <span className="text-[9px] bg-nura-purple/20 text-nura-purple px-1 rounded ml-2">RESERVADO_FUTURO</span>
      </h2>
      <p className="text-white/20">Módulo retenido para control IAM multi-inquilino avanzada.</p>
    </div>
  ),
  "ad-empresas": () => (
    <div className="space-y-4 font-mono text-xs">
      <h2 className="text-lg text-white/40 font-light">
        // adm_organizaciones{" "}
        <span className="text-[9px] bg-nura-purple/20 text-nura-purple px-1 rounded ml-2">RESERVADO_FUTURO</span>
      </h2>
      <p className="text-white/20">Módulo retenido para control de sub-tenants globales.</p>
    </div>
  ),
  "ad-licencias": () => (
    <div className="space-y-4 font-mono text-xs">
      <h2 className="text-lg text-white/40 font-light">
        // adm_licencias{" "}
        <span className="text-[9px] bg-nura-purple/20 text-nura-purple px-1 rounded ml-2">RESERVADO_FUTURO</span>
      </h2>
      <p className="text-white/20">Módulo retenido para firma criptográfica de llaves on-premise.</p>
    </div>
  ),
  "ad-monitoreo": () => (
    <div className="space-y-4 font-mono text-xs">
      <h2 className="text-lg text-white/40 font-light">
        // global_telemetria{" "}
        <span className="text-[9px] bg-nura-purple/20 text-nura-purple px-1 rounded ml-2">RESERVADO_FUTURO</span>
      </h2>
      <p className="text-white/20">Módulo retenido para trazas de telemetría inmutable distribuida.</p>
    </div>
  ),
};

export const ICON_MAP = {
  LayoutDashboard,
  Database,
  MessageSquareText,
  FileText,
  User,
  SlidersHorizontal,
  Package,
  Plug,
  ShieldAlert,
  Network,
  KeyRound,
  ActivitySquare,
  ChevronsUpDown,
  LogOut,
  Search,
  Upload,
  Send,
  Download,
  AlertTriangle,
  TrendingUp,
  FileSpreadsheet,
  Lightbulb,
  FolderArchive,
};