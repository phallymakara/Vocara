import { useState, useEffect, useCallback } from "react";
import { apiClient, ApiError } from "@/controllers/apiClient";
import type { ApiKeyItem, ApiKeyCreated } from "@/models/types";

const SAVED_KEYS_STORAGE_KEY = "vocara_saved_api_keys";

function readSavedKeySecrets(): Record<string, string> {
  try {
    const raw = localStorage.getItem(SAVED_KEYS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : {};
  } catch {
    return {};
  }
}

function writeSavedKeySecrets(map: Record<string, string>): void {
  try {
    localStorage.setItem(SAVED_KEYS_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore storage quota errors
  }
}

export function useKeyController() {
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [savedSecrets, setSavedSecrets] = useState<Record<string, string>>(() => readSavedKeySecrets());
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [newKeyName, setNewKeyName] = useState<string>("");
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [activeKeyInput, setActiveKeyInput] = useState<string>(apiClient.getApiKey() || "");
  const [nameError, setNameError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);

  // Edit Key Name Modal State
  const [editingKey, setEditingKey] = useState<ApiKeyItem | null>(null);
  const [editKeyName, setEditKeyName] = useState<string>("");
  const [isUpdatingKey, setIsUpdatingKey] = useState<boolean>(false);
  const [editNameError, setEditNameError] = useState<string | null>(null);

  // Delete Key Confirmation Modal State
  const [deleteConfirmKey, setDeleteConfirmKey] = useState<ApiKeyItem | null>(null);
  const [isDeletingKey, setIsDeletingKey] = useState<boolean>(false);

  const loadKeys = useCallback(async () => {
    setIsLoading(true);
    setGeneralError(null);
    try {
      const data = await apiClient.listKeys();
      setKeys(data);

      // Backfill currently active secret into local secret map if it matches a listed key prefix
      const activeRaw = apiClient.getApiKey()?.trim() || "";
      if (activeRaw.startsWith("voc_")) {
        const prefix = activeRaw.slice(0, 16);
        const matched = data.find((k) => k.key_prefix === prefix && k.status === "active");
        if (matched) {
          setSavedSecrets((prev) => {
            if (prev[matched.id] === activeRaw) return prev;
            const next = { ...prev, [matched.id]: activeRaw };
            writeSavedKeySecrets(next);
            return next;
          });
        }
      }
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

  const openCreateModal = () => {
    setNewKeyName("");
    setNameError(null);
    setGeneralError(null);
    setIsCreateModalOpen(true);
  };

  const closeCreateModal = () => {
    setIsCreateModalOpen(false);
    setNewKeyName("");
    setNameError(null);
    setGeneralError(null);
  };

  const createKey = async (): Promise<boolean> => {
    setNameError(null);
    setGeneralError(null);

    const trimmed = newKeyName.trim();
    if (!trimmed) {
      setNameError("Please enter a name for your API key.");
      return false;
    }
    if (trimmed.length < 2) {
      setNameError("Key name must be at least 2 characters.");
      return false;
    }

    setIsCreating(true);
    try {
      const created = await apiClient.createKey(trimmed);
      setCreatedKey(created);
      setNewKeyName("");
      setIsCreateModalOpen(false);
      // Persist raw key locally so user can copy it from the table later
      setSavedSecrets((prev) => {
        const next = { ...prev, [created.id]: created.api_key };
        writeSavedKeySecrets(next);
        return next;
      });
      // Automatically set this newly created key as the active key in the client
      apiClient.setApiKey(created.api_key);
      setActiveKeyInput(created.api_key);
      await loadKeys();
      return true;
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
      return false;
    } finally {
      setIsCreating(false);
    }
  };

  const openEditModal = (key: ApiKeyItem) => {
    setEditingKey(key);
    setEditKeyName(key.name);
    setEditNameError(null);
  };

  const closeEditModal = () => {
    setEditingKey(null);
    setEditKeyName("");
    setEditNameError(null);
  };

  const submitEditKey = async (): Promise<boolean> => {
    if (!editingKey) return false;
    setEditNameError(null);
    const trimmed = editKeyName.trim();
    if (!trimmed) {
      setEditNameError("Please enter a key name.");
      return false;
    }
    if (trimmed.length < 2) {
      setEditNameError("Key name must be at least 2 characters.");
      return false;
    }

    setIsUpdatingKey(true);
    try {
      await apiClient.updateKeyName(editingKey.id, trimmed);
      closeEditModal();
      await loadKeys();
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setEditNameError(err.fieldErrors?.name || err.message);
      } else {
        setEditNameError("Failed to update API key name.");
      }
      return false;
    } finally {
      setIsUpdatingKey(false);
    }
  };

  const clearIfActiveKey = (key: ApiKeyItem) => {
    const activeRaw = apiClient.getApiKey()?.trim() || "";
    const cachedSecret = savedSecrets[key.id];
    if (
      (cachedSecret && activeRaw === cachedSecret) ||
      (activeRaw && activeRaw.startsWith(key.key_prefix))
    ) {
      apiClient.setApiKey(null);
      setActiveKeyInput("");
    }
  };

  const revokeKey = async (key: ApiKeyItem) => {
    setGeneralError(null);
    try {
      await apiClient.revokeKey(key.id);
      clearIfActiveKey(key);
      await loadKeys();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Failed to revoke API key.");
      }
    }
  };

  const openDeleteConfirm = (key: ApiKeyItem) => {
    setDeleteConfirmKey(key);
  };

  const closeDeleteConfirm = () => {
    setDeleteConfirmKey(null);
  };

  const submitDeleteKey = async (): Promise<boolean> => {
    if (!deleteConfirmKey) return false;
    setGeneralError(null);
    setIsDeletingKey(true);
    try {
      const target = deleteConfirmKey;
      await apiClient.deleteKey(target.id);
      clearIfActiveKey(target);
      setSavedSecrets((prev) => {
        if (!(target.id in prev)) return prev;
        const next = { ...prev };
        delete next[target.id];
        writeSavedKeySecrets(next);
        return next;
      });
      setDeleteConfirmKey(null);
      await loadKeys();
      return true;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Failed to delete API key.");
      }
      return false;
    } finally {
      setIsDeletingKey(false);
    }
  };

  const copyKeyById = async (key: ApiKeyItem) => {
    const fullSecret = savedSecrets[key.id];
    if (!fullSecret) return;
    try {
      await navigator.clipboard.writeText(fullSecret);
      setCopiedKeyId(key.id);
      setTimeout(() => setCopiedKeyId((prev) => (prev === key.id ? null : prev)), 2000);
    } catch {
      // Fallback
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
    savedSecrets,
    copiedKeyId,
    isLoading,
    isCreating,
    isCreateModalOpen,
    openCreateModal,
    closeCreateModal,
    newKeyName,
    setNewKeyName,
    createdKey,
    copied,
    activeKeyInput,
    setActiveKeyInput,
    nameError,
    generalError,
    saveSuccessMessage,
    editingKey,
    editKeyName,
    setEditKeyName,
    isUpdatingKey,
    editNameError,
    openEditModal,
    closeEditModal,
    submitEditKey,
    deleteConfirmKey,
    isDeletingKey,
    openDeleteConfirm,
    closeDeleteConfirm,
    submitDeleteKey,
    loadKeys,
    createKey,
    revokeKey,
    copyKeyById,
    saveActiveKey,
    copyToClipboard,
    closeCreatedModal,
  };
}
