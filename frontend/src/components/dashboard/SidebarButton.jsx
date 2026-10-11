export default function SidebarButton({ item, isActive, onClick }) {
  const Icon = item.icon;
  const isPurple = item.accent === "purple";

  const activeBorder = isPurple ? "border-nura-purple" : "border-nura-electric";
  const activeStyles = isActive
    ? `bg-white/[0.04] text-white border-l-2 ${activeBorder} shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04)]`
    : "text-white/40 border-l-2 border-transparent hover:bg-white/[0.02] hover:text-white/80";
  const iconColor = isActive
    ? (isPurple ? "text-nura-purple" : "text-nura-electric")
    : "text-white/30";

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2.5 px-2.5 py-2 text-xs rounded-lg font-mono transition-all duration-150 ${activeStyles}`}
    >
      <Icon className={`w-3.5 h-3.5 flex-none transition-colors ${iconColor}`} />
      <span className="truncate">{item.label}</span>
    </button>
  );
}
