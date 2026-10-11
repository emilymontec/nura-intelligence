import { useEffect, useRef } from "react";

// Heatmap de correlación dibujado directamente sobre un <canvas> (en vez de
// un plugin extra de Chart.js) para que la exportación PNG/SVG funcione
// igual que con el resto de gráficos (ver utils/chartExport.js).
function correlationColor(value) {
  // -1 → rojo, 0 → gris oscuro neutro, 1 → azul eléctrico (paleta de la app)
  const clamped = Math.max(-1, Math.min(1, value));
  if (clamped >= 0) {
    const t = clamped;
    const r = Math.round(30 + (79 - 30) * t);
    const g = Math.round(30 + (123 - 30) * t);
    const b = Math.round(40 + (255 - 40) * t);
    return `rgb(${r}, ${g}, ${b})`;
  }
  const t = -clamped;
  const r = Math.round(30 + (220 - 30) * t);
  const g = Math.round(30 + (38 - 30) * t);
  const b = Math.round(40 + (38 - 40) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

export default function HeatmapChart({ labels, cells, canvasRef }) {
  const internalRef = useRef(null);
  const ref = canvasRef || internalRef;

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas || !labels?.length) return;

    const dpr = window.devicePixelRatio || 1;
    const padding = 110;
    const cellSize = 48;
    const size = labels.length * cellSize + padding;

    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, size, size);
    ctx.fillStyle = "#0a0a0f";
    ctx.fillRect(0, 0, size, size);

    const cellMap = {};
    for (const c of cells) {
      cellMap[`${c.row}|${c.col}`] = c.value;
    }

    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    labels.forEach((rowLabel, i) => {
      labels.forEach((colLabel, j) => {
        const value = cellMap[`${rowLabel}|${colLabel}`] ?? 0;
        const x = padding + j * cellSize;
        const y = padding + i * cellSize;

        ctx.fillStyle = correlationColor(value);
        ctx.fillRect(x, y, cellSize - 2, cellSize - 2);

        ctx.fillStyle = Math.abs(value) > 0.55 ? "#0a0a0f" : "#e5e5e5";
        ctx.font = "11px 'IBM Plex Mono', monospace";
        ctx.fillText(value.toFixed(2), x + cellSize / 2, y + cellSize / 2);
      });

      // Etiqueta de fila
      ctx.fillStyle = "#cccccc";
      ctx.font = "11px 'IBM Plex Mono', monospace";
      ctx.textAlign = "right";
      ctx.fillText(rowLabel.slice(0, 14), padding - 10, padding + i * cellSize + cellSize / 2);
      ctx.textAlign = "center";
    });

    // Etiquetas de columna (rotadas)
    labels.forEach((colLabel, j) => {
      const x = padding + j * cellSize + cellSize / 2;
      ctx.save();
      ctx.translate(x, padding - 14);
      ctx.rotate(-Math.PI / 5);
      ctx.fillStyle = "#cccccc";
      ctx.font = "11px 'IBM Plex Mono', monospace";
      ctx.textAlign = "left";
      ctx.fillText(colLabel.slice(0, 14), 0, 0);
      ctx.restore();
    });
  }, [labels, cells, ref]);

  return (
    <div style={{ overflowX: "auto" }}>
      <canvas ref={ref} />
    </div>
  );
}
