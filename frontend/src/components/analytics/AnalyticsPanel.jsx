import { useRef } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Line, Bar, Scatter } from 'react-chartjs-2';
import ChartExportButtons from './ChartExportButtons';
import HeatmapChart from './HeatmapChart';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function AnalyticsPanel({ datasetContext, onClose }) {
  const { summary, health, preview, charts, columns } = datasetContext;
  const chartRefs = useRef({});
  const heatmapCanvasRefs = useRef({});

  const renderCharts = () => {
    if (!charts || charts.length === 0) return null;

    return charts.map((chart, index) => {
      if (chart.type === 'distribution' && chart.data) {
        const data = {
          labels: chart.data.slice(0, 20).map((_, i) => `Dato ${i + 1}`),
          datasets: [
            {
              label: chart.column,
              data: chart.data.slice(0, 20),
              borderColor: '#00f2fe',
              backgroundColor: 'rgba(0, 242, 254, 0.1)',
              fill: true
            }
          ]
        };

        const options = {
          responsive: true,
          plugins: {
            legend: { position: 'top' }
          },
          scales: {
            x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#ccc' } },
            y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#ccc' } }
          }
        };

        return (
          <div key={index} className="chart-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4>{chart.column}</h4>
              <ChartExportButtons name={chart.column} getCanvas={() => chartRefs.current[index]?.canvas} />
            </div>
            <div className="chart-canvas-wrapper">
              <Line ref={(el) => { chartRefs.current[index] = el; }} data={data} options={options} />
            </div>
          </div>
        );
      }

      if (chart.type === 'categorical' && chart.labels && chart.values) {
        const data = {
          labels: chart.labels,
          datasets: [
            {
              label: chart.column,
              data: chart.values,
              backgroundColor: 'rgba(177, 86, 255, 0.4)',
              borderColor: '#b156ff',
              borderWidth: 1
            }
          ]
        };

        const options = {
          responsive: true,
          plugins: {
            legend: { position: 'top' }
          },
          scales: {
            x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#ccc' } },
            y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#ccc' } }
          }
        };

        return (
          <div key={index} className="chart-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4>{chart.column}</h4>
              <ChartExportButtons name={chart.column} getCanvas={() => chartRefs.current[index]?.canvas} />
            </div>
            <div className="chart-canvas-wrapper">
              <Bar ref={(el) => { chartRefs.current[index] = el; }} data={data} options={options} />
            </div>
          </div>
        );
      }

      if (chart.type === 'temporal' && chart.labels && chart.values) {
        const data = {
          labels: chart.labels,
          datasets: [
            {
              label: chart.column,
              data: chart.values,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              fill: true,
              tension: 0.4
            }
          ]
        };

        const options = {
          responsive: true,
          plugins: {
            legend: { position: 'top' }
          },
          scales: {
            x: { 
              grid: { color: 'rgba(255, 255, 255, 0.05)' }, 
              ticks: { color: '#ccc', maxTicksLimit: 8 }
            },
            y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#ccc' } }
          }
        };

        let title = chart.column;
        if (chart.date_column) {
          title = `${chart.column} vs ${chart.date_column}`;
        }

        return (
          <div key={index} className="chart-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4>{title}</h4>
              <ChartExportButtons name={title} getCanvas={() => chartRefs.current[index]?.canvas} />
            </div>
            <div className="chart-canvas-wrapper">
              <Line ref={(el) => { chartRefs.current[index] = el; }} data={data} options={options} />
            </div>
          </div>
        );
      }

      if (chart.type === 'scatter' && chart.points) {
        const data = {
          datasets: [
            {
              label: chart.column,
              data: chart.points,
              backgroundColor: 'rgba(79, 123, 255, 0.6)',
              borderColor: '#4F7BFF',
            },
          ],
        };

        const options = {
          responsive: true,
          plugins: {
            legend: { position: 'top' },
          },
          scales: {
            x: {
              title: { display: true, text: chart.x_label || '', color: '#999' },
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#ccc' },
            },
            y: {
              title: { display: true, text: chart.y_label || '', color: '#999' },
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#ccc' },
            },
          },
        };

        return (
          <div key={index} className="chart-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4>{chart.column}</h4>
              <ChartExportButtons name={chart.column} getCanvas={() => chartRefs.current[index]?.canvas} />
            </div>
            <div className="chart-canvas-wrapper">
              <Scatter ref={(el) => { chartRefs.current[index] = el; }} data={data} options={options} />
            </div>
          </div>
        );
      }

      if (chart.type === 'heatmap' && chart.labels && chart.cells) {
        return (
          <div key={index} className="chart-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4>{chart.column}</h4>
              <ChartExportButtons name={chart.column} getCanvas={() => heatmapCanvasRefs.current[index]} />
            </div>
            <div className="chart-canvas-wrapper">
              <HeatmapChart
                labels={chart.labels}
                cells={chart.cells}
                canvasRef={{
                  get current() { return heatmapCanvasRefs.current[index]; },
                  set current(val) { heatmapCanvasRefs.current[index] = val; },
                }}
              />
            </div>
          </div>
        );
      }

      return null;
    });
  };

  const getRiskColor = (risk) => {
    if (risk === 'bajo') return 'var(--green)';
    if (risk === 'moderado') return 'var(--amber)';
    return 'var(--red)';
  };

  return (
    <section className="analytics-panel">
      <header className="analytics-header">
        <div className="analytics-title-row">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="analytics-icon">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
          <h3>Resumen de tus Datos</h3>
        </div>
        <button className="close-analytics-btn" onClick={onClose} title="Cerrar panel">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>

      <div className="analytics-content">
        <div className="analytics-section">
          <div className="section-title">Resumen de Calidad</div>
          <div className="analytics-overview-card">
            <div className="overview-header">
              <div>
                <span className="card-eyebrow">Archivo</span>
                <strong style={{ fontSize: '0.95rem', fontWeight: '600' }} className="truncate">
                  {datasetContext.file_name}
                </strong>
              </div>
              <span className="mini-badge neutral">Datos Cargados</span>
            </div>
            <p className="overview-health-desc" style={{
              color: 'var(--text-secondary)',
              fontSize: '0.82rem',
              lineHeight: '1.5'
            }}>
              Calidad de datos: {health?.health_score?.toFixed(0) || 0}/100
            </p>
          </div>

          <div className="stats-grid">
            <div className="stat-card-clean">
              <span>Registros</span>
              <strong>{summary?.rows || 0}</strong>
            </div>
            <div className="stat-card-clean">
              <span>Variables</span>
              <strong>{summary?.columns || 0}</strong>
            </div>
            <div className="stat-card-clean">
              <span>Riesgo</span>
              <strong style={{ color: getRiskColor(health?.risk_level) }}>
                {health?.risk_level || 'Desconocido'}
              </strong>
            </div>
          </div>
        </div>

        {charts && charts.length > 0 && (
          <div className="analytics-section">
            <div className="section-title">Visualización de Datos</div>
            <div className="charts-grid">
              {renderCharts()}
            </div>
          </div>
        )}

        {preview && preview.length > 0 && (
          <div className="analytics-section">
            <div className="section-title">Vista Previa del Dataset</div>
            <div className="trend-table-wrapper" style={{
              padding: '16px',
              borderRadius: '12px',
              backgroundColor: 'var(--bg-surface-strong)',
              border: '1px solid var(--border-color)'
            }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr>
                    {Object.keys(preview[0]).map((col, i) => (
                      <th key={i} style={{ padding: '8px', textAlign: 'left', color: '#ccc', fontSize: '0.75rem', textTransform: 'uppercase' }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.slice(0, 8).map((row, rIndex) => (
                    <tr key={rIndex} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                      {Object.values(row).map((val, vIndex) => (
                        <td key={vIndex} style={{ padding: '8px', color: '#eee' }}>
                          {String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="analytics-section">
          <div className="section-title">Tendencias y Distribución</div>
          <div className="trends-placeholder">
            Sube un archivo con tus datos para mostrarte promedios, tendencias y detalles interesantes.
          </div>
        </div>
      </div>
    </section>
  );
}
