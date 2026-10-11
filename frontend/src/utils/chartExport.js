// Módulo 4 — exportación de gráficos individuales a PNG/SVG.
//
// Chart.js dibuja sobre un <canvas>, así que la exportación a PNG es
// directa (canvas.toDataURL). Un <canvas> es un mapa de píxeles, no tiene
// una representación vectorial real que extraer, así que para "exportar a
// SVG" envolvemos el PNG ya renderizado dentro de un contenedor SVG válido
// (<svg><image .../></svg>): sigue siendo un archivo .svg abrible en
// cualquier visor/editor (Illustrator, Inkscape, navegadores), simplemente
// no es vectorial internamente — igual que hacen la mayoría de export de
// gráficos basados en canvas.

function triggerDownload(dataUrl, filename) {
  const link = document.createElement("a");
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function sanitizeFilename(name) {
  return (name || "grafico").toString().replace(/[^a-z0-9_-]+/gi, "_").slice(0, 80);
}

export function exportCanvasAsPNG(canvas, name) {
  if (!canvas) return;
  const dataUrl = canvas.toDataURL("image/png", 1.0);
  triggerDownload(dataUrl, `${sanitizeFilename(name)}.png`);
}

export function exportCanvasAsSVG(canvas, name) {
  if (!canvas) return;
  const width = canvas.width;
  const height = canvas.height;
  const pngDataUrl = canvas.toDataURL("image/png", 1.0);
  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <image href="${pngDataUrl}" x="0" y="0" width="${width}" height="${height}" />
</svg>`;
  const blob = new Blob([svg], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  triggerDownload(url, `${sanitizeFilename(name)}.svg`);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
