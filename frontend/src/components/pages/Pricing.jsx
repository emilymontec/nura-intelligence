import { Link } from 'react-router-dom';

export default function Pricing() {
  return (
    <div className="bg-nura-black text-white font-sans antialiased min-h-screen relative overflow-hidden">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 tech-grid-public">
        <div className="absolute top-[-10%] left-[25%] w-[70vw] h-[40vw] rounded-full bg-nura-electric ambient-glow animate-pulse-slow" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-24">
        <div className="text-center space-y-4 mb-16">
          <h1 className="text-4xl md:text-5xl font-normal text-white tracking-tight">Planes</h1>
          <p className="text-white/40 text-sm md:text-base font-normal max-w-2xl mx-auto">
            Comienza hoy mismo con nuestra versión gratuita
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Plan */}
          <div className="pure-glass-public rounded-2xl p-8 space-y-6">
            <div className="space-y-2">
              <h2 className="text-2xl font-normal">Gratis</h2>
              <p className="text-white/40 text-sm font-mono">Perfecto para empezar</p>
              <div className="mt-4">
                <span className="text-4xl font-light">$0</span>
                <span className="text-white/40 text-sm font-mono ml-2">/mes</span>
              </div>
            </div>
            <div className="space-y-3 text-sm text-white/70">
              <div className="flex items-center gap-2">
                <span className="text-nura-electric">✓</span>
                <span>10 análisis por mes</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-nura-electric">✓</span>
                <span>Chat con datos</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-nura-electric">✓</span>
                <span>Exportación básica</span>
              </div>
            </div>
            <Link
              to="/register"
              className="block w-full text-center py-3 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-xs font-mono"
            >
              COMENZAR_GRATIS()
            </Link>
          </div>

          {/* Pro Plan (Coming Soon) */}
          <div className="pure-glass-public rounded-2xl p-8 space-y-6 opacity-60">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-normal">Pro</h2>
                <span className="text-[10px] px-2 py-1 rounded bg-white/10 text-white/50 font-mono">Próximamente</span>
              </div>
              <p className="text-white/40 text-sm font-mono">Para equipos y proyectos más grandes</p>
              <div className="mt-4">
                <span className="text-4xl font-light">$19</span>
                <span className="text-white/40 text-sm font-mono ml-2">/mes</span>
              </div>
            </div>
            <div className="space-y-3 text-sm text-white/70">
              <div className="flex items-center gap-2">
                <span className="text-nura-purple">✓</span>
                <span>Análisis ilimitados</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-nura-purple">✓</span>
                <span>Reportes avanzados</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-nura-purple">✓</span>
                <span>Soporte prioritario</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-nura-purple">✓</span>
                <span>APIs</span>
              </div>
            </div>
            <button
              disabled
              className="w-full py-3 rounded-lg bg-white/5 border border-white/10 text-white/30 cursor-not-allowed text-xs font-mono"
            >
              NOTIFICARME()
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}