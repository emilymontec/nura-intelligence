import React from 'react';
import { useNavigate } from 'react-router-dom';

function Hero() {
  const navigate = useNavigate();

  return (
    <section className="hero">
      <span className="hero-tag">Instrumento de escucha de datos</span>
      <h1>Todo dato dice algo.<br /><em>Lo</em> escucha antes que tú.</h1>
      <p>
        Se conecta a tu ecosistema, capta cada señal operativa en tiempo real y traduce el ruido en decisiones claras — en el mismo lenguaje con el que se lo preguntas. Sin paneles que configurar.
      </p>
      <div className="hero-actions">
        <button onClick={() => navigate('/asistente')} className="btn-primary">Iniciar escucha</button>
        <a href="#panel" className="btn-secondary">Ver el instrumento en vivo ↓</a>
      </div>

      <div className="trace-wrap">
        <div className="trace-track">
          <svg viewBox="0 0 700 96" preserveAspectRatio="none">
            <path d="M0,48 L20,48 L34,20 L48,76 L62,48 L110,48 L124,40 L138,56 L152,48 L220,48 L234,10 L248,86 L262,48 L330,48 L344,34 L358,60 L372,48 L440,48 L454,22 L468,74 L482,48 L560,48 L574,42 L588,54 L602,48 L700,48" fill="none" stroke="#4ade80" strokeWidth="1.4" opacity="0.55" />
          </svg>
          <svg viewBox="0 0 700 96" preserveAspectRatio="none">
            <path d="M0,48 L20,48 L34,20 L48,76 L62,48 L110,48 L124,40 L138,56 L152,48 L220,48 L234,10 L248,86 L262,48 L330,48 L344,34 L358,60 L372,48 L440,48 L454,22 L468,74 L482,48 L560,48 L574,42 L588,54 L602,48 L700,48" fill="none" stroke="#4ade80" strokeWidth="1.4" opacity="0.55" />
          </svg>
        </div>
      </div>
    </section>
  );
}

export default Hero;
