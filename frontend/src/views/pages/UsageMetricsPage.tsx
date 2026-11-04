import React from "react";
import { Clock, ShieldCheck, Loader2 } from "lucide-react";
import { useUsageController } from "@/controllers/useUsageController";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/views/components/ui/card";
import { Progress } from "@/views/components/ui/progress";
import { Badge } from "@/views/components/ui/badge";

export const UsageMetricsPage: React.FC = () => {
  const {
    usage,
    isLoading,
    generalError,
    percentUsed,
    charactersRemaining,
  } = useUsageController();

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          Usage & Quota Allocation
        </h2>
        <p className="text-sm text-muted-foreground">
          Real-time metrics on character consumption and rate limits.
        </p>
      </div>

      {generalError && (
        <p className="text-xs text-destructive">{generalError}</p>
      )}

      {isLoading ? (
        <div className="py-12 flex justify-center items-center text-sm text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          Retrieving usage metrics...
        </div>
      ) : !usage ? (
        <div className="py-8 text-center text-sm text-muted-foreground border border-dashed rounded">
          No usage information available. Make sure an active API key is set.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Main Monthly Quota Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Monthly Character Quota</CardTitle>
                  <CardDescription>
                    Resets automatically at the beginning of each billing cycle.
                  </CardDescription>
                </div>
                <Badge variant="outline" className="text-xs font-medium">
                  Active Period
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between items-baseline text-sm">
                  <div className="space-x-1">
                    <span className="text-2xl font-bold tracking-tight text-foreground font-mono">
                      {usage.characters_used.toLocaleString()}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      / {usage.total_quota.toLocaleString()} chars
                    </span>
                  </div>
                  <span className="font-mono text-xs font-semibold text-foreground">
                    {percentUsed}% used
                  </span>
                </div>
                <Progress value={percentUsed} className="h-2.5" />
              </div>

              <div className="flex flex-col sm:flex-row justify-between text-xs text-muted-foreground pt-2 border-t border-border gap-2">
                <div>
                  <span>Remaining quota: </span>
                  <strong className="text-foreground font-mono">
                    {charactersRemaining.toLocaleString()} characters
                  </strong>
                </div>
                <div>
                  <span>Billing Period: </span>
                  <span className="font-medium text-foreground">
                    Month {usage.month}, {usage.year}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Metric Stats Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Card>
              <CardContent className="pt-6 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium">
                  <Clock className="h-4 w-4 text-sky-600" />
                  <span>Consumed This Period</span>
                </div>
                <div className="text-2xl font-bold font-mono text-foreground">
                  {usage.characters_used.toLocaleString()}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Total characters synthesized in {usage.month}/{usage.year}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6 space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <span>Remaining Allowance</span>
                </div>
                <div className="text-2xl font-bold font-mono text-foreground">
                  {usage.quota_remaining.toLocaleString()}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Available quota until next billing period
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};
