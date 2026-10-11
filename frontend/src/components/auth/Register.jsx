import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { UserPlus } from 'lucide-react';

function Register() {
  const [email, setEmail] = useState('');
  const [password1, setPassword1] = useState('');
  const [password2, setPassword2] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (password1 !== password2) {
      setError('Las contraseñas no coinciden');
      return;
    }

    if (password1.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    setLoading(true);

    try {
      const data = await register(email, password1, password2);
      if (data.access || data.access_token) {
        navigate('/console');
      } else {
        setSuccess('¡Registro exitoso! Redirigiendo...');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-nura-black text-white font-sans antialiased min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 tech-grid-public">
        <div className="absolute top-[40%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-nura-purple ambient-glow" />
      </div>

      <div className="z-10 w-full max-w-md p-6">
        <div className="pure-glass-public rounded-2xl p-8 space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-normal text-white tracking-tight flex items-center justify-center gap-2">
              <UserPlus className="w-6 h-6 text-nura-purple" /> CREAR CUENTA
            </h1>
            <p className="text-white/40 text-xs font-mono">Únete a Nura Intelligence</p>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border-l-2 border-red-500 text-red-400 text-xs font-mono">
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 bg-emerald-500/10 border-l-2 border-emerald-500 text-emerald-400 text-xs font-mono">
              {success}
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
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-purple/40 text-sm transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] text-white/40 uppercase tracking-widest font-mono">
                Contraseña
              </label>
              <input
                type="password"
                value={password1}
                onChange={(e) => setPassword1(e.target.value)}
                required
                placeholder="Mínimo 8 caracteres"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-purple/40 text-sm transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] text-white/40 uppercase tracking-widest font-mono">
                Confirmar Contraseña
              </label>
              <input
                type="password"
                value={password2}
                onChange={(e) => setPassword2(e.target.value)}
                required
                placeholder="Repite tu contraseña"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-purple/40 text-sm transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 mt-4 rounded-lg bg-nura-purple/20 border border-nura-purple/30 text-nura-purple hover:bg-nura-purple/30 transition-all text-xs font-mono disabled:opacity-50"
            >
              {loading ? 'REGISTRANDO...' : 'CREAR_USUARIO()'}
            </button>
          </form>

          <div className="pt-4 flex items-center justify-center gap-4 text-xs font-mono">
            <span className="text-white/40">¿Ya tienes cuenta?</span>
            <Link to="/login" className="text-nura-purple hover:text-white transition-colors">
              Iniciar Sesión
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Register;
