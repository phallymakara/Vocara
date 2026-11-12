import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/controllers/AuthContext";

export const AuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const { completeOAuthCallback } = useAuth();

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, "");
    const params = new URLSearchParams(hash);
    const token = params.get("token");
    const defaultApiKey = params.get("api_key");

    if (!token) {
      navigate("/login?error=Google+sign-in+failed.", { replace: true });
      return;
    }

    completeOAuthCallback(token, defaultApiKey)
      .then(() => {
        navigate("/", { replace: true });
      })
      .catch(() => {
        navigate("/login?error=Unable+to+complete+sign-in.", { replace: true });
      });
  }, [completeOAuthCallback, navigate]);

  return (
    <div className="min-h-screen bg-[#F7F9FE] flex items-center justify-center p-6">
      <div className="flex items-center gap-2.5 text-sm text-[#64748B]">
        <Loader2 className="h-4 w-4 animate-spin text-[#1264F5]" />
        <span>Completing sign-in...</span>
      </div>
    </div>
  );
};

