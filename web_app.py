#!/usr/bin/env python3
"""
Flask Web Server for the Real Estate Consultation Agent.
Provides a beautiful chat interface for both Chatbot Baseline and ReAct Agent.
"""
import os
import sys
import json
import time
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent
from src.agent.chatbot import ChatbotBaseline
from src.tools import ALL_TOOLS as TOOLS
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Initialize provider and systems once
provider = None
agent = None
chatbot = None


def get_agent():
    """Lazy-initialize the agent."""
    global provider, agent, chatbot
    if agent is None:
        model_name = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
        api_key = os.getenv("GEMINI_API_KEY")
        provider = GeminiProvider(model_name=model_name, api_key=api_key)
        agent = ReActAgent(llm=provider, tools=TOOLS, max_steps=6)
        chatbot = ChatbotBaseline(llm=provider)
    return agent


@app.route("/")
def index():
    """Serve the main chat page."""
    return send_from_directory("static", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle chat messages from the frontend (ReAct Agent)."""
    data = request.get_json()
    user_message = data.get("message", "").strip()
    mode = data.get("mode", "agent")  # "agent" or "chatbot"

    if not user_message:
        return jsonify({"error": "Tin nhắn trống"}), 400

    try:
        get_agent()  # ensure initialized
        start = time.time()

        if mode == "chatbot":
            answer = chatbot.run(user_message)
        else:
            answer = agent.run(user_message)

        elapsed_ms = int((time.time() - start) * 1000)

        # Gather session metrics for the last request cycle
        recent = tracker.session_metrics[-1] if tracker.session_metrics else {}

        return jsonify({
            "answer": answer,
            "elapsed_ms": elapsed_ms,
            "tokens": recent.get("total_tokens", 0),
            "model": provider.model_name if provider else "unknown",
            "mode": mode,
        })

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def stats():
    """Return session performance statistics."""
    metrics = tracker.session_metrics
    if not metrics:
        return jsonify({"total_requests": 0})

    total_requests = len(metrics)
    total_tokens = sum(m.get("total_tokens", 0) for m in metrics)
    total_latency = sum(m.get("latency_ms", 0) for m in metrics)
    total_cost = sum(m.get("cost_estimate", 0) for m in metrics)

    return jsonify({
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "avg_latency_ms": int(total_latency / total_requests) if total_requests else 0,
        "total_cost_usd": round(total_cost, 6),
        "model": provider.model_name if provider else "unknown",
    })


@app.route("/api/suggestions", methods=["GET"])
def suggestions():
    """Return sample query suggestions."""
    return jsonify({
        "suggestions": [
            "Tìm căn STUDIO hướng Tây Nam tại The London giá dưới 2.2 tỷ",
            "Giá trung bình căn 2PN ở The Paris là bao nhiêu?",
            "Có căn 1PN nào đang bán ở The Zurich tầng cao không?",
            "So sánh giá căn 3PN giữa The Paris và The Beverly",
            "Cho tôi xem chi tiết căn hộ mã 5PDVUJ",
            "Mua căn 5 tỷ trả góp 20 năm thì tháng trả bao nhiêu?",
            "Xung quanh Vinhomes có trường học và bệnh viện gì?",
            "Tìm căn 2PN+ ở The Beverly rồi tính trả góp 15 năm",
        ]
    })


if __name__ == "__main__":
    print("\n🏠 Real Estate Agent Web Server")
    print("=" * 50)
    print(f"   Model: {os.getenv('DEFAULT_MODEL', 'gemini-2.5-flash')}")
    print(f"   Keys:  {len(os.getenv('GEMINI_API_KEYS', '').split(','))} keys in pool")
    print(f"   URL:   http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)

