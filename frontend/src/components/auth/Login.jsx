import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LogIn } from 'lucide-react';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [mfaToken, setMfaToken] = useState(null);
  const [mfaCode, setMfaCode] = useState('');
  const { login, verifyMfaLogin } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(email, password);
      if (result?.mfaRequired) {
        setMfaToken(result.mfaToken);
      } else {
        navigate('/console');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await verifyMfaLogin(mfaToken, mfaCode);
      navigate('/console');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (mfaToken) {
    return (
      <div className="bg-nura-black text-white font-sans antialiased min-h-screen flex items-center justify-center relative overflow-hidden">
        <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 tech-grid-public">
          <div className="absolute top-[-10%] left-[25%] w-[70vw] h-[40vw] rounded-full bg-nura-electric ambient-glow animate-pulse-slow" />
        </div>
        <div className="z-10 w-full max-w-md p-6">
          <div className="pure-glass-public rounded-2xl p-8 space-y-6">
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-normal text-white tracking-tight">VERIFICACIÓN EN DOS PASOS</h1>
              <p className="text-white/40 text-xs font-mono">Ingresa el código de tu app de autenticación</p>
            </div>
            {error && (
              <div className="p-3 bg-red-500/10 border-l-2 border-red-500 text-red-400 text-xs font-mono">
                {error}
              </div>
            )}
            <form onSubmit={handleMfaSubmit} className="space-y-4">
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                required
                placeholder="000000"
                autoFocus
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white text-center text-2xl tracking-[0.5em] focus:outline-none focus:border-nura-electric/40 transition-colors"
              />
              <button
                type="submit"
                disabled={loading || mfaCode.length !== 6}
                className="w-full py-3 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-xs font-mono disabled:opacity-50"
              >
                {loading ? 'VERIFICANDO...' : 'VERIFICAR()'}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-nura-black text-white font-sans antialiased min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 tech-grid-public">
        <div className="absolute top-[-10%] left-[25%] w-[70vw] h-[40vw] rounded-full bg-nura-electric ambient-glow animate-pulse-slow" />
      </div>

      <div className="z-10 w-full max-w-md p-6">
        <div className="pure-glass-public rounded-2xl p-8 space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-normal text-white tracking-tight flex items-center justify-center gap-2">
              <LogIn className="w-6 h-6 text-nura-electric" /> INICIAR SESIÓN
            </h1>
            <p className="text-white/40 text-xs font-mono">Accede al panel de analítica</p>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border-l-2 border-red-500 text-red-400 text-xs font-mono">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[10px] text-white/40 uppercase tracking-widest font-mono">
                Correo Electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="tu@email.com"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-sm transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] text-white/40 uppercase tracking-widest font-mono">
                Contraseña
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Tu contraseña"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-sm transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 mt-4 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-xs font-mono disabled:opacity-50"
            >
              {loading ? 'CARGANDO...' : 'ENTRAR()'}
            </button>
          </form>

          <div className="pt-4 flex items-center justify-center gap-4 text-xs font-mono">
            <Link to="/password-reset" className="text-white/40 hover:text-white transition-colors">
              ¿Olvidaste tu contraseña?
            </Link>
            <span className="text-white/20">|</span>
            <Link to="/register" className="text-nura-electric hover:text-white transition-colors">
              Crear cuenta
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
