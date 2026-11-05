import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Key, CheckCircle2, AlertCircle } from "lucide-react";
import { apiClient } from "@/controllers/apiClient";
import { Badge } from "@/views/components/ui/badge";
import { Button } from "@/views/components/ui/button";

interface HeaderProps {
  onNavigateKeys?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onNavigateKeys }) => {
  const navigate = useNavigate();
  const [apiKey, setApiKey] = useState<string | null>(apiClient.getApiKey());
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  const handleNavigateToKeys = () => {
    if (onNavigateKeys) {
      onNavigateKeys();
    } else {
      navigate("/keys");
    }
  };

  useEffect(() => {
    apiClient
      .getHealth()
      .then(() => setIsHealthy(true))
      .catch(() => setIsHealthy(false));

    const checkKeyInterval = setInterval(() => {
      setApiKey(apiClient.getApiKey());
    }, 1000);

    return () => clearInterval(checkKeyInterval);
  }, []);

  return (
    <header className="h-16 px-6 border-b border-border bg-background flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-foreground tracking-tight">
          Vocara Voice Studio
        </h1>
        {isHealthy !== null && (
          <Badge
            variant={isHealthy ? "secondary" : "destructive"}
            className="flex items-center gap-1.5 text-xs font-normal"
          >
            {isHealthy ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            ) : (
              <AlertCircle className="h-3.5 w-3.5" />
            )}
            <span>{isHealthy ? "Engine Ready" : "Offline"}</span>
          </Badge>
        )}
      </div>

      <div className="flex items-center gap-3">
        {apiKey ? (
          <div className="flex items-center gap-2 px-3 py-1.5 border border-border rounded text-xs text-muted-foreground">
            <Key className="h-3.5 w-3.5 text-sky-600" />
            <span>Key:</span>
            <span className="font-mono text-foreground font-medium">
              {apiKey.slice(0, 8)}...{apiKey.slice(-4)}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleNavigateToKeys}
              className="h-6 px-2 text-xs text-sky-600 hover:text-sky-700"
            >
              Change
            </Button>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={handleNavigateToKeys}
            className="text-xs border-destructive text-destructive hover:bg-destructive/10"
          >
            <Key className="h-3.5 w-3.5 mr-1.5" />
            Set API Key
          </Button>
        )}
      </div>
    </header>
  );
};
