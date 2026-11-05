import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Mic, Users, Key, BarChart3, Radio } from "lucide-react";
import { cn } from "@/lib/utils";

export const Sidebar: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: "/", alias: "/tts", label: "TTS Studio", icon: Mic },
    { path: "/voices", alias: "/voices", label: "Voice Library", icon: Users },
    { path: "/keys", alias: "/keys", label: "API Keys", icon: Key },
    { path: "/usage", alias: "/usage", label: "Usage & Quota", icon: BarChart3 },
    { path: "/jobs", alias: "/webhooks", label: "Jobs & Webhooks", icon: Radio },
  ];

  const isItemActive = (path: string, alias: string) => {
    if (path === "/") {
      return location.pathname === "/" || location.pathname === "/tts";
    }
    return location.pathname.startsWith(path) || location.pathname.startsWith(alias);
  };

  return (
    <aside className="w-16 md:w-64 bg-[#101B33] text-slate-100 flex flex-col flex-shrink-0 border-r border-[#1C2945] transition-all z-30">
      {/* Brand Header */}
      <NavLink
        to="/"
        className="h-20 flex items-center gap-3 px-3 md:px-5 hover:bg-white/[0.02] transition-colors"
      >
        <div className="h-10 w-10 flex-shrink-0 rounded-xl bg-[#1264F5] text-white flex items-center justify-center font-bold text-lg shadow-none">
          V
        </div>
        <div className="product-brand-name flex flex-col min-w-0">
          <span className="font-semibold text-base leading-tight text-white tracking-wide truncate">
            Vocara
          </span>
          <span className="text-xs text-[#7B8CA6] truncate mt-0.5">Voice Platform</span>
        </div>
      </NavLink>

      {/* Nav List */}
      <nav aria-label="Main Navigation" className="flex-1 py-2 px-2 md:px-3 space-y-1">
        <div className="hidden md:block px-3 pt-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-[#7B8CA6]">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = isItemActive(item.path, item.alias);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              title={item.label}
              className={cn(
                "w-full flex items-center gap-3 px-3.5 py-3 rounded-xl text-sm font-medium transition-all text-left",
                isActive
                  ? "bg-[#1264F5] text-white"
                  : "text-[#94A3B8] hover:bg-white/5 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              <span className="hidden md:inline truncate">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-[#1C2945] text-xs text-[#64748B] text-center md:text-left">
        <span className="hidden md:inline">Vocara API v1.0.0</span>
        <span className="md:hidden">v1</span>
      </div>
    </aside>
  );
};
