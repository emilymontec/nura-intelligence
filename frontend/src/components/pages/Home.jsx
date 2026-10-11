import { Link } from 'react-router-dom';
import { BarChart3, MessageSquare, FileText, Zap, Users, Database, PieChart, BookOpen } from 'lucide-react';
import PublicHeader from "../landing/PublicHeader";

function Home() {
  return (
    <div className="bg-nura-black text-white font-sans antialiased selection:bg-nura-electric/20 overflow-x-hidden min-h-screen">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 tech-grid-public">
        <div className="absolute top-[-10%] left-[25%] w-[70vw] h-[40vw] rounded-full bg-nura-electric ambient-glow animate-pulse-slow" />
        <div className="absolute top-[40%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-nura-purple ambient-glow" />
      </div>

      <PublicHeader />

      {/* Hero Section */}
      <section className="relative pt-40 pb-24 max-w-7xl mx-auto px-6 z-10">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.02] border border-white/[0.05] font-mono text-[10px] text-nura-electric uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-nura-electric animate-pulse" />
            Plataforma de análisis de datos
          </div>

          <h1 className="text-4xl md:text-6xl font-normal tracking-tight text-white leading-[1.1]">
            Nura Intelligence
          </h1>
          <p className="text-xl md:text-2xl text-white/70 font-normal">
            Analítica de datos asistida por inteligencia artificial
          </p>
          <p className="text-white/40 text-sm md:text-base font-normal max-w-2xl mx-auto">
            Transforma tus datos en decisiones inteligentes. Analiza, explora y pregunta sobre tus datasets 
            en lenguaje natural, sin conocimientos técnicos avanzados.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link
              to="/register"
              className="px-8 py-3 rounded bg-white text-nura-black text-sm font-medium hover:bg-white/90 transition-all"
            >
              Comenzar gratis
            </Link>
            <a
              href="#features"
              className="px-8 py-3 rounded border border-white/20 text-white/70 hover:text-white hover:border-white/40 transition-all text-sm font-light"
            >
              Ver demostración
            </a>
          </div>
        </div>

        {/* Mockup Section */}
        <div className="mt-16 md:mt-24">
          <div className="pure-glass-public rounded-2xl p-6 md:p-8 shadow-2xl">
            <div className="flex items-center gap-3 pb-4 border-b border-white/[0.05]">
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-white/10" />
                <span className="w-2.5 h-2.5 rounded-full bg-white/10" />
                <span className="w-2.5 h-2.5 rounded-full bg-white/10" />
              </div>
              <span className="text-[11px] text-white/30 font-mono">panel_analitico</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
              <div className="pure-glass rounded-lg p-4">
                <span className="text-[9px] text-white/30 block uppercase tracking-widest mb-2">
                  Registros analizados
                </span>
                <div className="text-2xl font-light text-white">142,500</div>
              </div>
              <div className="pure-glass rounded-lg p-4">
                <span className="text-[9px] text-white/30 block uppercase tracking-widest mb-2">
                  Health score
                </span>
                <div className="text-2xl font-light text-nura-electric">85%</div>
              </div>
              <div className="pure-glass rounded-lg p-4">
                <span className="text-[9px] text-white/30 block uppercase tracking-widest mb-2">
                  Anomalías
                </span>
                <div className="text-2xl font-light text-amber-400">12</div>
              </div>
            </div>
            <div className="mt-4 pure-glass rounded-lg p-4 font-mono text-xs text-white/50">
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 rounded-full bg-nura-purple" />
                <span>AI:</span>
              </div>
              <p>He detectado una tendencia ascendente en las ventas de los últimos 3 meses...</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative py-24 border-t border-white/[0.03] max-w-7xl mx-auto px-6 z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-normal tracking-tight text-white">
            Funcionalidades
          </h2>
          <p className="text-white/40 text-sm md:text-base font-light max-w-xl mx-auto mt-4">
            Todo lo que necesitas para analizar tus datos
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { title: "Motor de análisis", desc: "Estadísticas descriptivas, correlaciones y tendencias", icon: BarChart3 },
            { title: "Chat con datos", desc: "Pregunta sobre tus datos en lenguaje natural", icon: MessageSquare },
            { title: "Reportes", desc: "Genera reportes ejecutivos automáticos", icon: FileText }
          ].map((feature, i) => (
            <div key={i} className="pure-glass-public rounded-xl p-6 space-y-4 hover:border-white/10 transition-all">
              <div className="text-nura-electric">
                <feature.icon className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-normal text-white">{feature.title}</h3>
              <p className="text-white/40 text-sm font-normal leading-relaxed">
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="relative py-24 border-t border-white/[0.03] max-w-7xl mx-auto px-6 z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-normal tracking-tight text-white">
            Casos de uso básicos
          </h2>
          <p className="text-white/40 text-sm md:text-base font-normal max-w-xl mx-auto mt-4">
            Cómo puedes usar la plataforma
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {[
            { title: "Análisis de ventas", desc: "Explora tendencias, identifica productos con mejor rendimiento y detecta anomalías", icon: Zap },
            { title: "Datos de usuarios", desc: "Entiende el comportamiento de tus usuarios y segmenta tu audiencia", icon: Users },
            { title: "Inventario", desc: "Optimizá tu stock, detecta desabastecimiento y predice necesidades", icon: Database },
            { title: "Encuestas", desc: "Analiza respuestas de encuestas para extraer insights clave", icon: PieChart }
          ].map((usecase, i) => (
            <div key={i} className="pure-glass-public rounded-xl p-6 space-y-4">
              <div className="text-nura-purple">
                <usecase.icon className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-normal text-white">{usecase.title}</h3>
              <p className="text-white/40 text-sm font-normal">
                {usecase.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing Section */}
      <section className="relative py-24 border-t border-white/[0.03] max-w-7xl mx-auto px-6 z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-normal tracking-tight text-white">
            Precios
          </h2>
          <p className="text-white/40 text-sm md:text-base font-normal max-w-xl mx-auto mt-4">
            Comienza gratis, escala cuando lo necesites
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* Free Plan */}
          <div className="pure-glass-public rounded-2xl p-8 space-y-6 border border-nura-electric/30">
            <div className="space-y-2">
              <h3 className="text-2xl font-normal">Gratis</h3>
              <div className="mt-4">
                <span className="text-4xl font-light">$0</span>
                <span className="text-white/40 text-sm font-mono ml-2">/mes</span>
              </div>
            </div>
            <ul className="space-y-3 text-white/70 text-sm">
              <li className="flex items-center gap-2"><span className="text-nura-electric">✓</span>10 análisis por mes</li>
              <li className="flex items-center gap-2"><span className="text-nura-electric">✓</span>Chat con datos</li>
              <li className="flex items-center gap-2"><span className="text-nura-electric">✓</span>Exportación básica</li>
            </ul>
            <Link
              to="/register"
              className="block w-full text-center py-3 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-sm font-mono"
            >
              Comenzar gratis
            </Link>
          </div>

          {/* Pro Plan (Coming Soon) */}
          <div className="pure-glass-public rounded-2xl p-8 space-y-6 opacity-60">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <h3 className="text-2xl font-normal">Pro</h3>
                <span className="text-[10px] px-2 py-1 rounded bg-white/10 text-white/50 font-mono">Próximamente</span>
              </div>
              <div className="mt-4">
                <span className="text-4xl font-light">$19</span>
                <span className="text-white/40 text-sm font-mono ml-2">/mes</span>
              </div>
            </div>
            <ul className="space-y-3 text-white/70 text-sm">
              <li className="flex items-center gap-2"><span className="text-nura-purple">✓</span>Análisis ilimitados</li>
              <li className="flex items-center gap-2"><span className="text-nura-purple">✓</span>Reportes avanzados</li>
              <li className="flex items-center gap-2"><span className="text-nura-purple">✓</span>Soporte prioritario</li>
            </ul>
            <button disabled className="w-full py-3 rounded-lg bg-white/5 border border-white/10 text-white/30 cursor-not-allowed text-sm font-mono">
              Notificarme
            </button>
          </div>
        </div>
      </section>

      {/* Documentation Preview Section */}
      <section className="relative py-24 border-t border-white/[0.03] max-w-7xl mx-auto px-6 z-10">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-normal tracking-tight text-white">
            Documentación básica
          </h2>
          <p className="text-white/40 text-sm md:text-base font-normal max-w-xl mx-auto mt-4">
            Todo lo que necesitas para empezar
          </p>
        </div>

        <div className="max-w-3xl mx-auto pure-glass-public rounded-xl p-8">
          <div className="space-y-6 font-mono text-xs">
            <div className="space-y-2">
              <span className="text-nura-electric">1. </span><span className="text-white">Crear cuenta</span>
              <p className="text-white/40 pl-4">Regístrate con tu correo electrónico</p>
            </div>
            <div className="space-y-2">
              <span className="text-nura-electric">2. </span><span className="text-white">Subir dataset</span>
              <p className="text-white/40 pl-4">Carga tu archivo CSV o Excel</p>
            </div>
            <div className="space-y-2">
              <span className="text-nura-electric">3. </span><span className="text-white">Explorar datos</span>
              <p className="text-white/40 pl-4">Usa el dashboard y el chat para analizar</p>
            </div>
          </div>
          <div className="mt-6 text-center">
            <Link to="/docs" className="text-sm text-nura-electric hover:underline font-mono">
              Ver documentación completa →
            </Link>
          </div>
        </div>
      </section>

      {/* Footer with All Links */}
      <footer className="border-t border-white/[0.03] bg-nura-black relative z-10">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
            <div className="space-y-4">
              <h3 className="text-base font-normal text-white mb-4">Plataforma</h3>
              <ul className="space-y-3 text-white/40 text-sm">
                <li><Link to="/pricing" className="hover:text-white transition-colors">Precios</Link></li>
                <li><Link to="/docs" className="hover:text-white transition-colors">Documentación</Link></li>
                <li><Link to="/contact" className="hover:text-white transition-colors">Contacto</Link></li>
              </ul>
            </div>
            <div className="space-y-4">
              <h3 className="text-base font-normal text-white mb-4">Nosotros</h3>
              <ul className="space-y-3 text-white/40 text-sm">
                <li><Link to="/about" className="hover:text-white transition-colors">Acerca de</Link></li>
              </ul>
            </div>
            <div className="space-y-4">
              <h3 className="text-base font-normal text-white mb-4">Legal</h3>
              <ul className="space-y-3 text-white/40 text-sm">
                <li><Link to="/terms" className="hover:text-white transition-colors">Términos y condiciones</Link></li>
                <li><Link to="/privacy" className="hover:text-white transition-colors">Política de privacidad</Link></li>
              </ul>
            </div>
            <div className="space-y-4">
              <h3 className="text-base font-normal text-white mb-4">Nura Intelligence</h3>
              <p className="text-white/40 text-sm font-light leading-relaxed">
                Plataforma de análisis de datos asistida por IA
              </p>
            </div>
          </div>

          <div className="pt-10 mt-10 border-t border-white/[0.02] flex flex-col md:flex-row justify-between items-center gap-4">
            <span className="text-white/30 text-sm font-mono">
              © 2026 Nura Intelligence. Todos los derechos reservados.
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default Home;
