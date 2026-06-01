#!/usr/bin/env python3
"""
Automated Evaluation: Chatbot Baseline vs ReAct Agent.
Runs the same test cases on both systems and compares results.
Outputs a structured comparison table + metrics.
"""
import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.gemini_provider import GeminiProvider
from src.agent.agent import ReActAgent
from src.agent.chatbot import ChatbotBaseline
from src.tools import ALL_TOOLS as TOOLS
from src.telemetry.logger import logger
from src.telemetry.metrics import PerformanceTracker


# ====== Test Cases ======
TEST_CASES = [
    {
        "id": "TC01",
        "category": "Simple Q",
        "query": "Vinhomes Ocean Park 1 ở đâu?",
        "expected_type": "general_knowledge",
        "description": "Câu hỏi kiến thức chung - cả chatbot và agent đều nên trả lời được"
    },
    {
        "id": "TC02",
        "category": "Data Lookup",
        "query": "Tìm căn STUDIO hướng Tây Nam tại The London giá dưới 2.2 tỷ",
        "expected_type": "specific_data",
        "description": "Cần tra cứu database - chatbot sẽ bịa, agent dùng tool"
    },
    {
        "id": "TC03",
        "category": "Data Lookup",
        "query": "Cho tôi xem chi tiết căn hộ mã 5PDVUJ, bao gồm số điện thoại chủ nhà",
        "expected_type": "specific_data",
        "description": "Cần get_property_details - chatbot không thể biết SĐT thực"
    },
    {
        "id": "TC04",
        "category": "Multi-step",
        "query": "Giá trung bình căn 2PN ở The Paris là bao nhiêu? So sánh với The Zurich?",
        "expected_type": "analysis",
        "description": "Cần gọi calculate_market_stats 2 lần rồi so sánh"
    },
    {
        "id": "TC05",
        "category": "Data Lookup",
        "query": "Có căn 1PN nào đang bán ở The Zurich tầng cao không?",
        "expected_type": "specific_data",
        "description": "Cần search với nhiều filter: type + status + floor"
    },
]


def evaluate_single(system, system_name: str, query: str, metrics_tracker: PerformanceTracker):
    """Run a single query and capture results + metrics."""
    start_metrics_count = len(metrics_tracker.session_metrics)
    start_time = time.time()

    try:
        answer = system.run(query)
        success = True
        error = None
    except Exception as e:
        answer = f"ERROR: {e}"
        success = False
        error = str(e)

    elapsed_ms = int((time.time() - start_time) * 1000)

    # Gather metrics from this run
    new_metrics = metrics_tracker.session_metrics[start_metrics_count:]
    total_tokens = sum(m.get("total_tokens", 0) for m in new_metrics)
    total_cost = sum(m.get("cost_estimate", 0) for m in new_metrics)
    llm_calls = len(new_metrics)

    return {
        "system": system_name,
        "answer": answer,
        "success": success,
        "error": error,
        "elapsed_ms": elapsed_ms,
        "total_tokens": total_tokens,
        "cost_estimate": total_cost,
        "llm_calls": llm_calls,
    }


def check_answer_quality(result: dict, test_case: dict) -> dict:
    """
    Heuristic quality check for answers.
    Returns quality assessment with score.
    """
    answer = result.get("answer", "").lower()
    expected_type = test_case["expected_type"]
    score = 0
    notes = []

    if not result["success"]:
        return {"score": 0, "grade": "FAIL", "notes": ["Lỗi khi chạy"]}

    # Check for hallucination indicators
    hallucination_phrases = [
        "tôi không có thông tin",
        "không có dữ liệu cụ thể",
        "tôi không thể",
        "xin lỗi, tôi không",
        "không thể cung cấp",
    ]

    has_data = not any(p in answer for p in hallucination_phrases)

    if expected_type == "general_knowledge":
        # Both should answer correctly
        if len(answer) > 30:
            score = 1
            notes.append("Trả lời đủ dài")
        if "gia lâm" in answer or "hà nội" in answer or "ocean park" in answer:
            score = 2
            notes.append("Có thông tin chính xác")

    elif expected_type == "specific_data":
        # Agent should have real data, chatbot should not
        if has_data:
            # Check for real-looking data markers
            has_price = any(kw in answer for kw in ["tỷ", "triệu", "vnd"])
            has_code = any(kw in answer for kw in ["mã căn", "id:", "ld1", "zr", "pr"])
            has_phone = any(c.isdigit() for c in answer) and len([c for c in answer if c.isdigit()]) > 8

            if has_price:
                score += 1
                notes.append("Có giá cụ thể")
            if has_code or has_phone:
                score += 1
                notes.append("Có mã căn/SĐT thực")
        else:
            notes.append("Không có dữ liệu cụ thể")

    elif expected_type == "analysis":
        if has_data:
            has_comparison = any(kw in answer for kw in ["so sánh", "cao hơn", "thấp hơn", "chênh lệch", "trung bình"])
            has_numbers = any(kw in answer for kw in ["tỷ", "triệu"])
            if has_comparison:
                score += 1
                notes.append("Có so sánh")
            if has_numbers:
                score += 1
                notes.append("Có số liệu cụ thể")
        else:
            notes.append("Không có phân tích dữ liệu")

    grade = "FAIL" if score == 0 else ("PASS" if score == 1 else "GOOD")
    return {"score": score, "grade": grade, "notes": notes}


def run_evaluation():
    """Run full evaluation suite."""
    print("\n" + "=" * 70)
    print("  📊 ĐÁNH GIÁ: CHATBOT BASELINE vs REACT AGENT")
    print("=" * 70)

    # Create separate metrics trackers
    chatbot_metrics = PerformanceTracker()
    agent_metrics = PerformanceTracker()

    # Initialize systems
    model_name = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
    api_key = os.getenv("GEMINI_API_KEY")

    provider_chatbot = GeminiProvider(model_name=model_name, api_key=api_key)
    provider_agent = GeminiProvider(model_name=model_name, api_key=api_key)

    chatbot = ChatbotBaseline(llm=provider_chatbot)
    agent = ReActAgent(llm=provider_agent, tools=TOOLS, max_steps=5)

    # Override global tracker temporarily
    import src.telemetry.metrics as metrics_module

    results = []

    for tc in TEST_CASES:
        print(f"\n{'─' * 60}")
        print(f"  🧪 {tc['id']}: {tc['query'][:60]}...")
        print(f"  📂 Category: {tc['category']}")
        print(f"{'─' * 60}")

        # Run Chatbot
        print("  🤖 Running Chatbot...", end=" ", flush=True)
        metrics_module.tracker = chatbot_metrics
        cb_result = evaluate_single(chatbot, "Chatbot", tc["query"], chatbot_metrics)
        cb_quality = check_answer_quality(cb_result, tc)
        print(f"Done ({cb_result['elapsed_ms']}ms, {cb_result['total_tokens']} tokens)")

        # Small delay to avoid rate limit
        time.sleep(2)

        # Run Agent
        print("  🧠 Running Agent...", end=" ", flush=True)
        metrics_module.tracker = agent_metrics
        ag_result = evaluate_single(agent, "Agent", tc["query"], agent_metrics)
        ag_quality = check_answer_quality(ag_result, tc)
        print(f"Done ({ag_result['elapsed_ms']}ms, {ag_result['total_tokens']} tokens)")

        # Determine winner
        if ag_quality["score"] > cb_quality["score"]:
            winner = "🧠 Agent"
        elif cb_quality["score"] > ag_quality["score"]:
            winner = "🤖 Chatbot"
        else:
            winner = "🤝 Draw"

        results.append({
            "test_case": tc,
            "chatbot": {**cb_result, "quality": cb_quality},
            "agent": {**ag_result, "quality": ag_quality},
            "winner": winner,
        })

        time.sleep(2)  # Rate limit buffer

    # Print summary table
    print("\n\n" + "=" * 90)
    print("  📊 BẢNG SO SÁNH KẾT QUẢ")
    print("=" * 90)
    print(f"{'TC':<6} {'Category':<14} {'Chatbot':<12} {'Agent':<12} {'CB Time':<10} {'AG Time':<10} {'CB Tok':<8} {'AG Tok':<8} {'Winner':<12}")
    print("─" * 90)

    cb_wins = ag_wins = draws = 0
    for r in results:
        tc = r["test_case"]
        cb = r["chatbot"]
        ag = r["agent"]
        w = r["winner"]

        if "Agent" in w:
            ag_wins += 1
        elif "Chatbot" in w:
            cb_wins += 1
        else:
            draws += 1

        print(f"{tc['id']:<6} {tc['category']:<14} {cb['quality']['grade']:<12} {ag['quality']['grade']:<12} {cb['elapsed_ms']:<10} {ag['elapsed_ms']:<10} {cb['total_tokens']:<8} {ag['total_tokens']:<8} {w:<12}")

    print("─" * 90)
    print(f"\n  🏆 Kết quả: Agent thắng {ag_wins}/{len(results)} | Chatbot thắng {cb_wins}/{len(results)} | Hòa {draws}/{len(results)}")

    # Aggregate metrics
    cb_total_tokens = sum(r["chatbot"]["total_tokens"] for r in results)
    ag_total_tokens = sum(r["agent"]["total_tokens"] for r in results)
    cb_total_time = sum(r["chatbot"]["elapsed_ms"] for r in results)
    ag_total_time = sum(r["agent"]["elapsed_ms"] for r in results)
    cb_total_cost = sum(r["chatbot"]["cost_estimate"] for r in results)
    ag_total_cost = sum(r["agent"]["cost_estimate"] for r in results)

    print(f"\n  📈 Tổng tokens:  Chatbot={cb_total_tokens:,} | Agent={ag_total_tokens:,}")
    print(f"  ⏱️  Tổng thời gian: Chatbot={cb_total_time:,}ms | Agent={ag_total_time:,}ms")
    print(f"  💰 Tổng chi phí: Chatbot=${cb_total_cost:.6f} | Agent=${ag_total_cost:.6f}")

    # Save results to JSON
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "test_cases": len(TEST_CASES),
        "summary": {
            "agent_wins": ag_wins,
            "chatbot_wins": cb_wins,
            "draws": draws,
            "chatbot_total_tokens": cb_total_tokens,
            "agent_total_tokens": ag_total_tokens,
            "chatbot_total_time_ms": cb_total_time,
            "agent_total_time_ms": ag_total_time,
            "chatbot_total_cost": cb_total_cost,
            "agent_total_cost": ag_total_cost,
        },
        "results": []
    }

    for r in results:
        output["results"].append({
            "id": r["test_case"]["id"],
            "category": r["test_case"]["category"],
            "query": r["test_case"]["query"],
            "winner": r["winner"],
            "chatbot": {
                "grade": r["chatbot"]["quality"]["grade"],
                "elapsed_ms": r["chatbot"]["elapsed_ms"],
                "tokens": r["chatbot"]["total_tokens"],
                "llm_calls": r["chatbot"]["llm_calls"],
                "answer_preview": r["chatbot"]["answer"][:300],
            },
            "agent": {
                "grade": r["agent"]["quality"]["grade"],
                "elapsed_ms": r["agent"]["elapsed_ms"],
                "tokens": r["agent"]["total_tokens"],
                "llm_calls": r["agent"]["llm_calls"],
                "answer_preview": r["agent"]["answer"][:300],
            }
        })

    results_path = os.path.join("logs", "evaluation_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  💾 Kết quả đã lưu: {results_path}")
    print("=" * 90)

    return output


if __name__ == "__main__":
    run_evaluation()
