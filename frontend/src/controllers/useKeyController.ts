import { useState, useEffect, useCallback } from "react";
import { apiClient, ApiError } from "@/controllers/apiClient";
import type { ApiKeyItem, ApiKeyCreated } from "@/models/types";

export function useKeyController() {
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [newKeyName, setNewKeyName] = useState<string>("");
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [activeKeyInput, setActiveKeyInput] = useState<string>(apiClient.getApiKey() || "");
  const [nameError, setNameError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);

  const loadKeys = useCallback(async () => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const data = await apiClient.listKeys();
      setKeys(data);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Could not load API keys. Please verify your connection.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  const createKey = async () => {
    setNameError(null);
    setGeneralError(null);

    if (!newKeyName.trim()) {
      setNameError("Please enter a name for your API key.");
      return;
    }

    try {
      const created = await apiClient.createKey(newKeyName.trim());
      setCreatedKey(created);
      setNewKeyName("");
      // Automatically set this newly created key as the active key in the client
      apiClient.setApiKey(created.api_key);
      setActiveKeyInput(created.api_key);
      await loadKeys();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.fieldErrors?.name) {
          setNameError(err.fieldErrors.name);
        } else {
          setGeneralError(err.message);
        }
      } else {
        setGeneralError("Unable to create API key. Please try again.");
      }
    }
  };

  const revokeKey = async (id: string) => {
    setGeneralError(null);
    try {
      await apiClient.revokeKey(id);
      await loadKeys();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Failed to revoke API key.");
      }
    }
  };

  const saveActiveKey = () => {
    const trimmed = activeKeyInput.trim();
    if (!trimmed) {
      apiClient.setApiKey(null);
      setSaveSuccessMessage("API key cleared.");
    } else {
      apiClient.setApiKey(trimmed);
      setSaveSuccessMessage("Active API key updated.");
    }
    setTimeout(() => setSaveSuccessMessage(null), 3000);
    loadKeys();
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const closeCreatedModal = () => {
    setCreatedKey(null);
    setCopied(false);
  };

  return {
    keys,
    isLoading,
    newKeyName,
    setNewKeyName,
    createdKey,
    copied,
    activeKeyInput,
    setActiveKeyInput,
    nameError,
    generalError,
    saveSuccessMessage,
    loadKeys,
    createKey,
    revokeKey,
    saveActiveKey,
    copyToClipboard,
    closeCreatedModal,
  };
}
