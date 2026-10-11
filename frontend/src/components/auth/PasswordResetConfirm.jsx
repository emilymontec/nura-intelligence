import { useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { KeyRound } from 'lucide-react';

function PasswordResetConfirm() {
  const { uid, token } = useParams();
  const [newPassword1, setNewPassword1] = useState('');
  const [newPassword2, setNewPassword2] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const { confirmResetPassword } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword1 !== newPassword2) {
      setError('Las contraseñas no coinciden');
      return;
    }

    setLoading(true);

    try {
      await confirmResetPassword(uid, token, newPassword1, newPassword2);
      setSuccess('¡Contraseña restablecida con éxito! Redirigiendo...');
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-nura-black text-white font-sans antialiased min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 tech-grid-public">
        <div className="absolute top-[40%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-nura-electric ambient-glow" />
      </div>

      <div className="z-10 w-full max-w-md p-6">
        <div className="pure-glass-public rounded-2xl p-8 space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-normal text-white tracking-tight flex items-center justify-center gap-2">
              <KeyRound className="w-6 h-6 text-nura-electric" /> NUEVA CONTRASEÑA
            </h1>
            <p className="text-white/40 text-xs font-mono">Ingresa tu nueva clave de acceso</p>
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

          {!success && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] text-white/40 uppercase tracking-widest font-mono">
                  Nueva Contraseña
                </label>
                <input
                  type="password"
                  value={newPassword1}
                  onChange={(e) => setNewPassword1(e.target.value)}
                  required
                  placeholder="Tu nueva contraseña"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-sm transition-colors"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-white/40 uppercase tracking-widest font-mono">
                  Confirmar Nueva Contraseña
                </label>
                <input
                  type="password"
                  value={newPassword2}
                  onChange={(e) => setNewPassword2(e.target.value)}
                  required
                  placeholder="Confirma tu nueva contraseña"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-nura-electric/40 text-sm transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 mt-4 rounded-lg bg-nura-electric/20 border border-nura-electric/30 text-nura-electric hover:bg-nura-electric/30 transition-all text-xs font-mono disabled:opacity-50"
              >
                {loading ? 'RESTABLECIENDO...' : 'GUARDAR_CONTRASEÑA()'}
              </button>
            </form>
          )}

          <div className="pt-4 flex items-center justify-center gap-4 text-xs font-mono">
            <Link to="/login" className="text-white/40 hover:text-white transition-colors">
              Volver a Iniciar Sesión
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PasswordResetConfirm;
