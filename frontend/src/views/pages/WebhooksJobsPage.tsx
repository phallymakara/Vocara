import React from "react";
import { Trash2, Plus, Loader2 } from "lucide-react";
import { useWebhookController } from "@/controllers/useWebhookController";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/views/components/ui/table";

export const WebhooksJobsPage: React.FC = () => {
  const {
    webhooks,
    isLoadingWebhooks,
    targetUrl,
    setTargetUrl,
    selectedEvents,
    toggleEvent,
    urlError,
    webhookError,
    createWebhook,
    deleteWebhook,
  } = useWebhookController();

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Register Webhook Card */}
      <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
        <h3 className="text-base font-bold text-[#15213D] leading-tight">
          Register Webhook Endpoint
        </h3>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="webhook-url" className="text-xs font-semibold text-[#15213D] block">
              Target URL
            </label>
            <input
              id="webhook-url"
              type="text"
              placeholder="Enter webhook endpoint URL..."
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className={`w-full h-10 px-3.5 bg-white border rounded-xl text-sm text-[#15213D] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#1264F5] ${
                urlError ? "border-destructive" : "border-[#E5EBF5]"
              }`}
            />
            {urlError && <p className="text-xs text-destructive mt-1">{urlError}</p>}
          </div>

          <div className="space-y-2">
            <span className="text-xs font-semibold text-[#15213D] block">
              Subscribed Event Types
            </span>
            <div className="flex flex-wrap gap-4 pt-0.5">
              {[
                { id: "job.completed", label: "job.completed (Audio Ready)" },
                { id: "job.failed", label: "job.failed (Synthesis Error)" },
              ].map((ev) => (
                <label
                  key={ev.id}
                  className="flex items-center gap-2 text-xs text-[#15213D] cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(ev.id)}
                    onChange={() => toggleEvent(ev.id)}
                    className="h-4 w-4 rounded border-[#E5EBF5] text-[#1264F5] focus:ring-[#1264F5]"
                  />
                  <span>{ev.label}</span>
                </label>
              ))}
            </div>
          </div>

          {webhookError && <p className="text-xs text-destructive">{webhookError}</p>}

          <button
            type="button"
            onClick={createWebhook}
            className="inline-flex items-center justify-center gap-1.5 h-9 px-4 rounded-full bg-[#1264F5] hover:bg-[#0E52CC] text-xs font-semibold text-white transition-colors cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Webhook Endpoint</span>
          </button>
        </div>
      </div>

      {/* Webhooks Subscriptions Table */}
      <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
        <h3 className="text-base font-bold text-[#15213D] leading-tight">
          Active Subscriptions
        </h3>

        <div>
          {isLoadingWebhooks ? (
            <div className="py-10 flex justify-center items-center text-sm text-[#64748B]">
              <Loader2 className="h-4 w-4 animate-spin mr-2 text-[#1264F5]" />
              Loading webhooks...
            </div>
          ) : webhooks.length === 0 ? (
            <div className="py-10 text-center text-sm text-[#64748B] border border-dashed border-[#E5EBF5] rounded-2xl">
              No webhook subscriptions registered.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-[#E5EBF5]">
              <Table>
                <TableHeader className="bg-[#F8FAFC]">
                  <TableRow className="border-[#E5EBF5] hover:bg-transparent">
                    <TableHead className="text-xs font-semibold text-[#64748B]">Target URL</TableHead>
                    <TableHead className="text-xs font-semibold text-[#64748B]">Events</TableHead>
                    <TableHead className="text-xs font-semibold text-[#64748B]">Created</TableHead>
                    <TableHead className="text-right text-xs font-semibold text-[#64748B]">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {webhooks.map((sub) => (
                    <TableRow key={sub.id} className="border-[#E5EBF5] hover:bg-[#F8FAFC]/60">
                      <TableCell className="font-mono text-xs font-medium text-[#374151]">
                        {sub.url}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1.5">
                          {(sub.event_types || []).map((e) => (
                            <span
                              key={e}
                              className="inline-flex items-center rounded-full border border-[#E5EBF5] bg-white px-2.5 py-0.5 text-[11px] font-medium text-[#64748B]"
                            >
                              {e}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-[#64748B]">
                        {new Date(sub.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <button
                          type="button"
                          onClick={() => deleteWebhook(sub.id)}
                          className="inline-flex items-center gap-1 h-8 px-3 rounded-full text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          <span>Delete</span>
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
