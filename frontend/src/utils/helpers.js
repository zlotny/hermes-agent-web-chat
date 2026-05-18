/**
 * Shared utility functions used across stores and components.
 * Keeps logic in one place instead of duplicating across files.
 */

// ── System message detection ──────────────────────────────────────────────

const _SYSTEM_CONTENT_PREFIXES = [
  "[IMPORTANT:",
  "Review the conversation above",
  "Review the conversation",
  "System:",
  "You are a helpful assistant",
  "You are Hermes",
  "Hermes Agent",
  "You are an expert",
  "Today is",
  "Current date",
]
const _SYSTEM_CONTENT_EXACT = new Set(["[SILENT]"])

/**
 * Check if a message object or content string looks like a system-injected message.
 * Accepts either a message object ({ content, source, role }) or a plain string.
 */
export function isSystemMsg(msg) {
  if (!msg) return false
  // If the raw DB role is "system", it's a system message
  if (typeof msg === "object" && msg.role === "system") return true
  const content = typeof msg === "string" ? msg : msg.content
  if (!content) return false
  if (typeof msg === "object" && msg.source === "system") return true
  if (typeof msg === "object" && msg.source === "user") return false
  const stripped = content.trim()
  if (_SYSTEM_CONTENT_EXACT.has(stripped)) return true
  return _SYSTEM_CONTENT_PREFIXES.some((p) => stripped.startsWith(p))
}

// ── Model name formatting ─────────────────────────────────────────────────

/**
 * Shorten a model name to just the part after the last slash.
 * "openai/gpt-4o" → "gpt-4o"
 */
export function shortModel(name) {
  if (!name) return ""
  const short = name.split("/").pop() || name
  if (short.length > 20) {
    return short.slice(0, 10) + "…" + short.slice(-6)
  }
  return short
}

// ── Content rendering (markdown → HTML) ─────────────────────────────────

import { marked } from "marked"
import DOMPurify from "dompurify"

// Configure marked for GFM (tables, strikethrough, etc.) + line breaks
marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * Render markdown text to sanitized HTML.
 * Supports full GFM: headings, lists, tables, code blocks, blockquotes,
 * links, images, bold, italic, strikethrough, inline code, and more.
 */
export function renderContent(text) {
  if (!text) return ""
  const raw = marked.parse(text)
  return DOMPurify.sanitize(raw)
}

// ── Tool call formatting ─────────────────────────────────────────────────

/**
 * Pretty-print a JSON string (for tool call arguments display).
 */
export function prettyJson(str) {
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch {
    return str || ""
  }
}

/**
 * Extract a short preview from a tool call's arguments.
 * Finds the first string value under 40 chars.
 */
export function toolArgPreview(toolCall) {
  try {
    const args = JSON.parse(toolCall.function?.arguments || "{}")
    const val = Object.values(args).find(
      (v) => typeof v === "string" && v.length < 40,
    )
    return val || ""
  } catch {
    return ""
  }
}

// ── File path vs slash command detection ───────────────────────────────────

/**
 * Check if text looks like a file path rather than a slash command.
 * File paths have additional / chars in the first word (e.g. /Users/foo).
 */
export function looksLikeFilePath(text) {
  if (!text || !text.startsWith("/")) return false
  const firstWord = text.split(/\s+/)[0] || ""
  return firstWord.includes("/", 1)
}

// ── Timestamp formatting ──────────────────────────────────────────────────

/**
 * Format a unix timestamp or ISO string to a locale-friendly short string.
 */
export function formatMsgTime(ts) {
  if (!ts) return ""
  const d = typeof ts === "number" ? new Date(ts * 1000) : new Date(ts)
  if (isNaN(d.getTime())) return ""
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
