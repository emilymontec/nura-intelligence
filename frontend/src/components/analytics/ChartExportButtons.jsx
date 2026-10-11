import { Download } from "lucide-react";
import { exportCanvasAsPNG, exportCanvasAsSVG } from "../../utils/chartExport";

// Botones pequeños de exportación que se superponen en la esquina de cada
// chart-card. `getCanvas` devuelve el <canvas> real en el momento del click
// (no se guarda una referencia vieja), para soportar tanto gráficos de
// Chart.js (vía chartRef.current.canvas) como el heatmap dibujado a mano.
export default function ChartExportButtons({ getCanvas, name }) {
  const handleExport = (format) => {
    const canvas = getCanvas?.();
    if (!canvas) return;
    if (format === "png") exportCanvasAsPNG(canvas, name);
    else exportCanvasAsSVG(canvas, name);
  };

  return (
    <div className="chart-export-buttons" style={{ display: "flex", gap: "4px" }}>
      <button
        type="button"
        onClick={() => handleExport("png")}
        title="Exportar como PNG"
        className="chart-export-btn"
        style={{
          display: "flex", alignItems: "center", gap: "3px", fontSize: "10px",
          padding: "3px 6px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)",
          background: "rgba(255,255,255,0.04)", color: "#999", cursor: "pointer",
        }}
      >
        <Download size={10} /> PNG
      </button>
      <button
        type="button"
        onClick={() => handleExport("svg")}
        title="Exportar como SVG"
        className="chart-export-btn"
        style={{
          display: "flex", alignItems: "center", gap: "3px", fontSize: "10px",
          padding: "3px 6px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)",
          background: "rgba(255,255,255,0.04)", color: "#999", cursor: "pointer",
        }}
      >
        <Download size={10} /> SVG
      </button>
    </div>
  );
}
