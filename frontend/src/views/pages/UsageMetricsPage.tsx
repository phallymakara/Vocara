import React, { useEffect, useRef, useState } from "react";
import { Loader2, BarChart3, Clock, ChevronDown, Check } from "lucide-react";
import { useUsageController } from "@/controllers/useUsageController";
import { Progress } from "@/views/components/ui/progress";

const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const FULL_MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export const UsageMetricsPage: React.FC = () => {
  const {
    usage,
    selectedYear,
    selectedMonth,
    setSelectedMonth,
    isLoading,
    generalError,
    percentUsed,
    formatDuration,
  } = useUsageController();

  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [hoveredDay, setHoveredDay] = useState<number | null>(null);
  const [hoveredHour, setHoveredHour] = useState<number | null>(null);
  const [isMonthMenuOpen, setIsMonthMenuOpen] = useState(false);
  const monthMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isMonthMenuOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (monthMenuRef.current && !monthMenuRef.current.contains(event.target as Node)) {
        setIsMonthMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsMonthMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isMonthMenuOpen]);

  const dailyUsage = usage?.daily_usage ?? [];
  const activeDay = hoveredDay ?? selectedDay;
  const activeDateKey =
    activeDay !== null
      ? `${selectedYear}-${String(selectedMonth).padStart(2, "0")}-${String(activeDay).padStart(2, "0")}`
      : null;

  const baseHourlyMap = new Map(
    (activeDateKey ? usage?.hourly_by_date?.[activeDateKey] ?? [] : []).map((h) => [h.hour, h])
  );
  const hourlyUsage = Array.from({ length: 24 }, (_, hour) => {
    const existing = baseHourlyMap.get(hour);
    return (
      existing ?? {
        hour,
        characters: 0,
        requests: 0,
        duration_seconds: 0,
      }
    );
  });
  const totalRequests = usage?.total_requests ?? 0;
  const totalAudioSeconds = usage?.total_audio_seconds ?? 0;

  const now = new Date();
  const isCurrentMonth =
    usage?.year === now.getFullYear() && usage?.month === now.getMonth() + 1;
  const daysInMonth = new Date(selectedYear, selectedMonth, 0).getDate();
  const elapsedDays = isCurrentMonth ? Math.max(1, now.getDate()) : daysInMonth;
  const dailyAvgChars = usage ? Math.round(usage.characters_used / elapsedDays) : 0;

  const dailyMap = new Map(dailyUsage.map((d) => [d.date, d]));
  const monthDays = Array.from({ length: daysInMonth }, (_, idx) => {
    const day = idx + 1;
    const key = `${selectedYear}-${String(selectedMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const entry = dailyMap.get(key);
    return {
      day,
      date: key,
      characters: entry?.characters ?? 0,
      requests: entry?.requests ?? 0,
    };
  });

  const maxDailyChars = Math.max(1, ...monthDays.map((d) => d.characters));
  const maxHourlyChars = Math.max(1, ...hourlyUsage.map((h) => h.characters));
  const activeHourlyTotalChars = hourlyUsage.reduce((acc, h) => acc + h.characters, 0);
  const activeHourlyPoint =
    hoveredHour !== null ? hourlyUsage.find((h) => h.hour === hoveredHour) || null : null;

  const avgCharsPerRequest =
    usage && totalRequests > 0 ? Math.round(usage.characters_used / totalRequests) : 0;
  const projectedMonthChars = dailyAvgChars * daysInMonth;
  const peakDayEntry = dailyUsage.reduce<(typeof dailyUsage)[number] | null>(
    (best, cur) => (!best || cur.characters > best.characters ? cur : best),
    null
  );
  const monthlyHours = usage?.hourly_usage ?? [];
  const peakHourEntry = monthlyHours.reduce<(typeof monthlyHours)[number] | null>(
    (best, cur) => (!best || cur.characters > best.characters ? cur : best),
    null
  );
  const peakDayLabel = peakDayEntry
    ? `${SHORT_MONTHS[Number(peakDayEntry.date.split("-")[1]) - 1] || ""} ${Number(peakDayEntry.date.split("-")[2])}`
    : null;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {generalError && (
        <p className="text-xs text-destructive">{generalError}</p>
      )}

      {isLoading && !usage ? (
        <div className="py-12 flex justify-center items-center text-sm text-[#64748B]">
          <Loader2 className="h-5 w-5 animate-spin mr-2 text-[#1264F5]" />
          Retrieving usage metrics...
        </div>
      ) : !usage ? (
        <div className="py-10 text-center text-sm text-[#64748B] border border-dashed border-[#E5EBF5] bg-white rounded-3xl">
          No usage information available.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Top Row: Monthly Quota (Left) + Usage Analytics (Right) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
            {/* Main Monthly Quota Card */}
            <div className="lg:col-span-7 bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 flex flex-col justify-between space-y-5">
              <div className="space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <h3 className="text-base font-bold text-[#15213D] leading-tight">
                    Monthly Character Quota
                  </h3>
                  <span className="inline-flex items-center rounded-full border border-[#E5EBF5] bg-white px-3 py-1 text-xs font-medium text-[#15213D] w-fit">
                    Active Period
                  </span>
                </div>

                <div className="space-y-2.5">
                  <div className="flex justify-between items-baseline text-sm tabular-nums">
                    <div className="space-x-1.5">
                      <span className="text-2xl font-bold tracking-tight text-[#15213D]">
                        {usage.characters_used.toLocaleString()}
                      </span>
                      <span className="text-xs text-[#64748B]">
                        / {usage.total_quota.toLocaleString()} chars
                      </span>
                    </div>
                    <span className="text-xs font-semibold text-[#15213D]">
                      {percentUsed}% used
                    </span>
                  </div>
                  <Progress value={percentUsed} className="h-2.5 bg-[#E5EBF5]" />
                </div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-[#64748B] pt-4 border-t border-[#E5EBF5] tabular-nums">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span>
                    <strong className="font-semibold text-[#15213D]">
                      {totalRequests.toLocaleString()}
                    </strong>{" "}
                    requests
                  </span>
                  <span>&middot;</span>
                  <span>
                    <strong className="font-semibold text-[#15213D]">
                      {formatDuration(totalAudioSeconds)}
                    </strong>{" "}
                    audio
                  </span>
                  <span>&middot;</span>
                  <span>
                    <strong className="font-semibold text-[#15213D]">
                      {dailyAvgChars.toLocaleString()}
                    </strong>{" "}
                    chars/day
                  </span>
                </div>
                <div>
                  <span>Billing Period: </span>
                  <span className="font-medium text-[#15213D]">
                    Month {usage.month}, {usage.year}
                  </span>
                </div>
              </div>
            </div>

            {/* Usage Insights Analytics Card */}
            <div className="lg:col-span-5 bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 flex flex-col justify-between space-y-4">
              <h3 className="text-base font-bold text-[#15213D] leading-tight">
                Usage Analytics
              </h3>

              <div className="divide-y divide-[#E5EBF5] text-xs tabular-nums">
                <div className="flex items-center justify-between py-2.5 first:pt-0">
                  <span className="text-[#64748B]">Avg. Request Size</span>
                  <span className="font-semibold text-[#15213D]">
                    {avgCharsPerRequest > 0 ? `${avgCharsPerRequest.toLocaleString()} chars` : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2.5">
                  <span className="text-[#64748B]">Projected Month-End</span>
                  <span className="font-semibold text-[#1264F5]">
                    {projectedMonthChars > 0 ? `~${projectedMonthChars.toLocaleString()} chars` : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2.5">
                  <span className="text-[#64748B]">Peak Day</span>
                  <span className="font-semibold text-[#15213D]">
                    {peakDayEntry && peakDayEntry.characters > 0
                      ? `${peakDayLabel} · ${peakDayEntry.characters.toLocaleString()} chars`
                      : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between py-2.5 last:pb-0">
                  <span className="text-[#64748B]">Peak Hour</span>
                  <span className="font-semibold text-[#15213D]">
                    {peakHourEntry && peakHourEntry.characters > 0
                      ? `${String(peakHourEntry.hour).padStart(2, "0")}:00 · ${peakHourEntry.characters.toLocaleString()} chars`
                      : "—"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Daily Character Usage & Hover Hourly Area Graph */}
          <div
            onMouseLeave={() => {
              setHoveredDay(null);
              setHoveredHour(null);
            }}
            className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h3 className="text-base font-bold text-[#15213D] leading-tight flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-[#1264F5]" />
                <span>Daily Character Activity</span>
              </h3>

              <div className="relative" ref={monthMenuRef}>
                <button
                  type="button"
                  aria-label="Select Month"
                  aria-expanded={isMonthMenuOpen}
                  onClick={() => setIsMonthMenuOpen((prev) => !prev)}
                  className="inline-flex items-center justify-between gap-2 h-9 min-w-[140px] px-3.5 rounded-xl border border-[#E5EBF5] bg-white hover:border-[#CBD5E1] text-xs font-medium text-[#15213D] focus:outline-none focus:border-[#1264F5] focus:ring-1 focus:ring-[#1264F5]/30 cursor-pointer transition-colors"
                >
                  <span>{FULL_MONTHS[selectedMonth - 1] ?? "Select month"}</span>
                  <ChevronDown
                    className={`h-3.5 w-3.5 text-[#7B8CA6] transition-transform duration-150 ${
                      isMonthMenuOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {isMonthMenuOpen && (
                  <div
                    role="listbox"
                    aria-label="Select Month"
                    className="absolute right-0 top-full mt-2 w-48 max-h-64 overflow-y-auto z-50 bg-white border border-[#E5EBF5] rounded-2xl p-2 space-y-1 animate-panel-enter"
                  >
                    {FULL_MONTHS.map((name, idx) => {
                      const monthNumber = idx + 1;
                      const isSelected = monthNumber === selectedMonth;
                      return (
                        <button
                          key={name}
                          type="button"
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => {
                            setSelectedMonth(monthNumber);
                            setSelectedDay(null);
                            setHoveredDay(null);
                            setIsMonthMenuOpen(false);
                          }}
                          className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-xl border text-left text-xs font-medium transition-colors cursor-pointer ${
                            isSelected
                              ? "border-[#1264F5] bg-[#1264F5] text-white"
                              : "border-transparent bg-white text-[#15213D] hover:bg-[#F8FAFC]"
                          }`}
                        >
                          <span>{name}</span>
                          {isSelected && <Check className="h-3.5 w-3.5 text-white flex-shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="overflow-x-auto pb-1">
              <div className="h-48 min-w-[520px] flex items-end gap-1.5 pt-2">
                {monthDays.map((point) => {
                  const heightPct =
                    point.characters > 0
                      ? Math.max(8, Math.round((point.characters / maxDailyChars) * 100))
                      : 4;
                  const isActive = activeDay === point.day;
                  const tooltip = `${SHORT_MONTHS[selectedMonth - 1]} ${point.day}: ${point.characters.toLocaleString()} chars (${point.requests} req)`;
                  return (
                    <button
                      key={point.day}
                      type="button"
                      onClick={() => setSelectedDay((prev) => (prev === point.day ? null : point.day))}
                      onMouseEnter={() => {
                        setHoveredDay(point.day);
                        setHoveredHour(null);
                      }}
                      onFocus={() => setHoveredDay(point.day)}
                      title={tooltip}
                      aria-label={tooltip}
                      aria-pressed={selectedDay === point.day}
                      className="flex-1 h-full flex flex-col justify-end items-center gap-1.5 group cursor-pointer focus:outline-none"
                    >
                      <div className="w-full flex-1 flex items-end justify-center">
                        <div
                          style={{ height: `${heightPct}%` }}
                          className={`w-full max-w-[18px] rounded-t-lg transition-colors ${
                            isActive
                              ? point.characters > 0
                                ? "bg-[#0E52CC]"
                                : "bg-[#CBD5E1]"
                              : point.characters > 0
                              ? "bg-[#1264F5]"
                              : "bg-[#F1F5F9]"
                          }`}
                        />
                      </div>
                      <span
                        className={`text-[10px] tabular-nums ${
                          isActive
                            ? "font-bold text-[#1264F5]"
                            : point.characters > 0
                            ? "font-semibold text-[#15213D]"
                            : "text-[#94A3B8]"
                        }`}
                      >
                        {point.day}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Expanding Hourly Area Graph (opens when hovering or selecting a date) */}
            {activeDay !== null && (
              <div className="pt-5 border-t border-[#E5EBF5] space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-[#15213D]">
                    <Clock className="h-3.5 w-3.5 text-[#1264F5]" />
                    <span>
                      Hourly Usage &middot; {SHORT_MONTHS[selectedMonth - 1]} {activeDay}, {selectedYear}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-[#64748B] tabular-nums">
                    {activeHourlyPoint ? (
                      <span>
                        <strong className="font-semibold text-[#15213D]">
                          {String(activeHourlyPoint.hour).padStart(2, "0")}:00
                        </strong>{" "}
                        &middot; {activeHourlyPoint.characters.toLocaleString()} chars &middot;{" "}
                        {activeHourlyPoint.requests} req
                      </span>
                    ) : (
                      <span>
                        Total: {activeHourlyTotalChars.toLocaleString()} chars
                      </span>
                    )}
                    {selectedDay !== null && (
                      <button
                        type="button"
                        onClick={() => setSelectedDay(null)}
                        className="text-xs font-medium text-[#1264F5] hover:underline cursor-pointer"
                      >
                        Close
                      </button>
                    )}
                  </div>
                </div>

                <div className="overflow-x-auto pb-1">
                  <div className="h-32 min-w-[520px] flex items-end gap-2 pt-1">
                    {hourlyUsage.map((point) => {
                      const heightPct =
                        point.characters > 0
                          ? Math.max(12, Math.round((point.characters / maxHourlyChars) * 100))
                          : 0;
                      const isHourHovered = hoveredHour === point.hour;
                      const hourLabel = String(point.hour).padStart(2, "0");
                      const tooltip = `${hourLabel}:00 - ${point.characters.toLocaleString()} chars (${point.requests} req)`;
                      return (
                        <div
                          key={point.hour}
                          onMouseEnter={() => setHoveredHour(point.hour)}
                          onMouseLeave={() => setHoveredHour(null)}
                          title={tooltip}
                          aria-label={tooltip}
                          className="flex-1 h-full flex flex-col justify-end items-center gap-1.5 cursor-default"
                        >
                          <div className="w-full max-w-[12px] flex-1 rounded-full bg-[#F1F5F9] overflow-hidden flex items-end">
                            {heightPct > 0 && (
                              <div
                                style={{ height: `${heightPct}%` }}
                                className={`w-full rounded-full transition-colors ${
                                  isHourHovered ? "bg-[#0E52CC]" : "bg-[#1264F5]"
                                }`}
                              />
                            )}
                          </div>
                          <span
                            className={`text-[10px] tabular-nums ${
                              point.characters > 0 || isHourHovered
                                ? "font-semibold text-[#15213D]"
                                : "text-[#94A3B8]"
                            }`}
                          >
                            {hourLabel}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
