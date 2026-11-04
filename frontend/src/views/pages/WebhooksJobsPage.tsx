import React from "react";
import { Search, Download, Trash2, Plus, Loader2 } from "lucide-react";
import { useWebhookController } from "@/controllers/useWebhookController";
import { Button } from "@/views/components/ui/button";
import { Input } from "@/views/components/ui/input";
import { Label } from "@/views/components/ui/label";
import { Badge } from "@/views/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/views/components/ui/card";
import { Progress } from "@/views/components/ui/progress";
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
    jobIdInput,
    setJobIdInput,
    inspectedJob,
    isInspectingJob,
    jobSearchError,
    createWebhook,
    deleteWebhook,
    inspectJob,
    downloadJobAudio,
  } = useWebhookController();

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Jobs & Webhook Dispatcher
        </h2>
        <p className="text-sm text-muted-foreground">
          Monitor asynchronous batch synthesis tasks and register webhook callbacks for completed audio.
        </p>
      </div>

      {/* Job Lookup Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Inspect Background Job</CardTitle>
          <CardDescription>
            Query real-time status and retrieve audio for synthesis jobs exceeding 250 characters.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-2 items-start">
            <div className="flex-1 w-full space-y-1">
              <Input
                placeholder="Enter Job ID..."
                value={jobIdInput}
                onChange={(e) => setJobIdInput(e.target.value)}
                error={Boolean(jobSearchError)}
                className="font-mono text-xs"
              />
              {jobSearchError && (
                <p className="text-xs text-destructive">{jobSearchError}</p>
              )}
            </div>
            <Button
              onClick={inspectJob}
              disabled={isInspectingJob}
              className="w-full sm:w-auto"
            >
              {isInspectingJob ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Search className="h-4 w-4 mr-1.5" />
                  Inspect Job
                </>
              )}
            </Button>
          </div>

          {/* Inspected Job Details */}
          {inspectedJob && (
            <div className="p-4 border border-border rounded-md space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs text-muted-foreground font-mono">Job ID: {inspectedJob.id}</span>
                </div>
                <Badge
                  variant={
                    inspectedJob.status === "completed"
                      ? "default"
                      : inspectedJob.status === "failed"
                      ? "destructive"
                      : "secondary"
                  }
                  className="capitalize text-xs"
                >
                  {inspectedJob.status}
                </Badge>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Job State</span>
                  <span className="font-mono capitalize">{inspectedJob.status}</span>
                </div>
                <Progress
                  value={
                    inspectedJob.status === "completed"
                      ? 100
                      : inspectedJob.status === "processing"
                      ? 60
                      : 25
                  }
                  className="h-2"
                />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-xs border-t border-border">
                <div>
                  <span className="text-muted-foreground block">Voice ID</span>
                  <span className="font-mono font-medium">{inspectedJob.voice_id?.slice(0, 8)}...</span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Characters</span>
                  <span className="font-medium font-mono">{inspectedJob.char_count}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Format</span>
                  <span className="font-medium uppercase">{inspectedJob.output_format}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Created</span>
                  <span className="font-medium">{new Date(inspectedJob.created_at).toLocaleTimeString()}</span>
                </div>
              </div>

              {inspectedJob.status === "completed" && (
                <div className="pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => downloadJobAudio(inspectedJob.id)}
                    className="text-xs gap-1.5"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Rendered Audio
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Register Webhook Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Register Webhook Endpoint</CardTitle>
          <CardDescription>
            Receive HTTP POST notifications when long-form batch audio completes or encounters an issue.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="webhook-url">Target URL</Label>
            <Input
              id="webhook-url"
              placeholder="Enter webhook endpoint URL..."
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              error={Boolean(urlError)}
            />
            {urlError && <p className="text-xs text-destructive mt-1">{urlError}</p>}
          </div>

          <div className="space-y-2">
            <Label>Subscribed Event Types</Label>
            <div className="flex flex-wrap gap-4 pt-1">
              {[
                { id: "job.completed", label: "job.completed (Audio Ready)" },
                { id: "job.failed", label: "job.failed (Synthesis Error)" },
              ].map((ev) => (
                <label key={ev.id} className="flex items-center gap-2 text-xs cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(ev.id)}
                    onChange={() => toggleEvent(ev.id)}
                    className="rounded border-input text-primary focus:ring-primary"
                  />
                  <span>{ev.label}</span>
                </label>
              ))}
            </div>
          </div>

          {webhookError && <p className="text-xs text-destructive">{webhookError}</p>}

          <Button onClick={createWebhook} size="sm">
            <Plus className="h-4 w-4 mr-1.5" />
            Add Webhook Endpoint
          </Button>
        </CardContent>
      </Card>

      {/* Webhooks Subscriptions Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Active Subscriptions</CardTitle>
          <CardDescription>
            Registered endpoints that receive event payloads with HMAC signature headers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingWebhooks ? (
            <div className="py-8 flex justify-center items-center text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Loading webhooks...
            </div>
          ) : webhooks.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground border border-dashed rounded">
              No webhook subscriptions registered.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Target URL</TableHead>
                  <TableHead>Events</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {webhooks.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell className="font-mono text-xs font-medium">
                      {sub.url}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {(sub.event_types || []).map((e) => (
                          <Badge key={e} variant="secondary" className="text-[10px]">
                            {e}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(sub.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteWebhook(sub.id)}
                        className="h-8 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
