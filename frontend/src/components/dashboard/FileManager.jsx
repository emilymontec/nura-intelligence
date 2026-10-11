import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../../contexts/AuthContext";
import {
  Upload,
  Search,
  FolderOpen,
  FileSpreadsheet,
  FileJson,
  FileText,
  Star,
  Trash2,
  Pencil,
  Download,
  MoreVertical,
  X,
  Check,
  FolderPlus,
  Filter,
  ArrowUpDown,
  Grid3X3,
  List,
  AlertTriangle,
  Eye,
  Copy,
  Tag,
  Archive,
  RefreshCw,
  GitBranch,
  Merge,
  Play,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "";

// Módulo 2 — subida en partes para archivos grandes. Por debajo del umbral
// se sube en un solo POST (como antes); por encima, el archivo se parte en
// pedazos de 5MB y se van mandando uno por uno al endpoint de chunks.
const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
const CHUNK_THRESHOLD = 10 * 1024 * 1024; // 10MB

function makeUploadId() {
  return `u${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

async function uploadFileInChunks(file, headers, onProgress) {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  const uploadId = makeUploadId();
  let lastData = null;

  for (let index = 0; index < totalChunks; index++) {
    const start = index * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const blob = file.slice(start, end);

    const formData = new FormData();
    formData.append("upload_id", uploadId);
    formData.append("file_name", file.name);
    formData.append("chunk_index", String(index));
    formData.append("total_chunks", String(totalChunks));
    formData.append("chunk", blob, file.name);

    const res = await fetch(`${API_BASE}/datasets/upload-chunk`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || body.detail || `Error ${res.status} subiendo pedazo ${index + 1}/${totalChunks}`);
    }

    lastData = await res.json();
    if (onProgress) onProgress(Math.round(((index + 1) / totalChunks) * 100));
  }

  return lastData;
}

const FILE_ICONS = {
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  json: FileJson,
};

const STATUS_STYLES = {
  valid: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  invalid: "bg-red-500/10 text-red-400 border-red-500/20",
  pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  processing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

function formatSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + " " + units[i];
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}

function getAuthHeaders(tokenFn) {
  return async () => {
    let t = localStorage.getItem("accessToken");
    if (!t) return {};
    try {
      const p = JSON.parse(atob(t.split(".")[1]));
      if (Date.now() >= p.exp * 1000) t = await tokenFn();
    } catch {
      t = await tokenFn();
    }
    return t ? { Authorization: `Bearer ${t}` } : {};
  };
}

function MetadataModal({ dataset, onClose }) {
  if (!dataset) return null;
  const FileIcon = FILE_ICONS[dataset.file_type] || FileText;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-nura-gray border border-nura-border rounded-2xl w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-white font-medium text-sm">Metadata del Archivo</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <FileIcon className="w-8 h-8 text-nura-electric/60" />
          <div>
            <div className="text-white text-sm font-medium">{dataset.file_name}</div>
            <div className="text-white/40 text-[11px]">{dataset.original_name}</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 text-[11px]">
          {[
            ["Nombre", dataset.file_name],
            ["Tamaño", formatSize(dataset.file_size)],
            ["Tipo", dataset.file_type?.toUpperCase()],
            ["Fecha", formatDate(dataset.uploaded_at)],
            ["Autor", dataset.uploaded_by?.email || "—"],
            ["Hash", dataset.file_hash?.slice(0, 16) + "..."],
            ["Estado", dataset.status?.toUpperCase()],
            ["Estrellas", dataset.starred ? "Sí" : "No"],
            ["Versión", `v${dataset.version || 1}`],
            ["Archivado", dataset.archived ? "Sí" : "No"],
          ].map(([label, val]) => (
            <div key={label} className="space-y-0.5">
              <div className="text-white/30 uppercase tracking-wider text-[9px]">{label}</div>
              <div className="text-white/70 truncate" title={val}>{val}</div>
            </div>
          ))}
        </div>
        {dataset.tags?.length > 0 && (
          <div className="space-y-1">
            <div className="text-white/30 uppercase tracking-wider text-[9px]">Tags</div>
            <div className="flex flex-wrap gap-1">
              {dataset.tags.map((t, i) => (
                <span key={i} className="px-2 py-0.5 rounded bg-nura-electric/10 text-nura-electric text-[10px] border border-nura-electric/20">{t}</span>
              ))}
            </div>
          </div>
        )}
        {dataset.description && (
          <div className="space-y-1">
            <div className="text-white/30 uppercase tracking-wider text-[9px]">Descripción</div>
            <div className="text-white/60 text-[11px]">{dataset.description}</div>
          </div>
        )}
        {dataset.validation_errors?.length > 0 && (
          <div className="p-2 rounded bg-red-500/5 border border-red-500/20 text-red-400 text-[10px]">
            <AlertTriangle className="w-3 h-3 inline mr-1" />
            {dataset.validation_errors.join(", ")}
          </div>
        )}
      </div>
    </div>
  );
}

function CategoryModal({ categories, onAdd, onDelete, onClose }) {
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState("#6366f1");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (newName.trim()) {
      onAdd(newName.trim(), newColor);
      setNewName("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-nura-gray border border-nura-border rounded-2xl w-full max-w-md p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-white font-medium text-sm">Categorías</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="color"
            value={newColor}
            onChange={(e) => setNewColor(e.target.value)}
            className="w-8 h-8 rounded cursor-pointer border-0 bg-transparent"
          />
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nueva categoría..."
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-nura-electric/40"
          />
          <button type="submit" className="px-3 py-1.5 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric text-xs hover:bg-nura-electric/30">
            <FolderPlus className="w-3.5 h-3.5" />
          </button>
        </form>
        <div className="space-y-1 max-h-48 overflow-y-auto scrollbar-thin">
          {categories.length === 0 && (
            <div className="text-white/30 text-[11px] text-center py-4">No hay categorías</div>
          )}
          {categories.map((cat) => (
            <div key={cat.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/[0.03] group">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }} />
                <span className="text-white/70 text-xs">{cat.name}</span>
                <span className="text-white/30 text-[10px]">({cat.dataset_count})</span>
              </div>
              <button
                onClick={() => onDelete(cat.id)}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-opacity"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function FileManager() {
  const { refreshAccessToken } = useAuth();
  const getHeaders = useCallback(getAuthHeaders(refreshAccessToken), [refreshAccessToken]);

  const [datasets, setDatasets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});

  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterStarred, setFilterStarred] = useState(false);
  const [sortBy, setSortBy] = useState("-uploaded_at");
  const [viewMode, setViewMode] = useState("list");

  const [selectedIds, setSelectedIds] = useState(new Set());
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");

  const [showMetadata, setShowMetadata] = useState(null);
  const [showCategories, setShowCategories] = useState(false);
  const [showMerge, setShowMerge] = useState(false);
  const [showVersions, setShowVersions] = useState(null);
  const [showExplore, setShowExplore] = useState(null);
  const [showTagManager, setShowTagManager] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [archivedFilter, setArchivedFilter] = useState(false);

  const fileInputRef = useRef(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = await getHeaders();
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (filterType) params.set("type", filterType);
      if (filterStatus) params.set("status", filterStatus);
      if (filterCategory) params.set("category", filterCategory);
      if (filterStarred) params.set("starred", "true");
      if (archivedFilter) params.set("archived", "true");
      params.set("sort", sortBy);

      const [dsRes, catRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/datasets?${params}`, { headers }),
        fetch(`${API_BASE}/categories`, { headers }),
        fetch(`${API_BASE}/datasets/stats`, { headers }),
      ]);

      if (dsRes.ok) setDatasets(await dsRes.json());
      if (catRes.ok) setCategories(await catRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (e) {
      console.error("Error fetching data:", e);
    } finally {
      setLoading(false);
    }
  }, [search, filterType, filterStatus, filterCategory, filterStarred, archivedFilter, sortBy, getHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleUpload = async (files) => {
    if (!files?.length) return;
    setUploading(true);
    setUploadError(null);
    setUploadProgress({});
    const errors = [];
    try {
      const headers = await getHeaders();
      for (const file of files) {
        try {
          if (file.size > CHUNK_THRESHOLD) {
            // Archivo grande: subida en partes, con progreso por archivo.
            setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
            await uploadFileInChunks(file, headers, (pct) => {
              setUploadProgress((prev) => ({ ...prev, [file.name]: pct }));
            });
          } else {
            const formData = new FormData();
            formData.append("file", file);
            const res = await fetch(`${API_BASE}/datasets`, { method: "POST", headers, body: formData });
            if (!res.ok) {
              const body = await res.json().catch(() => ({}));
              const msg = body.error || body.detail || `Error ${res.status}`;
              errors.push(`${file.name}: ${msg}`);
            }
          }
        } catch (err) {
          errors.push(`${file.name}: ${err.message || "Error de red"}`);
        }
      }
      if (errors.length > 0) {
        setUploadError(errors.join("\n"));
      }
      fetchData();
    } catch (e) {
      console.error("Upload error:", e);
      setUploadError("Error inesperado al subir archivos");
    } finally {
      setUploading(false);
      setUploadProgress({});
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  const handleDelete = async (id) => {
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/datasets/${id}`, { method: "DELETE", headers });
      fetchData();
    } catch (e) {
      console.error("Delete error:", e);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`¿Eliminar ${selectedIds.size} archivo(s)?`)) return;
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE}/datasets/bulk-delete`, {
        method: "POST",
        headers,
        body: JSON.stringify({ ids: [...selectedIds] }),
      });
      setSelectedIds(new Set());
      fetchData();
    } catch (e) {
      console.error("Bulk delete error:", e);
    }
  };

  const handleRename = async (id) => {
    if (!editName.trim()) return;
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE}/datasets/${id}/rename`, {
        method: "POST",
        headers,
        body: JSON.stringify({ file_name: editName.trim() }),
      });
      setEditingId(null);
      fetchData();
    } catch (e) {
      console.error("Rename error:", e);
    }
  };

  const handleStar = async (id) => {
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/datasets/${id}/star`, { method: "POST", headers });
      fetchData();
    } catch (e) {
      console.error("Star error:", e);
    }
  };

  const handleMove = async (id, categoryId) => {
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE}/datasets/${id}/move`, {
        method: "POST",
        headers,
        body: JSON.stringify({ category_id: categoryId || null }),
      });
      fetchData();
    } catch (e) {
      console.error("Move error:", e);
    }
  };

  const handleAddCategory = async (name, color) => {
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE}/categories`, {
        method: "POST",
        headers,
        body: JSON.stringify({ name, color }),
      });
      fetchData();
    } catch (e) {
      console.error("Add category error:", e);
    }
  };

  const handleDeleteCategory = async (id) => {
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/categories/${id}`, { method: "DELETE", headers });
      fetchData();
    } catch (e) {
      console.error("Delete category error:", e);
    }
  };

  const handleDuplicate = async (id) => {
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE}/datasets/${id}/duplicate`, { method: "POST", headers, body: JSON.stringify({}) });
      fetchData();
    } catch (e) {
      console.error("Duplicate error:", e);
    }
  };

  const handleArchive = async (id) => {
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/datasets/${id}/archive`, { method: "POST", headers });
      fetchData();
    } catch (e) {
      console.error("Archive error:", e);
    }
  };

  const handleReanalyze = async (id) => {
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/datasets/${id}/reanalyze`, { method: "POST", headers });
      fetchData();
    } catch (e) {
      console.error("Reanalyze error:", e);
    }
  };

  const handleCreateVersion = async (id) => {
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      const note = window.prompt("Nota para esta versión (opcional):") || "";
      await fetch(`${API_BASE}/datasets/${id}/versions`, {
        method: "POST", headers, body: JSON.stringify({ note }),
      });
      fetchData();
    } catch (e) {
      console.error("Create version error:", e);
    }
  };

  const handleRestoreVersion = async (datasetId, versionId) => {
    try {
      const headers = await getHeaders();
      await fetch(`${API_BASE}/datasets/${datasetId}/versions/${versionId}/restore`, { method: "POST", headers });
      setShowVersions(null);
      fetchData();
    } catch (e) {
      console.error("Restore version error:", e);
    }
  };

  const handleAddTag = async (id, tagName) => {
    if (!tagName.trim()) return;
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE}/datasets/${id}/tags/add`, {
        method: "POST", headers, body: JSON.stringify({ tags: [tagName.trim()] }),
      });
      fetchData();
    } catch (e) {
      console.error("Add tag error:", e);
    }
  };

  const handleRemoveTag = async (id, tagName) => {
    try {
      const headers = await getHeaders();
      headers["Content-Type"] = "application/json";
      await fetch(`${API_BASE}/datasets/${id}/tags/remove`, {
        method: "POST", headers, body: JSON.stringify({ tags: [tagName] }),
      });
      fetchData();
    } catch (e) {
      console.error("Remove tag error:", e);
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === datasets.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(datasets.map((d) => d.id)));
    }
  };

  return (
    <div className="h-full flex flex-col font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="space-y-0.5">
          <h2 className="text-lg text-white font-light flex items-center gap-2">
            // gestion_archivos
          </h2>
          <p className="text-white/30 text-[10px]">Subir, renombrar, eliminar, buscar, filtrar y organizar archivos.</p>
        </div>
        <div className="flex items-center gap-2">
          {stats && (
            <div className="flex items-center gap-3 text-[10px] text-white/30 mr-2">
              <span>{stats.total} archivos</span>
              <span>{formatSize(stats.total_size)}</span>
              {stats.starred > 0 && <span className="text-yellow-400">{stats.starred} favoritos</span>}
            </div>
          )}
          <button
            onClick={() => setShowMerge(true)}
            className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white transition-all text-[11px] flex items-center gap-1.5"
          >
            <Merge className="w-3.5 h-3.5" /> Fusionar
          </button>
          <button
            onClick={() => setShowCategories(true)}
            className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white transition-all text-[11px] flex items-center gap-1.5"
          >
            <FolderOpen className="w-3.5 h-3.5" /> Categorías
          </button>
          <div className="flex rounded-lg border border-white/10 overflow-hidden">
            <button
              onClick={() => setViewMode("list")}
              className={`px-2 py-1.5 ${viewMode === "list" ? "bg-white/10 text-white" : "text-white/40 hover:text-white/60"}`}
            >
              <List className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode("grid")}
              className={`px-2 py-1.5 ${viewMode === "grid" ? "bg-white/10 text-white" : "text-white/40 hover:text-white/60"}`}
            >
              <Grid3X3 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar archivos..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/80 text-xs focus:outline-none focus:border-nura-electric/40"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/70 text-xs focus:outline-none cursor-pointer"
        >
          <option value="">Todos los tipos</option>
          <option value="csv">CSV</option>
          <option value="xlsx">Excel</option>
          <option value="json">JSON</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/70 text-xs focus:outline-none cursor-pointer"
        >
          <option value="">Todos los estados</option>
          <option value="valid">Válido</option>
          <option value="invalid">Inválido</option>
          <option value="pending">Pendiente</option>
        </select>
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/70 text-xs focus:outline-none cursor-pointer"
        >
          <option value="">Todas las categorías</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <button
          onClick={() => setFilterStarred(!filterStarred)}
          className={`px-2.5 py-1.5 rounded-lg border text-xs flex items-center gap-1 transition-all ${
            filterStarred
              ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-400"
              : "bg-white/5 border-white/10 text-white/50 hover:text-white/70"
          }`}
        >
          <Star className="w-3 h-3" fill={filterStarred ? "currentColor" : "none"} />
        </button>
        <button
          onClick={() => setArchivedFilter(!archivedFilter)}
          className={`px-2.5 py-1.5 rounded-lg border text-xs flex items-center gap-1 transition-all ${
            archivedFilter
              ? "bg-orange-500/10 border-orange-500/30 text-orange-400"
              : "bg-white/5 border-white/10 text-white/50 hover:text-white/70"
          }`}
        >
          <Archive className="w-3 h-3" />
        </button>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/70 text-xs focus:outline-none cursor-pointer"
        >
          <option value="-uploaded_at">Más recientes</option>
          <option value="uploaded_at">Más antiguos</option>
          <option value="file_name">Nombre A-Z</option>
          <option value="-file_name">Nombre Z-A</option>
          <option value="-file_size">Mayor tamaño</option>
          <option value="file_size">Menor tamaño</option>
        </select>
      </div>

      {/* Bulk actions */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 p-2 mb-3 rounded-lg bg-nura-electric/5 border border-nura-electric/20">
          <span className="text-nura-electric text-[11px]">{selectedIds.size} seleccionado(s)</span>
          <button onClick={toggleSelectAll} className="text-[10px] text-white/40 hover:text-white/60">
            {selectedIds.size === datasets.length ? "Deseleccionar todo" : "Seleccionar todo"}
          </button>
          <button
            onClick={handleBulkDelete}
            className="px-3 py-1 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-[11px] hover:bg-red-500/20 flex items-center gap-1"
          >
            <Trash2 className="w-3 h-3" /> Eliminar
          </button>
          <button onClick={() => setSelectedIds(new Set())} className="text-white/40 hover:text-white/60 ml-auto">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Upload zone */}
      <div
        className={`border-2 border-dashed rounded-xl transition-colors cursor-pointer mb-4 ${
          dragOver
            ? "border-nura-electric bg-nura-electric/5"
            : "border-nura-border bg-nura-gray/30 hover:border-nura-electric/40"
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.json"
          multiple
          className="hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
        <div className="flex flex-col items-center gap-2 py-6">
          <Upload className={`w-6 h-6 transition-colors ${dragOver ? "text-nura-electric" : "text-white/20"}`} />
          <p className="text-white/40 text-center text-xs">
            {uploading ? "Subiendo archivos..." : "Arrastra archivos aquí o haz clic para examinar"}
          </p>
          <p className="text-white/20 text-[10px]">CSV, XLSX, JSON — máx. 50MB por archivo</p>
        </div>
      </div>
      {Object.keys(uploadProgress).length > 0 && (
        <div className="mb-3 space-y-1.5">
          {Object.entries(uploadProgress).map(([name, pct]) => (
            <div key={name} className="text-[11px]">
              <div className="flex justify-between text-white/40 mb-0.5">
                <span className="truncate max-w-[70%]">{name}</span>
                <span>{pct}%</span>
              </div>
              <div className="h-1 rounded-full bg-nura-gray/50 overflow-hidden">
                <div
                  className="h-full bg-nura-electric transition-all duration-150"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
      {uploadError && (
        <div className="mb-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-[11px] flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-none" />
          <div className="whitespace-pre-wrap">{uploadError}</div>
          <button onClick={() => setUploadError(null)} className="ml-auto text-red-400 hover:text-red-300 flex-none"><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* File list */}
      <div className="flex-1 overflow-y-auto min-h-0 scrollbar-thin">
        {loading ? (
          <div className="text-white/40 text-center py-8">Cargando archivos...</div>
        ) : datasets.length === 0 ? (
          <div className="text-white/30 text-center py-12 space-y-2">
            <FolderOpen className="w-10 h-10 mx-auto text-white/10" />
            <p className="text-xs">No hay archivos. Sube tu primer dataset.</p>
          </div>
        ) : viewMode === "list" ? (
          <div className="space-y-1">
            {/* List header */}
            <div className="grid grid-cols-[32px_1fr_80px_80px_100px_100px_40px] gap-2 px-3 py-1.5 text-[9px] text-white/30 uppercase tracking-wider border-b border-nura-border">
              <div></div>
              <div>Nombre</div>
              <div>Tipo</div>
              <div>Tamaño</div>
              <div>Fecha</div>
              <div>Estado</div>
              <div></div>
            </div>
            {datasets.map((ds) => {
              const FileIcon = FILE_ICONS[ds.file_type] || FileText;
              const isEditing = editingId === ds.id;
              return (
                <div
                  key={ds.id}
                  className={`grid grid-cols-[32px_1fr_80px_80px_100px_100px_40px] gap-2 items-center px-3 py-2.5 rounded-lg transition-colors group ${
                    selectedIds.has(ds.id) ? "bg-nura-electric/5 border border-nura-electric/20" : "hover:bg-white/[0.02] border border-transparent"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(ds.id)}
                    onChange={() => toggleSelect(ds.id)}
                    className="w-3.5 h-3.5 rounded border-white/20 bg-white/5 accent-nura-electric cursor-pointer"
                  />
                  <div className="flex items-center gap-2 min-w-0">
                    <FileIcon className="w-4 h-4 text-nura-electric/50 flex-none" />
                    {isEditing ? (
                      <div className="flex items-center gap-1 flex-1">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleRename(ds.id)}
                          className="flex-1 bg-white/5 border border-nura-electric/40 rounded px-2 py-0.5 text-white text-xs focus:outline-none"
                          autoFocus
                        />
                        <button onClick={() => handleRename(ds.id)} className="text-emerald-400 hover:text-emerald-300"><Check className="w-3 h-3" /></button>
                        <button onClick={() => setEditingId(null)} className="text-white/40 hover:text-white/60"><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <span className="text-white/80 text-xs truncate">{ds.file_name}</span>
                    )}
                    {ds.category_detail && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] border flex-none" style={{ borderColor: ds.category_detail.color + "40", color: ds.category_detail.color, backgroundColor: ds.category_detail.color + "10" }}>
                        {ds.category_detail.name}
                      </span>
                    )}
                  </div>
                  <div className="text-white/40 text-[10px]">{ds.file_type?.toUpperCase()}</div>
                  <div className="text-white/40 text-[10px]">{formatSize(ds.file_size)}</div>
                  <div className="text-white/40 text-[10px]">{formatDate(ds.uploaded_at)}</div>
                  <div>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border ${STATUS_STYLES[ds.status] || STATUS_STYLES.pending}`}>
                      {ds.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => handleStar(ds.id)} className={`p-1 rounded hover:bg-white/5 ${ds.starred ? "text-yellow-400" : "text-white/30 hover:text-yellow-400"}`}>
                      <Star className="w-3 h-3" fill={ds.starred ? "currentColor" : "none"} />
                    </button>
                    <button onClick={() => { setEditingId(ds.id); setEditName(ds.file_name); }} className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60">
                      <Pencil className="w-3 h-3" />
                    </button>
                    <button onClick={() => handleDuplicate(ds.id)} className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60" title="Duplicar">
                      <Copy className="w-3 h-3" />
                    </button>
                    <button onClick={() => handleArchive(ds.id)} className={`p-1 rounded hover:bg-white/5 ${ds.archived ? "text-orange-400" : "text-white/30 hover:text-orange-400"}`} title={ds.archived ? "Desarchivar" : "Archivar"}>
                      <Archive className="w-3 h-3" />
                    </button>
                    {ds.file_type === 'csv' || ds.file_type === 'xlsx' ? (
                      <button onClick={() => handleReanalyze(ds.id)} className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-emerald-400" title="Re-analizar">
                        <RefreshCw className="w-3 h-3" />
                      </button>
                    ) : null}
                    <button onClick={() => handleCreateVersion(ds.id)} className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60" title="Crear versión">
                      <GitBranch className="w-3 h-3" />
                    </button>
                    <button onClick={() => setShowVersions(ds)} className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60" title="Ver versiones">
                      <GitBranch className="w-3 h-3" />
                    </button>
                    <button onClick={() => setShowExplore(ds)} className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60" title="Explorar">
                      <Eye className="w-3 h-3" />
                    </button>
                    <button onClick={() => setShowTagManager(ds)} className={`p-1 rounded hover:bg-white/5 ${ds.tags?.length > 0 ? "text-nura-electric" : "text-white/30 hover:text-nura-electric"}`} title="Etiquetas">
                      <Tag className="w-3 h-3" />
                    </button>
                    <a href={`${API_BASE}/datasets/${ds.id}/download/`} className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60" title="Descargar" onClick={(e) => e.stopPropagation()}>
                      <Download className="w-3 h-3" />
                    </a>
                    <div className="relative group/cat">
                      <button className="p-1 rounded hover:bg-white/5 text-white/30 hover:text-white/60">
                        <FolderOpen className="w-3 h-3" />
                      </button>
                      <div className="absolute right-0 top-full mt-1 bg-nura-gray border border-nura-border rounded-lg p-1.5 hidden group-hover/cat:block z-10 min-w-[140px] shadow-xl">
                        <button
                          onClick={() => handleMove(ds.id, null)}
                          className="w-full text-left px-2 py-1 text-[10px] text-white/50 hover:bg-white/5 hover:text-white/70 rounded"
                        >
                          Sin categoría
                        </button>
                        {categories.map((c) => (
                          <button
                            key={c.id}
                            onClick={() => handleMove(ds.id, c.id)}
                            className="w-full text-left px-2 py-1 text-[10px] text-white/50 hover:bg-white/5 hover:text-white/70 rounded flex items-center gap-1.5"
                          >
                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }} />
                            {c.name}
                          </button>
                        ))}
                      </div>
                    </div>
                    <button onClick={() => handleDelete(ds.id)} className="p-1 rounded hover:bg-red-500/10 text-white/30 hover:text-red-400">
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Grid view */
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {datasets.map((ds) => {
              const FileIcon = FILE_ICONS[ds.file_type] || FileText;
              return (
                <div
                  key={ds.id}
                  className={`pure-glass rounded-xl p-4 space-y-3 group relative ${
                    selectedIds.has(ds.id) ? "ring-1 ring-nura-electric/40" : ""
                  }`}
                >
                  <div className="absolute top-3 left-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(ds.id)}
                      onChange={() => toggleSelect(ds.id)}
                      className="w-3 h-3 rounded border-white/20 bg-white/5 accent-nura-electric cursor-pointer"
                    />
                  </div>
                  <button
                    onClick={() => handleStar(ds.id)}
                    className={`absolute top-3 right-3 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${
                      ds.starred ? "text-yellow-400 opacity-100" : "text-white/30 hover:text-yellow-400"
                    }`}
                  >
                    <Star className="w-3 h-3" fill={ds.starred ? "currentColor" : "none"} />
                  </button>
                  <div className="flex items-center justify-center pt-2">
                    <FileIcon className="w-10 h-10 text-nura-electric/40" />
                  </div>
                  <div className="space-y-1">
                    <div className="text-white/80 text-xs font-medium truncate">{ds.file_name}</div>
                    <div className="flex items-center gap-2 text-[10px] text-white/30">
                      <span>{ds.file_type?.toUpperCase()}</span>
                      <span>{formatSize(ds.file_size)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded border ${STATUS_STYLES[ds.status] || STATUS_STYLES.pending}`}>
                        {ds.status?.toUpperCase()}
                      </span>
                      {ds.category_detail && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] border" style={{ borderColor: ds.category_detail.color + "40", color: ds.category_detail.color, backgroundColor: ds.category_detail.color + "10" }}>
                          {ds.category_detail.name}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-center gap-1 pt-1 border-t border-nura-border opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => { setEditingId(ds.id); setEditName(ds.file_name); }} className="p-1.5 rounded hover:bg-white/5 text-white/30 hover:text-white/60"><Pencil className="w-3 h-3" /></button>
                    <button onClick={() => handleDuplicate(ds.id)} className="p-1.5 rounded hover:bg-white/5 text-white/30 hover:text-white/60" title="Duplicar"><Copy className="w-3 h-3" /></button>
                    <button onClick={() => handleArchive(ds.id)} className={`p-1.5 rounded hover:bg-white/5 ${ds.archived ? "text-orange-400" : "text-white/30 hover:text-orange-400"}`} title="Archivar"><Archive className="w-3 h-3" /></button>
                    <button onClick={() => setShowExplore(ds)} className="p-1.5 rounded hover:bg-white/5 text-white/30 hover:text-white/60" title="Explorar"><Eye className="w-3 h-3" /></button>
                    <a href={`${API_BASE}/datasets/${ds.id}/download/`} className="p-1.5 rounded hover:bg-white/5 text-white/30 hover:text-white/60" onClick={(e) => e.stopPropagation()}><Download className="w-3 h-3" /></a>
                    <button onClick={() => handleDelete(ds.id)} className="p-1.5 rounded hover:bg-red-500/10 text-white/30 hover:text-red-400"><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modals */}
      {showMetadata && <MetadataModal dataset={showMetadata} onClose={() => setShowMetadata(null)} />}
      {showCategories && (
        <CategoryModal
          categories={categories}
          onAdd={handleAddCategory}
          onDelete={handleDeleteCategory}
          onClose={() => setShowCategories(false)}
        />
      )}
      {showMerge && (
        <MergeModal
          datasets={datasets}
          onMerge={async (ids, name, type, joinCol) => {
            try {
              const headers = await getHeaders();
              headers["Content-Type"] = "application/json";
              const res = await fetch(`${API_BASE}/datasets/merge`, {
                method: "POST", headers,
                body: JSON.stringify({ dataset_ids: ids, file_name: name, type, join_column: joinCol }),
              });
              if (res.ok) fetchData();
            } catch (e) { console.error("Merge error:", e); }
          }}
          onClose={() => setShowMerge(false)}
        />
      )}
      {showVersions && (
        <VersionModal
          dataset={showVersions}
          onRestore={handleRestoreVersion}
          onClose={() => setShowVersions(null)}
          getHeaders={getHeaders}
        />
      )}
      {showExplore && (
        <ExploreModal dataset={showExplore} onClose={() => setShowExplore(null)} getHeaders={getHeaders} />
      )}
      {showTagManager && (
        <TagManagerModal
          dataset={showTagManager}
          onAdd={(name) => handleAddTag(showTagManager.id, name)}
          onRemove={(name) => handleRemoveTag(showTagManager.id, name)}
          onClose={() => setShowTagManager(null)}
        />
      )}
    </div>
  );
}

function MergeModal({ datasets, onMerge, onClose }) {
  const [selected, setSelected] = useState([]);
  const [name, setName] = useState("Dataset fusionado");
  const [type, setType] = useState("concat");
  const [joinCol, setJoinCol] = useState("");

  const toggle = (id) => {
    setSelected((prev) => prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-nura-gray border border-nura-border rounded-2xl w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-white font-medium text-sm flex items-center gap-2"><Merge className="w-4 h-4" /> Fusionar Datasets</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto scrollbar-thin">
          {datasets.filter(d => !d.archived).map((ds) => (
            <label key={ds.id} className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${selected.includes(ds.id) ? "bg-nura-electric/10 border border-nura-electric/30" : "hover:bg-white/[0.03] border border-transparent"}`}>
              <input type="checkbox" checked={selected.includes(ds.id)} onChange={() => toggle(ds.id)} className="w-3.5 h-3.5 rounded border-white/20 bg-white/5 accent-nura-electric" />
              <span className="text-white/70 text-xs">{ds.file_name}</span>
              <span className="text-white/30 text-[10px] ml-auto">{ds.file_type?.toUpperCase()}</span>
            </label>
          ))}
        </div>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre del dataset fusionado" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-nura-electric/40" />
        <select value={type} onChange={(e) => setType(e.target.value)} className="w-full px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/70 text-xs focus:outline-none cursor-pointer">
          <option value="concat">Concatenar (uno debajo del otro)</option>
          <option value="join">Unir por columna (left join)</option>
        </select>
        {type === "join" && (
          <input type="text" value={joinCol} onChange={(e) => setJoinCol(e.target.value)} placeholder="Nombre de la columna para unir" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-nura-electric/40" />
        )}
        <button onClick={() => { if (selected.length >= 2) { onMerge(selected, name, type, joinCol); onClose(); } }} disabled={selected.length < 2} className={`w-full py-2 rounded-lg text-xs font-medium transition-all ${selected.length >= 2 ? "bg-nura-electric text-white hover:bg-nura-electric/80" : "bg-white/5 text-white/30 cursor-not-allowed"}`}>
          Fusionar {selected.length} datasets
        </button>
      </div>
    </div>
  );
}

function VersionModal({ dataset, onRestore, onClose, getHeaders }) {
  const [versions, setVersions] = useState([]);
  useEffect(() => {
    getHeaders().then((h) => {
      fetch(`${API_BASE}/datasets/${dataset.id}/versions`, { headers: h })
        .then((r) => r.json()).then(setVersions).catch(() => {});
    });
  }, [dataset.id, getHeaders]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-nura-gray border border-nura-border rounded-2xl w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-white font-medium text-sm flex items-center gap-2"><GitBranch className="w-4 h-4" /> Versiones — {dataset.file_name}</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
          {versions.length === 0 && <div className="text-white/30 text-center text-xs py-4">No hay versiones guardadas</div>}
          {versions.map((v) => (
            <div key={v.id} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
              <div>
                <div className="text-white/70 text-xs">v{v.version_number} — {v.file_name}</div>
                <div className="text-white/30 text-[10px]">{new Date(v.created_at).toLocaleString("es-ES")}{v.note ? ` — ${v.note}` : ""}</div>
              </div>
              <button onClick={() => { onRestore(dataset.id, v.id); }} className="px-2 py-1 rounded bg-nura-electric/20 text-nura-electric text-[10px] hover:bg-nura-electric/30">
                Restaurar
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ExploreModal({ dataset, onClose, getHeaders }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    getHeaders().then((h) => {
      fetch(`${API_BASE}/datasets/${dataset.id}/explore`, { headers: h })
        .then((r) => r.json()).then(setData).catch(() => {});
    });
  }, [dataset.id, getHeaders]);

  if (!data) return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-nura-gray border border-nura-border rounded-2xl w-full max-w-3xl p-6 text-center text-white/40 text-xs" onClick={(e) => e.stopPropagation()}>Cargando...</div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-nura-gray border border-nura-border rounded-2xl w-full max-w-4xl max-h-[80vh] overflow-y-auto p-6 space-y-4 scrollbar-thin" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-white font-medium text-sm">Explorar — {dataset.file_name}</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        {data.summary && (
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(data.summary).map(([k, v]) => (
              <div key={k} className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                <div className="text-white/30 text-[9px] uppercase">{k}</div>
                <div className="text-white/70 text-xs">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</div>
              </div>
            ))}
          </div>
        )}
        {data.preview?.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-nura-border">
                  {Object.keys(data.preview[0]).map((col) => (
                    <th key={col} className="text-left text-white/30 uppercase px-2 py-1 font-normal">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.preview.map((row, i) => (
                  <tr key={i} className="border-b border-white/[0.03]">
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="text-white/60 px-2 py-1">{val === null ? "—" : String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data.columns?.length > 0 && (
          <div className="space-y-1">
            <div className="text-white/30 text-[9px] uppercase">Columnas ({data.columns.length})</div>
            <div className="grid grid-cols-3 gap-1">
              {data.columns.map((c, i) => (
                <div key={i} className="text-white/50 text-[10px] p-1 rounded bg-white/[0.02]">
                  {c.name || c} {c.dtype ? `(${c.dtype})` : ""}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TagManagerModal({ dataset, onAdd, onRemove, onClose }) {
  const [newTag, setNewTag] = useState("");
  const tags = dataset?.tags || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-nura-gray border border-nura-border rounded-2xl w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-white font-medium text-sm flex items-center gap-2"><Tag className="w-4 h-4" /> Etiquetas</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); onAdd(newTag); setNewTag(""); }} className="flex gap-2">
          <input type="text" value={newTag} onChange={(e) => setNewTag(e.target.value)} placeholder="Nueva etiqueta..." className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-nura-electric/40" />
          <button type="submit" className="px-3 py-1.5 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric text-xs hover:bg-nura-electric/30">+</button>
        </form>
        <div className="flex flex-wrap gap-1.5">
          {tags.length === 0 && <div className="text-white/30 text-[11px] text-center py-4 w-full">Sin etiquetas</div>}
          {tags.map((t, i) => (
            <span key={i} className="flex items-center gap-1 px-2 py-0.5 rounded bg-nura-electric/10 text-nura-electric text-[11px] border border-nura-electric/20">
              {t}
              <button onClick={() => onRemove(t)} className="hover:text-white/60"><X className="w-2.5 h-2.5" /></button>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
