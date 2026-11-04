import React, { useState } from "react";
import { Sidebar, type NavTab } from "@/views/components/Sidebar";
import { Header } from "@/views/components/Header";
import { TTSStudioPage } from "@/views/pages/TTSStudioPage";
import { VoiceLibraryPage } from "@/views/pages/VoiceLibraryPage";
import { ApiKeysPage } from "@/views/pages/ApiKeysPage";
import { UsageMetricsPage } from "@/views/pages/UsageMetricsPage";
import { WebhooksJobsPage } from "@/views/pages/WebhooksJobsPage";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>("tts");

  const navigateToKeys = () => setActiveTab("keys");

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Sidebar with responsive product name hiding on mobile */}
      <Sidebar activeTab={activeTab} onSelectTab={setActiveTab} />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header onNavigateKeys={navigateToKeys} />
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          {activeTab === "tts" && <TTSStudioPage />}
          {activeTab === "voices" && <VoiceLibraryPage />}
          {activeTab === "keys" && <ApiKeysPage />}
          {activeTab === "usage" && <UsageMetricsPage />}
          {activeTab === "webhooks" && <WebhooksJobsPage />}
        </main>
      </div>
    </div>
  );
};

export default App;
