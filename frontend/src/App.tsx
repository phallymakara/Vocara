import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "@/views/components/Sidebar";
import { Header } from "@/views/components/Header";
import { TTSStudioPage } from "@/views/pages/TTSStudioPage";
import { VoiceLibraryPage } from "@/views/pages/VoiceLibraryPage";
import { ApiKeysPage } from "@/views/pages/ApiKeysPage";
import { UsageMetricsPage } from "@/views/pages/UsageMetricsPage";
import { WebhooksJobsPage } from "@/views/pages/WebhooksJobsPage";

export const App: React.FC = () => {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#F7F9FE]">
      {/* Responsive Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden bg-[#F7F9FE]">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 lg:p-10 relative">
          <Routes>
            <Route path="/" element={<TTSStudioPage />} />
            <Route path="/tts" element={<Navigate to="/" replace />} />
            <Route path="/voices" element={<VoiceLibraryPage />} />
            <Route path="/keys" element={<ApiKeysPage />} />
            <Route path="/usage" element={<UsageMetricsPage />} />
            <Route path="/jobs" element={<WebhooksJobsPage />} />
            <Route path="/webhooks" element={<Navigate to="/jobs" replace />} />
            {/* Fallback to root */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export default App;
