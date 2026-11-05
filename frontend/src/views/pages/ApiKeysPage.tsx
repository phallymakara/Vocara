import React, { useState } from "react";
import { Copy, Check, Trash2, Plus, ShieldAlert, Loader2, Cpu } from "lucide-react";
import { useKeyController } from "@/controllers/useKeyController";
import { Button } from "@/views/components/ui/button";
import { Input } from "@/views/components/ui/input";
import { Label } from "@/views/components/ui/label";
import { Badge } from "@/views/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/views/components/ui/card";
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

export const ApiKeysPage: React.FC = () => {
  const {
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
    createKey,
    revokeKey,
    saveActiveKey,
    copyToClipboard,
    closeCreatedModal,
  } = useKeyController();

  const [selectedMcpTab, setSelectedMcpTab] = useState<"cursor" | "claude" | "python" | "typescript">("cursor");
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  const baseUrl = typeof window !== "undefined"
    ? (window.location.port === "3000"
        ? `${window.location.protocol}//${window.location.hostname}:8002`
        : window.location.origin)
    : "http://localhost:8002";

  const effectiveKey = activeKeyInput?.trim() || "voc_YOUR_API_KEY";
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
                "text": "សួស្តីពិភពលោក",
                "voice_id": "voice-sophea-built-in",
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

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          API Key Management
        </h2>
        <p className="text-sm text-muted-foreground">
          Create and manage bearer keys for authenticating requests to Vocara API endpoints.
        </p>
      </div>

      {/* Active Key Config */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Active Workspace Key</CardTitle>
          <CardDescription>
            This key is sent in the Authorization header when synthesizing speech or managing resources.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="flex-1">
              <Input
                type="password"
                placeholder="Enter or paste Vocara API secret key..."
                value={activeKeyInput}
                onChange={(e) => setActiveKeyInput(e.target.value)}
                className="font-mono text-xs"
              />
            </div>
            <Button onClick={saveActiveKey} variant="secondary" className="sm:w-auto">
              Save Active Key
            </Button>
          </div>
          {saveSuccessMessage && (
            <p className="text-xs text-emerald-600 font-medium">{saveSuccessMessage}</p>
          )}
        </CardContent>
      </Card>

      {/* Create Key Form */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Generate New API Key</CardTitle>
          <CardDescription>
            Name your key based on environment or service (e.g. Production Webhook, Local Dev).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-2 items-start">
            <div className="flex-1 w-full space-y-1">
              <Input
                placeholder="Key label or service name..."
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                error={Boolean(nameError)}
              />
              {nameError && (
                <p className="text-xs text-destructive">{nameError}</p>
              )}
            </div>
            <Button onClick={createKey} className="w-full sm:w-auto">
              <Plus className="h-4 w-4 mr-1.5" />
              Generate Key
            </Button>
          </div>
          {generalError && (
            <p className="text-xs text-destructive">{generalError}</p>
          )}
        </CardContent>
      </Card>

      {/* Keys Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Issued Keys</CardTitle>
          <CardDescription>
            All active credentials associated with this project.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 flex justify-center items-center text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Loading API keys...
            </div>
          ) : keys.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground border border-dashed rounded">
              No API keys found. Generate a key above to start using the API.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key Name</TableHead>
                  <TableHead>Key Prefix</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((k) => (
                  <TableRow key={k.id}>
                    <TableCell className="font-medium text-sm">{k.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {k.key_prefix}...
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(k.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[11px] text-emerald-600 border-emerald-300">
                        Active
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => revokeKey(k.id)}
                        className="h-8 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Revoke
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Model Context Protocol (MCP) Integration */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                Model Context Protocol (MCP) Integration
              </CardTitle>
              <CardDescription>
                Allow external developers, Cursor IDE, Claude Desktop, and AI agents to discover voices and synthesize speech.
              </CardDescription>
            </div>
            <Badge variant="outline" className="w-fit text-[11px] font-mono">
              mcp://vocara-voices
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground font-normal">Remote SSE Endpoint</Label>
            <div className="flex gap-2">
              <Input
                readOnly
                value={sseEndpointUrl}
                className="font-mono text-xs select-all bg-muted/30"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(sseEndpointUrl);
                  setCopiedSnippet(true);
                  setTimeout(() => setCopiedSnippet(false), 2000);
                }}
                className="flex-shrink-0"
              >
                {copiedSnippet ? (
                  <Check className="h-4 w-4 text-emerald-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex gap-1.5">
                {[
                  { id: "cursor" as const, label: "Cursor IDE" },
                  { id: "claude" as const, label: "Claude Desktop" },
                  { id: "python" as const, label: "Python SDK" },
                  { id: "typescript" as const, label: "TypeScript" },
                ].map((tab) => (
                  <Button
                    key={tab.id}
                    variant={selectedMcpTab === tab.id ? "secondary" : "ghost"}
                    size="sm"
                    className="h-7 text-xs font-medium"
                    onClick={() => setSelectedMcpTab(tab.id)}
                  >
                    {tab.label}
                  </Button>
                ))}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={copySnippet}
                className="h-7 text-xs gap-1.5"
              >
                {copiedSnippet ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-600" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    <span>Copy Config</span>
                  </>
                )}
              </Button>
            </div>

            <div className="relative">
              <pre className="p-3 bg-muted/40 rounded border border-border text-xs font-mono overflow-x-auto text-foreground whitespace-pre leading-relaxed">
                {snippetMap[selectedMcpTab]}
              </pre>
            </div>
          </div>

          <div className="pt-2 border-t border-border">
            <p className="text-[11px] text-muted-foreground font-medium mb-1.5">Exposed MCP Capabilities:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-muted-foreground font-mono">
              <div className="p-2 rounded bg-muted/20 border border-border/60">
                <span className="text-foreground font-semibold">vocara_list_voices</span>
                <p className="text-[11px] font-sans mt-0.5">Filter voices by language (km, en) and voice type.</p>
              </div>
              <div className="p-2 rounded bg-muted/20 border border-border/60">
                <span className="text-foreground font-semibold">vocara_get_voice_details</span>
                <p className="text-[11px] font-sans mt-0.5">Inspect acoustic parameters (pitch, speed, emotion).</p>
              </div>
              <div className="p-2 rounded bg-muted/20 border border-border/60">
                <span className="text-foreground font-semibold">vocara_preview_voice</span>
                <p className="text-[11px] font-sans mt-0.5">Listen to voice audio sample before synthesizing.</p>
              </div>
              <div className="p-2 rounded bg-muted/20 border border-border/60">
                <span className="text-foreground font-semibold">vocara_generate_speech</span>
                <p className="text-[11px] font-sans mt-0.5">Synthesize text into WAV/MP3 speech.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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
    </div>
  );
};
