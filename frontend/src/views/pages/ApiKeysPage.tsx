import React, { useState, useEffect, useRef } from "react";
import { Copy, Check, Trash2, Plus, ShieldAlert, Loader2, MoreVertical, Edit2, Ban } from "lucide-react";
import { useKeyController } from "@/controllers/useKeyController";
import { useWebhookController } from "@/controllers/useWebhookController";
import { Button } from "@/views/components/ui/button";
import { Input } from "@/views/components/ui/input";
import { Label } from "@/views/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/views/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/views/components/ui/dialog";

import type { ApiKeyItem } from "@/models/types";

export const ApiKeysPage: React.FC = () => {
  const {
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
    nameError,
    generalError,
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
    createKey,
    revokeKey,
    copyKeyById,
    copyToClipboard,
    closeCreatedModal,
  } = useKeyController();

  const {
    webhooks,
    isLoadingWebhooks,
    targetUrl,
    setTargetUrl,
    selectedEvents,
    toggleEvent,
    urlError,
    webhookError,
    createWebhook,
    deleteWebhook,
  } = useWebhookController();

  const [selectedMcpTab, setSelectedMcpTab] = useState<"cursor" | "claude" | "python" | "typescript">("cursor");
  const [copiedEndpoint, setCopiedEndpoint] = useState(false);
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [openMenu, setOpenMenu] = useState<{
    key: ApiKeyItem;
    top: number;
    right: number;
  } | null>(null);
  const actionMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!openMenu) return;
    const handleOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (target.closest("[data-key-menu-trigger='true']")) return;
      if (actionMenuRef.current && !actionMenuRef.current.contains(target)) {
        setOpenMenu(null);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpenMenu(null);
    };
    const handleScrollOrResize = () => setOpenMenu(null);
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("keydown", handleEscape);
    window.addEventListener("resize", handleScrollOrResize);
    window.addEventListener("scroll", handleScrollOrResize, true);
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("keydown", handleEscape);
      window.removeEventListener("resize", handleScrollOrResize);
      window.removeEventListener("scroll", handleScrollOrResize, true);
    };
  }, [openMenu]);

  const baseUrl =
    (import.meta.env.VITE_MCP_BASE_URL as string | undefined)?.replace(/\/+$/, "") ||
    (typeof window !== "undefined" ? window.location.origin : "");

  const trimmedActiveKey = activeKeyInput?.trim() || "";
  const effectiveKey = trimmedActiveKey.startsWith("voc_") ? trimmedActiveKey : "voc_YOUR_API_KEY";
  const sseEndpointUrl = `${baseUrl}/mcp/sse?api_key=${effectiveKey}`;

  const snippetMap = {
    cursor: JSON.stringify(
      {
        mcpServers: {
          vocara: {
            url: sseEndpointUrl,
          },
        },
      },
      null,
      2
    ),
    claude: JSON.stringify(
      {
        mcpServers: {
          vocara: {
            url: sseEndpointUrl,
          },
        },
      },
      null,
      2
    ),
    python: `import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    url = "${sseEndpointUrl}"
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 1. Discover voices
            voices = await session.call_tool("vocara_list_voices", {"language": "km"})
            print("Voices:", voices)
            
            # 2. Synthesize speech
            result = await session.call_tool("vocara_generate_speech", {
                "text": voices[0]["sample_text"] if voices else "Hello",
                "voice_id": voices[0]["id"],
                "output_format": "mp3"
            })
            print("Synthesis result:", result)

asyncio.run(main())`,
    typescript: `import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function main() {
  const transport = new SSEClientTransport(
    new URL("${sseEndpointUrl}")
  );

  const client = new Client(
    { name: "vocara-agent", version: "1.0.0" },
    { capabilities: {} }
  );

  await client.connect(transport);

  // List voices
  const voices = await client.callTool({
    name: "vocara_list_voices",
    arguments: { language: "all" },
  });
  console.log("Vocara voices:", voices);
}

main().catch(console.error);`,
  };

  const copySnippet = () => {
    navigator.clipboard.writeText(snippetMap[selectedMcpTab]);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const toggleRowMenu = (event: React.MouseEvent<HTMLButtonElement>, keyItem: ApiKeyItem) => {
    if (openMenu?.key.id === keyItem.id) {
      setOpenMenu(null);
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const estimatedMenuHeight = 176;
    const opensUpward = rect.bottom + estimatedMenuHeight > window.innerHeight - 16;
    setOpenMenu({
      key: keyItem,
      top: opensUpward ? Math.max(12, rect.top - estimatedMenuHeight) : rect.bottom + 6,
      right: Math.max(12, window.innerWidth - rect.right),
    });
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Keys Table */}
      <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h3 className="text-base font-bold text-[#15213D] leading-tight">Issued Keys</h3>
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center justify-center gap-1.5 h-9 px-4 rounded-full bg-[#1264F5] hover:bg-[#0E52CC] text-xs font-semibold text-white transition-colors cursor-pointer w-full sm:w-auto"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Generate Key</span>
          </button>
        </div>

        <div className="space-y-3">
          {generalError && !isCreateModalOpen && (
            <p className="text-xs text-destructive">{generalError}</p>
          )}
          {isLoading ? (
            <div className="py-10 flex justify-center items-center text-sm text-[#64748B]">
              <Loader2 className="h-4 w-4 animate-spin mr-2 text-[#1264F5]" />
              Loading API keys...
            </div>
          ) : keys.length === 0 ? (
            <div className="py-10 text-center text-sm text-[#64748B] border border-dashed border-[#E5EBF5] rounded-2xl">
              No API keys found. Click Generate Key to create one.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-[#E5EBF5]">
              <Table>
                <TableHeader className="bg-[#F8FAFC]">
                  <TableRow className="border-[#E5EBF5] hover:bg-transparent">
                    <TableHead className="text-xs font-semibold text-[#64748B]">Key Name</TableHead>
                    <TableHead className="text-xs font-semibold text-[#64748B]">Key Prefix</TableHead>
                    <TableHead className="text-xs font-semibold text-[#64748B]">Created</TableHead>
                    <TableHead className="text-xs font-semibold text-[#64748B]">Status</TableHead>
                    <TableHead className="text-right text-xs font-semibold text-[#64748B]">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys.map((k) => {
                    const isActive = k.status === "active";
                    const hasSavedSecret = Boolean(savedSecrets[k.id]);
                    const isRowCopied = copiedKeyId === k.id;
                    return (
                      <TableRow key={k.id} className="border-[#E5EBF5] hover:bg-[#F8FAFC]/60">
                        <TableCell className="font-medium text-sm text-[#15213D]">{k.name}</TableCell>
                        <TableCell className="font-mono text-xs text-[#64748B]">
                          <div className="inline-flex items-center gap-2">
                            <span>{k.key_prefix}...</span>
                            {hasSavedSecret && (
                              <button
                                type="button"
                                onClick={() => copyKeyById(k)}
                                title="Copy full API key"
                                aria-label={`Copy ${k.name} API key`}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-[#E5EBF5] bg-white hover:bg-[#F8FAFC] hover:border-[#1264F5]/40 text-[11px] font-sans font-medium text-[#64748B] hover:text-[#15213D] transition-colors cursor-pointer"
                              >
                                {isRowCopied ? (
                                  <>
                                    <Check className="h-3 w-3 text-emerald-600" />
                                    <span className="text-emerald-600">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="h-3 w-3" />
                                    <span>Copy</span>
                                  </>
                                )}
                              </button>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-xs text-[#64748B]">
                          {new Date(k.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          {isActive ? (
                            <span className="text-xs font-medium text-emerald-600">
                              Active
                            </span>
                          ) : (
                            <span className="text-xs font-medium text-[#64748B]">
                              Revoked
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <button
                            type="button"
                            data-key-menu-trigger="true"
                            onClick={(e) => toggleRowMenu(e, k)}
                            aria-label={`Actions for ${k.name}`}
                            aria-expanded={openMenu?.key.id === k.id}
                            className="h-8 w-8 rounded-full inline-flex items-center justify-center text-[#64748B] hover:text-[#15213D] hover:bg-[#F8FAFC] transition-colors cursor-pointer"
                          >
                            <MoreVertical className="h-4 w-4" />
                          </button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>

      {/* Anchored Three-Dot Action Menu */}
      {openMenu && (
        <div
          ref={actionMenuRef}
          role="menu"
          style={{ top: `${openMenu.top}px`, right: `${openMenu.right}px` }}
          className="fixed z-50 w-44 rounded-2xl border border-[#E5EBF5] bg-white p-1.5 space-y-0.5"
        >
          {savedSecrets[openMenu.key.id] && (
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                copyKeyById(openMenu.key);
                setOpenMenu(null);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-[#15213D] hover:bg-[#F8FAFC] transition-colors cursor-pointer text-left"
            >
              <Copy className="h-3.5 w-3.5 text-[#64748B]" />
              <span>Copy Key</span>
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              openEditModal(openMenu.key);
              setOpenMenu(null);
            }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-[#15213D] hover:bg-[#F8FAFC] transition-colors cursor-pointer text-left"
          >
            <Edit2 className="h-3.5 w-3.5 text-[#64748B]" />
            <span>Edit Name</span>
          </button>
          {openMenu.key.status === "active" && (
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                const target = openMenu.key;
                setOpenMenu(null);
                revokeKey(target);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-[#15213D] hover:bg-[#F8FAFC] transition-colors cursor-pointer text-left"
            >
              <Ban className="h-3.5 w-3.5 text-[#64748B]" />
              <span>Revoke Key</span>
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              openDeleteConfirm(openMenu.key);
              setOpenMenu(null);
            }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-destructive hover:bg-destructive/5 transition-colors cursor-pointer text-left"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Delete Key</span>
          </button>
        </div>
      )}

      {/* Model Context Protocol (MCP) Integration */}
      <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
        <h3 className="text-base font-bold text-[#15213D] leading-tight">
          Model Context Protocol (MCP) Integration
        </h3>

        <div className="space-y-5">
          <div className="space-y-1.5">
            <label htmlFor="mcp-sse-endpoint" className="text-xs font-semibold text-[#15213D] block">
              Remote SSE Endpoint
            </label>
            <div className="flex gap-2">
              <input
                id="mcp-sse-endpoint"
                readOnly
                value={sseEndpointUrl}
                className="flex-1 h-10 px-3.5 bg-white border border-[#E5EBF5] rounded-xl font-mono text-xs text-[#374151] select-all focus:outline-none focus:border-[#1264F5]"
              />
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(sseEndpointUrl);
                  setCopiedEndpoint(true);
                  setTimeout(() => setCopiedEndpoint(false), 2000);
                }}
                aria-label="Copy Remote SSE Endpoint"
                title="Copy Remote SSE Endpoint"
                className="h-10 w-10 rounded-xl border border-[#E5EBF5] bg-white hover:bg-[#F8FAFC] hover:border-[#1264F5]/40 text-[#64748B] hover:text-[#15213D] inline-flex items-center justify-center flex-shrink-0 transition-colors cursor-pointer"
              >
                {copiedEndpoint ? (
                  <Check className="h-4 w-4 text-emerald-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex flex-wrap items-center gap-2">
                {[
                  { id: "cursor" as const, label: "Cursor IDE" },
                  { id: "claude" as const, label: "Claude Desktop" },
                  { id: "python" as const, label: "Python SDK" },
                  { id: "typescript" as const, label: "TypeScript" },
                ].map((tab) => {
                  const isActive = selectedMcpTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setSelectedMcpTab(tab.id)}
                      className={`h-8 px-3.5 rounded-full border text-xs transition-colors cursor-pointer ${
                        isActive
                          ? "border-[#1264F5] bg-[#1264F5] hover:bg-[#0E52CC] text-white font-semibold"
                          : "border-[#E5EBF5] bg-white text-[#64748B] font-medium hover:text-[#15213D] hover:bg-[#F8FAFC]"
                      }`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              <button
                type="button"
                onClick={copySnippet}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[#E5EBF5] bg-white text-xs font-medium text-[#64748B] hover:text-[#15213D] hover:bg-[#F8FAFC] transition-colors cursor-pointer"
              >
                {copiedSnippet ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600" />
                    <span className="text-emerald-600">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy Config</span>
                  </>
                )}
              </button>
            </div>

            <div className="relative">
              <pre className="p-4 bg-white rounded-2xl border border-[#E5EBF5] text-xs font-mono overflow-x-auto text-[#374151] whitespace-pre leading-relaxed">
                {snippetMap[selectedMcpTab]}
              </pre>
            </div>
          </div>
        </div>
      </div>

      {/* Register Webhook Endpoint */}
      <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
        <h3 className="text-base font-bold text-[#15213D] leading-tight">
          Register Webhook Endpoint
        </h3>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="webhook-url" className="text-xs font-semibold text-[#15213D] block">
              Target URL
            </label>
            <input
              id="webhook-url"
              type="text"
              placeholder="Enter webhook endpoint URL..."
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className={`w-full h-10 px-3.5 bg-white border rounded-xl text-sm text-[#15213D] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#1264F5] ${
                urlError ? "border-destructive" : "border-[#E5EBF5]"
              }`}
            />
            {urlError && <p className="text-xs text-destructive mt-1">{urlError}</p>}
          </div>

          <div className="space-y-2">
            <span className="text-xs font-semibold text-[#15213D] block">
              Subscribed Event Types
            </span>
            <div className="flex flex-wrap gap-4 pt-0.5">
              {[
                { id: "job.completed", label: "job.completed (Audio Ready)" },
                { id: "job.failed", label: "job.failed (Synthesis Error)" },
              ].map((ev) => (
                <label
                  key={ev.id}
                  className="flex items-center gap-2 text-xs text-[#15213D] cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(ev.id)}
                    onChange={() => toggleEvent(ev.id)}
                    className="h-4 w-4 rounded border-[#E5EBF5] text-[#1264F5] focus:ring-[#1264F5]"
                  />
                  <span>{ev.label}</span>
                </label>
              ))}
            </div>
          </div>

          {webhookError && <p className="text-xs text-destructive">{webhookError}</p>}

          <button
            type="button"
            onClick={createWebhook}
            className="inline-flex items-center justify-center gap-1.5 h-9 px-4 rounded-full bg-[#1264F5] hover:bg-[#0E52CC] text-xs font-semibold text-white transition-colors cursor-pointer"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Webhook Endpoint</span>
          </button>
        </div>
      </div>

      {/* Active Webhook Subscriptions */}
      <div className="bg-white border border-[#E5EBF5] rounded-3xl p-6 md:p-8 space-y-5">
        <h3 className="text-base font-bold text-[#15213D] leading-tight">
          Active Subscriptions
        </h3>

        <div>
          {isLoadingWebhooks ? (
            <div className="py-10 flex justify-center items-center text-sm text-[#64748B]">
              <Loader2 className="h-4 w-4 animate-spin mr-2 text-[#1264F5]" />
              Loading webhooks...
            </div>
          ) : webhooks.length === 0 ? (
            <div className="py-10 text-center text-sm text-[#64748B]">
              No webhook subscriptions registered.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-[#E5EBF5]">
              <Table>
                <TableHeader className="bg-[#F8FAFC]">
                  <TableRow className="border-[#E5EBF5] hover:bg-transparent">
                    <TableHead className="text-xs font-semibold text-[#64748B]">Target URL</TableHead>
                    <TableHead className="text-xs font-semibold text-[#64748B]">Events</TableHead>
                    <TableHead className="text-xs font-semibold text-[#64748B]">Created</TableHead>
                    <TableHead className="text-right text-xs font-semibold text-[#64748B]">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {webhooks.map((sub) => (
                    <TableRow key={sub.id} className="border-[#E5EBF5] hover:bg-[#F8FAFC]/60">
                      <TableCell className="font-mono text-xs font-medium text-[#374151]">
                        {sub.url}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1.5">
                          {(sub.event_types || []).map((e) => (
                            <span
                              key={e}
                              className="inline-flex items-center rounded-full border border-[#E5EBF5] bg-white px-2.5 py-0.5 text-[11px] font-medium text-[#64748B]"
                            >
                              {e}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-[#64748B]">
                        {new Date(sub.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <button
                          type="button"
                          onClick={() => deleteWebhook(sub.id)}
                          className="inline-flex items-center gap-1 h-8 px-3 rounded-full text-xs font-medium text-destructive hover:bg-destructive/10 transition-colors cursor-pointer"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          <span>Delete</span>
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>

      {/* Generate Key Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={(open) => !open && closeCreateModal()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Generate New API Key</DialogTitle>
          </DialogHeader>

          <form
            onSubmit={async (e) => {
              e.preventDefault();
              await createKey();
            }}
            className="space-y-4 pt-1"
          >
            <div className="space-y-1.5">
              <Label htmlFor="new-api-key-name">Key Name</Label>
              <Input
                id="new-api-key-name"
                placeholder="Key label or service name..."
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                error={Boolean(nameError)}
                autoFocus
              />
              {nameError && (
                <p className="text-xs text-destructive">{nameError}</p>
              )}
              {generalError && (
                <p className="text-xs text-destructive">{generalError}</p>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={closeCreateModal}
                disabled={isCreating}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isCreating}>
                {isCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-1.5" />
                    Generate Key
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Secret Key Revealed Dialog */}
      <Dialog open={Boolean(createdKey)} onOpenChange={(open) => !open && closeCreatedModal()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Save Your API Key</DialogTitle>
            <DialogDescription>
              This is the only time the full secret key will be shown. Please copy and store it securely.
            </DialogDescription>
          </DialogHeader>

          {createdKey && (
            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label>Secret Key</Label>
                <div className="flex gap-2">
                  <Input
                    readOnly
                    value={createdKey.api_key}
                    className="font-mono text-xs select-all"
                  />
                  <Button
                    variant="outline"
                    onClick={() => copyToClipboard(createdKey.api_key)}
                    className="flex-shrink-0"
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldAlert className="h-4 w-4 text-amber-500 flex-shrink-0" />
                <span>We cannot recover this key if lost. Keep it in your environment variables.</span>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button onClick={closeCreatedModal}>I Have Saved This Key</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Key Name Dialog */}
      <Dialog open={Boolean(editingKey)} onOpenChange={(open) => !open && closeEditModal()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit API Key Name</DialogTitle>
          </DialogHeader>

          <form
            onSubmit={async (e) => {
              e.preventDefault();
              await submitEditKey();
            }}
            className="space-y-4 pt-1"
          >
            <div className="space-y-1.5">
              <Label htmlFor="edit-api-key-name">Key Name</Label>
              <Input
                id="edit-api-key-name"
                value={editKeyName}
                onChange={(e) => setEditKeyName(e.target.value)}
                error={Boolean(editNameError)}
                autoFocus
              />
              {editNameError && (
                <p className="text-xs text-destructive">{editNameError}</p>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={closeEditModal}
                disabled={isUpdatingKey}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isUpdatingKey}>
                {isUpdatingKey ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Name"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Key Confirmation Dialog */}
      <Dialog open={Boolean(deleteConfirmKey)} onOpenChange={(open) => !open && closeDeleteConfirm()}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>Delete API Key</DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete &ldquo;{deleteConfirmKey?.name}&rdquo;? Any applications using this key will stop working immediately.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={closeDeleteConfirm}
              disabled={isDeletingKey}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={submitDeleteKey}
              disabled={isDeletingKey}
            >
              {isDeletingKey ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete Key"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
