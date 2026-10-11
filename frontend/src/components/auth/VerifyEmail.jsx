import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { MailCheck } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL
  : '';

function VerifyEmail() {
  const { key } = useParams();
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!key) {
      setStatus('error');
      setError('Enlace de verificación inválido.');
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/registration/verify-email/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ key }),
        });

        const data = await response.json();

        if (response.ok) {
          setStatus('success');
        } else {
          setStatus('error');
          setError(data.detail || data.key?.[0] || 'Error al verificar el correo electrónico.');
        }
      } catch {
        setStatus('error');
        setError('Error de conexión. Intenta de nuevo más tarde.');
      }
    };

    verifyEmail();
  }, [key]);

  return (
    <div className="bg-nura-black text-white font-sans antialiased min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 tech-grid-public">
        <div className="absolute top-[40%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-nura-electric ambient-glow" />
      </div>

      <div className="z-10 w-full max-w-md p-6">
        <div className="pure-glass-public rounded-2xl p-8 space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-normal text-white tracking-tight flex items-center justify-center gap-2">
              <MailCheck className="w-6 h-6 text-nura-electric" /> VERIFICACIÓN
            </h1>
            <p className="text-white/40 text-xs font-mono">Validación de correo electrónico</p>
          </div>

          {status === 'loading' && (
            <div className="text-center text-white/40 text-xs font-mono py-4">
              Verificando tu correo electrónico...
            </div>
          )}

          {status === 'success' && (
            <div className="space-y-6">
              <div className="p-3 bg-emerald-500/10 border-l-2 border-emerald-500 text-emerald-400 text-xs font-mono">
                ¡Correo electrónico verificado con éxito! Ya puedes iniciar sesión.
              </div>
              <div className="pt-2 flex items-center justify-center text-xs font-mono">
                <Link to="/login" className="text-nura-electric hover:text-white transition-colors">
                  Iniciar Sesión
                </Link>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-6">
              <div className="p-3 bg-red-500/10 border-l-2 border-red-500 text-red-400 text-xs font-mono">
                {error}
              </div>
              <div className="pt-2 flex items-center justify-center text-xs font-mono">
                <Link to="/login" className="text-white/40 hover:text-white transition-colors">
                  Volver a Iniciar Sesión
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default VerifyEmail;
