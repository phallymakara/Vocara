import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { apiClient } from "@/controllers/apiClient";
import { useAuth } from "@/controllers/AuthContext";
import type { UsageSummary } from "@/models/types";

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "U";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [avatarError, setAvatarError] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setAvatarError(false);
  }, [user?.avatar_url]);

  useEffect(() => {
    if (!user) {
      setUsage(null);
      return;
    }

    let cancelled = false;
    const fetchUsage = () => {
      apiClient
        .getUsage()
        .then((data) => {
          if (!cancelled) setUsage(data);
        })
        .catch(() => {
          // Ignore transient header usage fetch errors
        });
    };

    fetchUsage();
    window.addEventListener("vocara:usage-updated", fetchUsage);

    return () => {
      cancelled = true;
      window.removeEventListener("vocara:usage-updated", fetchUsage);
    };
  }, [user?.id, location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [menuOpen]);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate("/login", { replace: true });
  };

  const remainingCredits = usage?.quota_remaining ?? null;
  const totalQuota = usage?.total_quota ?? 0;
  const remainingRatio =
    remainingCredits !== null && totalQuota > 0
      ? Math.max(0, Math.min(1, remainingCredits / totalQuota))
      : 1;
  const ringRadius = 19;
  const ringCircumference = 2 * Math.PI * ringRadius;
  const ringDashOffset = ringCircumference * (1 - remainingRatio);

  return (
    <header className="h-16 px-6 md:px-8 bg-white border-b border-[#E8EDF5] flex items-center justify-between relative z-20">
      <div className="flex items-center gap-3">
        <h1 className="product-brand-name text-base font-semibold text-[#15213D] tracking-tight">
          Vocara Voice Studio
        </h1>
      </div>

      {user && (
        <div className="relative" ref={menuRef}>
          <div className="relative h-11 w-11 flex items-center justify-center">
            <svg
              className="absolute inset-0 h-11 w-11 -rotate-90 pointer-events-none"
              viewBox="0 0 44 44"
              aria-hidden="true"
            >
              <circle
                cx="22"
                cy="22"
                r={ringRadius}
                fill="none"
                stroke="#E5EBF5"
                strokeWidth="2.5"
              />
              <circle
                cx="22"
                cy="22"
                r={ringRadius}
                fill="none"
                stroke="#1264F5"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeDasharray={ringCircumference}
                strokeDashoffset={ringDashOffset}
                className="transition-all duration-300"
              />
            </svg>

            <button
              type="button"
              onClick={() => setMenuOpen((prev) => !prev)}
              aria-expanded={menuOpen}
              aria-haspopup="menu"
              aria-label="Open user profile menu"
              title={
                remainingCredits !== null
                  ? `${remainingCredits.toLocaleString()} credits remaining`
                  : user.name
              }
              className="relative h-8 w-8 rounded-full bg-[#EEF4FF] hover:bg-[#E0ECFF] text-xs font-semibold text-[#1264F5] flex items-center justify-center overflow-hidden transition-colors cursor-pointer"
            >
              {user.avatar_url && !avatarError ? (
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  referrerPolicy="no-referrer"
                  onError={() => setAvatarError(true)}
                  className="h-full w-full object-cover"
                />
              ) : (
                <span>{getInitials(user.name)}</span>
              )}
            </button>
          </div>

          {menuOpen && (
            <div
              role="menu"
              className="absolute right-0 mt-2 w-64 rounded-2xl border border-[#E5EBF5] bg-white p-2 z-30 animate-panel-enter"
            >
              <div className="px-3 py-2.5 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-[#15213D] truncate">
                    {user.name}
                  </p>
                  <span className="text-[11px] font-medium text-[#15213D] border border-[#E5EBF5] bg-white px-2 py-0.5 rounded-full capitalize flex-shrink-0">
                    {user.plan}
                  </span>
                </div>
                <p className="text-xs text-[#64748B] truncate">{user.email}</p>
              </div>

              {remainingCredits !== null && (
                <>
                  <div className="my-1 border-t border-[#E5EBF5]" />
                  <Link
                    to="/usage"
                    onClick={() => setMenuOpen(false)}
                    className="block px-3 py-2 rounded-xl hover:bg-[#F8FAFC] transition-colors space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-[#64748B]">Credits remaining</span>
                      <span className="font-semibold text-[#15213D] tabular-nums">
                        {remainingCredits.toLocaleString()}
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-[#E5EBF5] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#1264F5] transition-all duration-300"
                        style={{ width: `${Math.round(remainingRatio * 100)}%` }}
                      />
                    </div>
                  </Link>
                </>
              )}

              <div className="my-1 border-t border-[#E5EBF5]" />

              <button
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-[#15213D] hover:bg-[#F8FAFC] transition-colors cursor-pointer text-left"
              >
                <LogOut className="h-3.5 w-3.5 text-[#64748B]" />
                <span>Log out</span>
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
};
