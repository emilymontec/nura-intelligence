import { useCallback } from "react";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import SidebarNav from "./SidebarNav";
import HeaderBar from "./HeaderBar";
import TelemetryPanel from "./TelemetryPanel";
import DashboardFooter from "./DashboardFooter";
import { NAV_SECTIONS } from "./viewContent";

function findItemLabel(viewId) {
  if (!NAV_SECTIONS || !Array.isArray(NAV_SECTIONS)) return viewId;
  for (const section of NAV_SECTIONS) {
    if (section.items && Array.isArray(section.items)) {
      for (const item of section.items) {
        if (item.id === viewId) return item.label;
      }
    }
  }
  return viewId;
}

function getViewIdFromLocation(location) {
  const pathParts = location.pathname.split("/").filter(Boolean);
  if (pathParts.length >= 2 && pathParts[0] === "console") {
    return pathParts[1];
  }
  return "dashboard";
}

export default function DashboardLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const currentView = getViewIdFromLocation(location);

  const handleNavigate = useCallback((viewId) => {
    navigate(`/console/${viewId}`);
  }, [navigate]);

  const handleNewAnalysis = useCallback(() => {
    navigate("/console/datasets");
  }, [navigate]);

  const label = findItemLabel(currentView) || currentView || "dashboard";
  const sysPath = `root / ${label}`;

  return (
    <div className="bg-nura-black text-white font-sans antialiased h-screen flex overflow-hidden select-none">
      <div className="fixed inset-0 pointer-events-none z-0 tech-grid overflow-hidden">
        <div className="absolute top-[-30%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-nura-electric/10 filter blur-[120px] animate-gradient-drift" />
        <div className="absolute bottom-[-25%] left-[5%] w-[40vw] h-[40vw] rounded-full bg-nura-purple/10 filter blur-[130px] animate-gradient-drift" style={{ animationDelay: "-11s" }} />
      </div>

      <SidebarNav currentView={currentView} onNavigate={handleNavigate} />

      <main className="flex-1 bg-nura-black z-10 flex flex-col overflow-hidden relative">
        <HeaderBar currentPath={sysPath} onNewAnalysis={handleNewAnalysis} />
        <Outlet />
        <DashboardFooter />
      </main>

      <TelemetryPanel />
    </div>
  );
}
