import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Key } from "lucide-react";
import { apiClient } from "@/controllers/apiClient";

interface HeaderProps {
  onNavigateKeys?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onNavigateKeys }) => {
  const navigate = useNavigate();
  const [apiKey, setApiKey] = useState<string | null>(apiClient.getApiKey());

  const handleNavigateToKeys = () => {
    if (onNavigateKeys) {
      onNavigateKeys();
    } else {
      navigate("/keys");
    }
  };

  useEffect(() => {
    const checkKeyInterval = setInterval(() => {
      setApiKey(apiClient.getApiKey());
    }, 1000);

    return () => clearInterval(checkKeyInterval);
  }, []);

  const formatMaskedKey = (key: string) => {
    if (key.length <= 12) return key;
    return `${key.slice(0, 8)}...${key.slice(-4)}`;
  };

  return (
    <header className="h-16 px-6 md:px-8 bg-white border-b border-[#E8EDF5] flex items-center justify-between relative z-20">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-[#15213D] tracking-tight">
          Vocara Voice Studio
        </h1>
      </div>

      <div className="flex items-center gap-2 text-xs">
        {apiKey ? (
          <div className="flex items-center gap-2 text-[#64748B]">
            <Key className="h-3.5 w-3.5 text-[#1264F5]" />
            <span className="text-[#15213D] font-normal">
              Key: <span className="font-mono font-medium">{formatMaskedKey(apiKey)}</span>
            </span>
            <button
              type="button"
              onClick={handleNavigateToKeys}
              className="text-[#1264F5] hover:underline font-medium ml-1 transition-colors"
            >
              Change
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={handleNavigateToKeys}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#1264F5] bg-[#EBF2FE] hover:bg-[#DCE9FE] transition-colors"
          >
            <Key className="h-3.5 w-3.5" />
            <span>Set API Key</span>
          </button>
        )}
      </div>
    </header>
  );
};
