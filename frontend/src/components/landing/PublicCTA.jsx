export default function PublicCTA() {
  return (
    <section className="relative py-28 max-w-4xl mx-auto px-6 text-center z-10 space-y-8">
      <div className="w-px h-12 bg-gradient-to-b from-transparent to-white/20 mx-auto" />
      <h2 className="text-2xl md:text-4xl font-light tracking-tight text-white/90 max-w-xl mx-auto leading-snug">
        Transforma tus datos en decisiones con inteligencia artificial.
      </h2>
      <div>
        <a
          href="/login"
          className="inline-flex h-10 px-6 rounded bg-white text-nura-black text-xs font-medium items-center justify-center hover:bg-white/90 transition-all font-mono tracking-wide"
        >
          comenzar_analisis()
        </a>
      </div>
    </section>
  );
}
