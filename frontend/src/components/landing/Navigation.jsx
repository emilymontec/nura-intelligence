import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

function Navigation() {
  const { user, logout } = useAuth();

  return (
    <nav>
      <div className="rec-indicator">
        <span className="rec-dot"></span>
        <span>ESCUCHA ACTIVA</span>
      </div>
      <div className="nav-links">
        <a href="#panel" className="active">Plataforma</a>
        <a href="#instrumento">Instrumento</a>
        {user ? (
          <>
            <span className="user-email">{user.email}</span>
            <button onClick={logout}>Cerrar Sesión</button>
            <Link to="/asistente" className="cta">Ir al Chat</Link>
          </>
        ) : (
          <>
            <Link to="/login">Iniciar Sesión</Link>
            <Link to="/register" className="cta">Crear Cuenta</Link>
          </>
        )}
      </div>
    </nav>
  );
}

export default Navigation;
