from __future__ import annotations

import json
import os
import re
import sys
import webbrowser
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {"error": "unknown_tool", "message": f"No local implementation for {call.name}"},
        }
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events, max_chars=24000)}\n\n"
            "Use only these tool results. If the user asked for an incident report and the findings are ready, "
            "call the reporting tool. Otherwise answer directly, state uncertainty, and give the safest next step."
        ),
    }


def assistant_tool_message(response_text: str | None, calls: list[ToolCall]) -> dict[str, str]:
    call_summary = [{"name": call.name, "args": call.args} for call in calls]
    content = response_text or "I will call the selected tool(s)."
    return {
        "role": "assistant",
        "content": f"{content}\n\nTOOL_CALLS_JSON:\n{json_text(call_summary)}",
    }


def trim_history(history: list[dict[str, str]], window: int = 5) -> list[dict[str, str]]:
    if window <= 0:
        return []
    return history[-window * 2:]


class ChatSession:
    def __init__(self, provider_name: str = "openrouter", version: str = "v3", model: str | None = None):
        self.provider_name = provider_name
        self.version = version
        self.model = model
        self.system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
        self.tools_path = ARTIFACTS_DIR / "tools.yaml"
        self.history_window = 5
        self.max_tool_rounds = 4

        self.system_prompt = self.system_prompt_path.read_text(encoding="utf-8")
        self.tool_declarations = load_tool_declarations(self.tools_path)
        self.openai_tools = to_openai_tools(self.tool_declarations)
        self.provider = make_provider(self.provider_name)
        self.selected_model = self.model or getattr(self.provider, "default_model", None)
        self.artifact_version = build_artifact_version(self.version, self.system_prompt_path, self.tools_path)

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        self.transcript_id = "_".join([
            safe_slug(self.version),
            safe_slug(self.provider_name),
            timestamp,
        ])
        self.transcript_path = TRANSCRIPTS_DIR / f"{self.transcript_id}.transcript.json"
        self.transcript: dict[str, Any] = {
            "transcript_id": self.transcript_id,
            **artifact_version_dict(self.artifact_version),
            "provider": self.provider_name,
            "model": self.selected_model,
            "system_prompt": str(self.system_prompt_path),
            "tools": str(self.tools_path),
            "history_window": self.history_window,
            "max_tool_rounds": self.max_tool_rounds,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
        }
        self.history: list[dict[str, str]] = []
        self.turn_index = 0

    def chat_turn(self, user_text: str) -> dict[str, Any]:
        self.turn_index += 1
        messages = [
            {"role": "system", "content": self.system_prompt},
            *trim_history(self.history, self.history_window),
            {"role": "user", "content": user_text},
        ]

        turn_record: dict[str, Any] = {
            "turn_index": self.turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }

        try:
            working_messages = list(messages)
            rounds: list[dict[str, Any]] = []
            all_tool_events: list[dict[str, Any]] = []
            final_status = "answered"
            assistant_text = ""

            for round_index in range(1, self.max_tool_rounds + 1):
                response = self.provider.complete(working_messages, self.openai_tools, model=self.model, temperature=0.0)
                calls = response.tool_calls
                round_record: dict[str, Any] = {
                    "round": round_index,
                    "assistant_text": response.text,
                    "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
                    "tool_results": [],
                }

                if not calls:
                    rounds.append(round_record)
                    assistant_text = response.text or ""
                    final_status = "answered"
                    break

                working_messages.append(assistant_tool_message(response.text, calls))
                non_clarification_events: list[dict[str, Any]] = []

                for call in calls:
                    event = execute_tool_call(call)
                    round_record["tool_results"].append(event)
                    all_tool_events.append(event)

                    result = event.get("result", {})
                    if isinstance(result, dict) and result.get("awaiting_user"):
                        question = result.get("question") or call.args.get("question") or "Bạn vui lòng bổ sung thêm thông tin."
                        assistant_text = question
                        final_status = "waiting_for_user"

                    non_clarification_events.append(event)

                rounds.append(round_record)
                if final_status == "waiting_for_user":
                    break

                working_messages.append(tool_results_message(non_clarification_events))
            else:
                final_status = "max_tool_rounds"
                assistant_text = f"Đã dừng sau {self.max_tool_rounds} vòng gọi công cụ."

            turn_record.update({
                "status": final_status,
                "assistant_text": assistant_text,
                "rounds": rounds,
                "tool_events": all_tool_events,
            })
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": assistant_text})
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {str(exc)}",
                "assistant_text": f"Lỗi gọi Provider: {str(exc)}",
            })

        turn_record["ended_at"] = now_iso()
        self.transcript["turns"].append(turn_record)
        self.transcript["updated_at"] = now_iso()

        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        self.transcript_path.write_text(json.dumps(self.transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

        return {
            "turn_index": self.turn_index,
            "assistant_text": turn_record["assistant_text"],
            "status": turn_record["status"],
            "tool_events": turn_record.get("tool_events", []),
            "rounds": turn_record.get("rounds", []),
            "transcript_id": self.transcript_id,
            "artifact_version": self.artifact_version.artifact_version,
        }


# Global active session
CURRENT_SESSION = ChatSession()


HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IT Helpdesk AI Agent — NhomGG</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-main: #0B0F19;
      --bg-card: #111827;
      --bg-card-hover: #1F2937;
      --border-color: #374151;
      --primary: #3B82F6;
      --primary-glow: rgba(59, 130, 246, 0.35);
      --accent: #10B981;
      --accent-purple: #8B5CF6;
      --accent-amber: #F59E0B;
      --text-main: #F3F4F6;
      --text-muted: #9CA3AF;
      --text-dim: #6B7280;
      --font-sans: 'Plus Jakarta Sans', system-ui, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg-main);
      color: var(--text-main);
      font-family: var(--font-sans);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }

    /* Sidebar */
    .sidebar {
      width: 320px;
      background: rgba(17, 24, 39, 0.95);
      backdrop-filter: blur(12px);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      padding: 20px;
      gap: 20px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
    }
    .brand-logo {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      background: linear-gradient(135deg, #3B82F6, #8B5CF6);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 18px;
      box-shadow: 0 0 15px var(--primary-glow);
    }
    .brand-text h1 { font-size: 16px; font-weight: 700; color: #fff; }
    .brand-text p { font-size: 12px; color: var(--text-muted); }

    .control-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .control-group label {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
    }
    select, input, button {
      font-family: var(--font-sans);
      border-radius: 8px;
      border: 1px solid var(--border-color);
      background: #1E293B;
      color: var(--text-main);
      padding: 10px 12px;
      font-size: 13px;
      outline: none;
      transition: all 0.2s;
    }
    select:focus, input:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 2px var(--primary-glow);
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      font-family: var(--font-mono);
      background: rgba(59, 130, 246, 0.15);
      color: #60A5FA;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }

    .quick-prompts {
      display: flex;
      flex-direction: column;
      gap: 6px;
      overflow-y: auto;
      flex: 1;
    }
    .quick-btn {
      text-align: left;
      background: #1F2937;
      border: 1px solid #374151;
      padding: 8px 10px;
      border-radius: 6px;
      color: var(--text-muted);
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .quick-btn:hover {
      background: #374151;
      color: #fff;
      border-color: var(--primary);
    }

    .sidebar-actions {
      display: flex;
      flex-direction: column;
      gap: 10px;
      border-top: 1px solid var(--border-color);
      padding-top: 16px;
    }
    .btn-primary {
      background: linear-gradient(135deg, #2563EB, #1D4ED8);
      color: white;
      font-weight: 600;
      cursor: pointer;
      border: none;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }
    .btn-primary:hover {
      background: linear-gradient(135deg, #3B82F6, #2563EB);
      box-shadow: 0 0 15px var(--primary-glow);
    }
    .btn-secondary {
      background: #1F2937;
      cursor: pointer;
      border: 1px solid var(--border-color);
      font-weight: 500;
    }
    .btn-secondary:hover { background: #374151; }

    /* Main Chat Area */
    .main {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: radial-gradient(circle at 50% 0%, rgba(30, 58, 138, 0.15) 0%, transparent 70%), var(--bg-main);
    }

    .chat-header {
      padding: 16px 24px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(17, 24, 39, 0.5);
      backdrop-filter: blur(8px);
    }
    .chat-header-title {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 8px var(--accent);
    }

    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .message-row {
      display: flex;
      gap: 14px;
      max-width: 85%;
    }
    .message-row.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }
    .message-row.agent {
      align-self: flex-start;
    }

    .avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      flex-shrink: 0;
    }
    .avatar.user { background: #4B5563; color: #fff; }
    .avatar.agent { background: linear-gradient(135deg, #3B82F6, #10B981); color: #fff; }

    .message-bubble {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 14px 18px;
      font-size: 14px;
      line-height: 1.6;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    .message-row.user .message-bubble {
      background: #1E3A8A;
      border-color: #2563EB;
      color: #EFF6FF;
    }

    /* Tool Call Card */
    .tool-card {
      margin: 10px 0;
      background: #0D1117;
      border: 1px solid #30363D;
      border-radius: 8px;
      overflow: hidden;
      font-family: var(--font-mono);
      font-size: 12px;
    }
    .tool-header {
      padding: 8px 12px;
      background: #161B22;
      border-bottom: 1px solid #30363D;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #58A6FF;
      font-weight: 600;
    }
    .tool-body {
      padding: 10px 12px;
      color: #C9D1D9;
      white-space: pre-wrap;
      max-height: 250px;
      overflow-y: auto;
      font-size: 11.5px;
    }
    .tool-result-header {
      padding: 6px 12px;
      background: rgba(16, 185, 129, 0.1);
      border-top: 1px solid #30363D;
      border-bottom: 1px solid #30363D;
      color: #34D399;
      font-weight: 600;
    }

    /* Input area */
    .chat-input-area {
      padding: 18px 24px;
      background: rgba(17, 24, 39, 0.95);
      border-top: 1px solid var(--border-color);
      display: flex;
      gap: 12px;
    }
    .chat-input {
      flex: 1;
      background: #1F2937;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px 16px;
      color: #fff;
      font-size: 14px;
    }
    .send-btn {
      padding: 0 24px;
      border-radius: 10px;
    }

    /* Spinner */
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 0.8s ease-in-out infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-logo">GG</div>
      <div class="brand-text">
        <h1>IT Helpdesk Assistant</h1>
        <p>K4-Day04 • Team NhomGG</p>
      </div>
    </div>

    <div class="control-group">
      <label>Phiên bản Agent</label>
      <select id="agentVersion" onchange="resetSession()">
        <option value="v3" selected>v3 (Multi-turn + Triage + Bonus Tool)</option>
        <option value="v2">v2 (Ticket Confirmation + Clarify)</option>
        <option value="v1">v1 (Missing Info Handling)</option>
        <option value="v0">v0 (Starter Baseline)</option>
      </select>
    </div>

    <div class="control-group">
      <label>Provider</label>
      <select id="providerName" onchange="resetSession()">
        <option value="openrouter" selected>OpenRouter (gpt-4o-mini)</option>
        <option value="gemini">Google Gemini</option>
        <option value="openai">OpenAI</option>
      </select>
    </div>

    <div class="control-group" style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
      <label>Test nhanh (Quick Prompts)</label>
      <div class="quick-prompts">
        <button class="quick-btn" onclick="sendQuick(this.innerText)">Kiểm tra trạng thái VPN production</button>
        <button class="quick-btn" onclick="sendQuick(this.innerText)">Kiểm tra laptop LT-204 giúp mình</button>
        <button class="quick-btn" onclick="sendQuick(this.innerText)">Ping và đo độ trễ đến hệ thống VPN</button>
        <button class="quick-btn" onclick="sendQuick(this.innerText)">Kiểm tra port của máy chủ email nội bộ</button>
        <button class="quick-btn" onclick="sendQuick(this.innerText)">Kiểm tra laptop và ping tới gateway</button>
        <button class="quick-btn" onclick="sendQuick(this.innerText)">Tra cứu nhân viên EMP-1003</button>
        <button class="quick-btn" onclick="sendQuick(this.innerText)">Tạo ticket mức high cho lỗi VPN trên LT-204</button>
      </div>
    </div>

    <div class="sidebar-actions">
      <button class="btn-primary" onclick="downloadTranscript()">
        📥 Tải Transcript (.json)
      </button>
      <button class="btn-secondary" onclick="resetSession()">
        🔄 Tạo phiên chat mới
      </button>
    </div>
  </aside>

  <!-- Main Chat -->
  <main class="main">
    <header class="chat-header">
      <div class="chat-header-title">
        <div class="status-dot"></div>
        <div>
          <strong id="headerTitle">Agent v3 Live Session</strong>
          <div style="font-size: 11px; color: var(--text-muted);" id="headerSubtitle">Artifact: v3 • Provider: OpenRouter</div>
        </div>
      </div>
      <span class="badge" id="transcriptBadge">transcript: initializing...</span>
    </header>

    <div class="chat-messages" id="messagesContainer">
      <div class="message-row agent">
        <div class="avatar agent">AI</div>
        <div class="message-bubble">
          Xin chào! Tôi là trợ lý IT Helpdesk của Northstar Labs (Team NhomGG). Tôi có thể hỗ trợ kiểm tra trạng thái dịch vụ (VPN/Email/SSO), chẩn đoán thiết bị, tra cứu danh bạ, kiểm tra chính sách và chẩn đoán kết nối mạng <code>diagnose_network</code>. Bạn cần hỗ trợ gì?
        </div>
      </div>
    </div>

    <form class="chat-input-area" onsubmit="handleSend(event)">
      <input type="text" id="userInput" class="chat-input" placeholder="Nhập câu hỏi hoặc yêu cầu hỗ trợ kỹ thuật..." autocomplete="off">
      <button type="submit" id="sendBtn" class="btn-primary send-btn">Gửi</button>
    </form>
  </main>

  <script>
    const messagesContainer = document.getElementById('messagesContainer');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const transcriptBadge = document.getElementById('transcriptBadge');
    const headerTitle = document.getElementById('headerTitle');
    const headerSubtitle = document.getElementById('headerSubtitle');

    function sendQuick(text) {
      userInput.value = text;
      handleSend(new Event('submit'));
    }

    async function handleSend(e) {
      if (e) e.preventDefault();
      const text = userInput.value.trim();
      if (!text) return;

      appendMessage('user', text);
      userInput.value = '';
      sendBtn.disabled = true;
      sendBtn.innerHTML = '<span class="spinner"></span>';

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            version: document.getElementById('agentVersion').value,
            provider: document.getElementById('providerName').value
          })
        });
        const data = await res.json();
        
        if (data.transcript_id) {
          transcriptBadge.innerText = data.transcript_id;
        }

        appendMessage('agent', data.assistant_text, data.tool_events);
      } catch (err) {
        appendMessage('agent', '⚠️ Lỗi kết nối đến máy chủ: ' + err.message);
      } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = 'Gửi';
      }
    }

    function appendMessage(role, text, toolEvents = []) {
      const row = document.createElement('div');
      row.className = 'message-row ' + role;
      
      const avatar = document.createElement('div');
      avatar.className = 'avatar ' + role;
      avatar.innerText = role === 'user' ? 'YOU' : 'AI';

      const bubble = document.createElement('div');
      bubble.className = 'message-bubble';

      // Tool events visualization
      if (toolEvents && toolEvents.length > 0) {
        toolEvents.forEach(evt => {
          const card = document.createElement('div');
          card.className = 'tool-card';
          
          const header = document.createElement('div');
          header.className = 'tool-header';
          header.innerHTML = `<span>⚡ Tool Call: <b>${evt.tool}</b></span><span>args</span>`;

          const body = document.createElement('div');
          body.className = 'tool-body';
          body.innerText = JSON.stringify(evt.args, null, 2);

          const resHeader = document.createElement('div');
          resHeader.className = 'tool-result-header';
          resHeader.innerHTML = `<span>✓ Tool Output / Execution Result</span>`;

          const resBody = document.createElement('div');
          resBody.className = 'tool-body';
          resBody.innerText = JSON.stringify(evt.result, null, 2);

          card.appendChild(header);
          card.appendChild(body);
          card.appendChild(resHeader);
          card.appendChild(resBody);
          bubble.appendChild(card);
        });
      }

      const textNode = document.createElement('div');
      textNode.style.marginTop = (toolEvents && toolEvents.length > 0) ? '10px' : '0';
      textNode.innerText = text || '';
      bubble.appendChild(textNode);

      row.appendChild(avatar);
      row.appendChild(bubble);
      messagesContainer.appendChild(row);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function resetSession() {
      const version = document.getElementById('agentVersion').value;
      const provider = document.getElementById('providerName').value;
      headerTitle.innerText = `Agent ${version} Live Session`;
      headerSubtitle.innerText = `Artifact: ${version} • Provider: ${provider}`;

      await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version, provider })
      });

      messagesContainer.innerHTML = `
        <div class="message-row agent">
          <div class="avatar agent">AI</div>
          <div class="message-bubble">
            Đã chuyển sang phiên bản <b>${version.toUpperCase()}</b> với provider <b>${provider}</b>. Mời bạn đặt câu hỏi!
          </div>
        </div>
      `;
    }

    function downloadTranscript() {
      window.open('/api/transcript', '_blank');
    }
  </script>
</body>
</html>
"""


class RequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path == "/api/transcript":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f"attachment; filename={CURRENT_SESSION.transcript_id}.json")
            self.end_headers()
            self.wfile.write(json.dumps(CURRENT_SESSION.transcript, ensure_ascii=False, indent=2, default=str).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global CURRENT_SESSION
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body.decode("utf-8")) if body else {}

        if parsed.path == "/api/chat":
            user_msg = data.get("message", "")
            version = data.get("version", CURRENT_SESSION.version)
            provider = data.get("provider", CURRENT_SESSION.provider_name)

            if version != CURRENT_SESSION.version or provider != CURRENT_SESSION.provider_name:
                CURRENT_SESSION = ChatSession(provider_name=provider, version=version)

            result = CURRENT_SESSION.chat_turn(user_msg)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        elif parsed.path == "/api/reset":
            version = data.get("version", "v3")
            provider = data.get("provider", "openrouter")
            CURRENT_SESSION = ChatSession(provider_name=provider, version=version)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "transcript_id": CURRENT_SESSION.transcript_id}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port: int = 8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, RequestHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n========================================================")
    print(f" 🚀 IT Helpdesk Web UI is running at: {url}")
    print(f" Giao diện Chatbot chuyên nghiệp cho bạn Nguyễn Văn Đại (UI/UX)")
    print(f" Nhấn Ctrl+C để dừng server.")
    print(f"========================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
