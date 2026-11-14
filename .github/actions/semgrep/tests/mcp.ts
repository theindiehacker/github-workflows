import { McpServer } from "@modelcontextprotocol/server";
import axios from "axios";
import * as z from "zod";

const server = new McpServer({ name: "test", version: "1.0.0" });
const BASE = "https://api.example.com";
const text = (value: string) => ({
  content: [{ type: "text" as const, text: value }],
});

server.registerTool(
  "fetch_url",
  { inputSchema: z.object({ url: z.string(), id: z.string() }) },
  async ({ url, id }) => {
    // ruleid: mcp-ssrf
    await fetch(url);
    // ruleid: mcp-ssrf
    await axios.get(url);
    // ruleid: mcp-ssrf
    await fetch(`${url}/items`);
    // ok: mcp-ssrf
    await fetch(`https://api.example.com/items/${id}`);
    // ok: mcp-ssrf
    await fetch(`${BASE}/items/${id}`);
    // ok: mcp-ssrf
    return text(`${url} を読みました`);
  },
);

server.registerTool("echo", {}, async (args) => {
  // ruleid: mcp-ssrf
  await fetch(args.url);
  // ok: mcp-ssrf
  return text(`${args.url}`);
});

server.tool("legacy", { url: z.string() }, async ({ url }) => {
  // ruleid: mcp-ssrf
  await fetch(url);
  return text("ok");
});

server.registerPrompt("summarize", {}, ({ url }) => {
  // ruleid: mcp-ssrf
  void fetch(url);
  return { messages: [] };
});

server.registerResource(
  "page",
  "page://{url}",
  {},
  async (uri, { url }) => {
    // ruleid: mcp-ssrf
    await fetch(String(url));
    // ok: mcp-ssrf
    await fetch(`${BASE}/pages/${uri.pathname}`);
    return { contents: [] };
  },
);

server.server.setRequestHandler("tools/call", async (request) => {
  // ruleid: mcp-ssrf
  await fetch(request.params.arguments.url);
  return {};
});

export function notMcp(url: string) {
  // ok: mcp-ssrf
  return fetch(url);
}
