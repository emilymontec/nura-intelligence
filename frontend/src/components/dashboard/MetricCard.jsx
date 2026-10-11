export default function MetricCard({ label, value, unit, barColor = "bg-nura-electric", barWidth, valueColor = "text-white" }) {
  return (
    <div className="pure-glass rounded-xl p-4 font-mono transition-all duration-200 hover:border-white/10 hover:bg-white/[0.03]">
      <span className="text-[9px] text-white/30 block tracking-widest">// {label}</span>
      <div className={`text-xl font-light mt-1.5 ${valueColor}`}>
        {value} <span className="text-xs text-white/30">{unit}</span>
      </div>
      {barWidth && (
        <div className="w-full bg-white/5 h-1 mt-3 rounded-full overflow-hidden">
          <div
            className={`${barColor} h-full rounded-full transition-all duration-500`}
            style={{ width: typeof barWidth === "string" && barWidth.endsWith("%") ? barWidth : "100%" }}
          />
        </div>
      )}
    </div>
  );
}
