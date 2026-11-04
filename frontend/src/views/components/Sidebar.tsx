import React from "react";
import { Mic, Users, Key, BarChart3, Radio } from "lucide-react";
import { cn } from "@/lib/utils";

export type NavTab = "tts" | "voices" | "keys" | "usage" | "webhooks";

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onSelectTab }) => {
  const navItems = [
    { key: "tts" as NavTab, label: "TTS Studio", icon: Mic },
    { key: "voices" as NavTab, label: "Voice Library", icon: Users },
    { key: "keys" as NavTab, label: "API Keys", icon: Key },
    { key: "usage" as NavTab, label: "Usage & Quota", icon: BarChart3 },
    { key: "webhooks" as NavTab, label: "Jobs & Webhooks", icon: Radio },
  ];

  return (
    <aside className="w-16 md:w-64 bg-slate-900 text-slate-100 flex flex-col flex-shrink-0 border-r border-slate-800 transition-all select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-3 md:px-5 border-b border-slate-800">
        <div className="h-9 w-9 flex-shrink-0 rounded bg-sky-600 text-white flex items-center justify-center font-bold text-lg">
          V
        </div>
        <div className="product-brand-name flex flex-col min-w-0">
          <span className="font-semibold text-sm leading-tight text-white tracking-wide truncate">
            Vocara
          </span>
          <span className="text-[11px] text-slate-400 truncate">Voice Platform</span>
        </div>
      </div>

      {/* Nav List */}
      <div className="flex-1 py-4 px-2 md:px-3 space-y-1">
        <div className="hidden md:block px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onSelectTab(item.key)}
              title={item.label}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded text-sm font-medium transition-colors text-left",
                isActive
                  ? "bg-sky-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              <span className="hidden md:inline truncate">{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800 text-[11px] text-slate-400 text-center md:text-left">
        <span className="hidden md:inline">Vocara API v1.0.0</span>
        <span className="md:hidden">v1</span>
      </div>
    </aside>
  );
};

