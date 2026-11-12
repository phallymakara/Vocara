import React from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { AuthProvider, useAuth } from "@/controllers/AuthContext";
import { TTSProvider } from "@/controllers/TTSContext";
import { Sidebar } from "@/views/components/Sidebar";
import { Header } from "@/views/components/Header";
import { TTSStudioPage } from "@/views/pages/TTSStudioPage";
import { VoiceLibraryPage } from "@/views/pages/VoiceLibraryPage";
import { ApiKeysPage } from "@/views/pages/ApiKeysPage";
import { UsageMetricsPage } from "@/views/pages/UsageMetricsPage";
import { LoginPage } from "@/views/pages/LoginPage";
import { RegisterPage } from "@/views/pages/RegisterPage";
import { AuthCallbackPage } from "@/views/pages/AuthCallbackPage";

const ProtectedWorkspace: React.FC = () => {
  const { user, isAuthLoading } = useAuth();
  const location = useLocation();

  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-[#F7F9FE] flex items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-[#1264F5]" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <TTSProvider>
      <div className="flex h-screen w-screen overflow-hidden bg-[#F7F9FE]">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden bg-[#F7F9FE]">
          <Header />
          <main className="flex-1 overflow-y-auto p-6 md:p-8 lg:p-10 relative scroll-smooth">
            <div key={location.pathname} className="animate-page-enter">
              <Routes>
                <Route path="/" element={<TTSStudioPage />} />
                <Route path="/tts" element={<Navigate to="/" replace />} />
                <Route path="/voices" element={<VoiceLibraryPage />} />
                <Route path="/keys" element={<ApiKeysPage />} />
                <Route path="/usage" element={<UsageMetricsPage />} />
                <Route path="/jobs" element={<Navigate to="/keys" replace />} />
                <Route path="/webhooks" element={<Navigate to="/keys" replace />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
    </TTSProvider>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/*" element={<ProtectedWorkspace />} />
      </Routes>
    </AuthProvider>
  );
};

export default App;
