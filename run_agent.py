#!/usr/bin/env python3
"""
Interactive CLI for the Real Estate Consultation Agent.
Demonstrates the ReAct loop with Vinhomes Ocean Park property data.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.gemini_provider import GeminiProvider
from src.core.openai_provider import OpenAIProvider
from src.agent.agent import ReActAgent
from src.tools import ALL_TOOLS as TOOLS
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


def create_provider():
    """Create the LLM provider based on environment config."""
    provider_name = os.getenv("DEFAULT_PROVIDER", "google")
    model_name = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
    
    if provider_name == "google":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            print("❌ Error: GEMINI_API_KEY chưa được cấu hình trong file .env")
            sys.exit(1)
        return GeminiProvider(model_name=model_name, api_key=api_key)
    
    elif provider_name == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            print("❌ Error: OPENAI_API_KEY chưa được cấu hình trong file .env")
            sys.exit(1)
        return OpenAIProvider(model_name=model_name, api_key=api_key)
    
    else:
        print(f"❌ Error: Provider '{provider_name}' không được hỗ trợ. Chọn 'google' hoặc 'openai'.")
        sys.exit(1)


def print_banner():
    """Print the welcome banner."""
    print("\n" + "=" * 70)
    print("  🏠  TRỢ LÝ TƯ VẤN BẤT ĐỘNG SẢN VINHOMES OCEAN PARK 1")
    print("  ⚡  Powered by ReAct Agent + Gemini AI")
    print("=" * 70)
    print()
    print("  Hỏi bất cứ điều gì về căn hộ tại Vinhomes Ocean Park 1:")
    print("  • Tìm căn hộ theo tiêu chí (giá, loại, hướng, tầng)")
    print("  • Xem chi tiết và liên hệ chủ nhà")  
    print("  • Phân tích giá thị trường theo dự án")
    print()
    print("  Gõ 'quit' hoặc 'exit' để thoát.")
    print("  Gõ 'stats' để xem thống kê phiên làm việc.")
    print("-" * 70)


def print_session_stats():
    """Print session performance statistics."""
    metrics = tracker.session_metrics
    if not metrics:
        print("\n📊 Chưa có dữ liệu thống kê.")
        return
    
    total_requests = len(metrics)
    total_tokens = sum(m.get("total_tokens", 0) for m in metrics)
    total_latency = sum(m.get("latency_ms", 0) for m in metrics)
    total_cost = sum(m.get("cost_estimate", 0) for m in metrics)
    avg_latency = total_latency / total_requests if total_requests else 0
    
    print("\n" + "=" * 50)
    print("  📊 THỐNG KÊ PHIÊN LÀM VIỆC")
    print("=" * 50)
    print(f"  Tổng số request LLM : {total_requests}")
    print(f"  Tổng tokens sử dụng : {total_tokens:,}")
    print(f"  Tổng thời gian phản hồi: {total_latency:,}ms")
    print(f"  Thời gian TB/request : {avg_latency:,.0f}ms")
    print(f"  Chi phí ước tính     : ${total_cost:.6f}")
    print("=" * 50)


def run_demo():
    """Run predefined demo queries to showcase the agent."""
    demo_queries = [
        "Tìm cho tôi các căn STUDIO hướng Tây Nam tại dự án The London.",
        "Giá trung bình của căn 2PN ở The Paris là bao nhiêu?",
    ]
    
    print("\n🎬 CHẠY DEMO VỚI CÁC CÂU HỎI MẪU...\n")
    
    provider = create_provider()
    agent = ReActAgent(llm=provider, tools=TOOLS, max_steps=5)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'='*60}")
        print(f"  Demo #{i}: {query}")
        print(f"{'='*60}\n")
        
        answer = agent.run(query)
        print(f"\n🤖 Trả lời:\n{answer}\n")
    
    print_session_stats()


def main():
    """Main interactive loop."""
    print_banner()
    
    # Check for demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
        return
    
    # Create provider and agent
    provider = create_provider()
    agent = ReActAgent(llm=provider, tools=TOOLS, max_steps=5)
    
    print(f"\n✅ Agent khởi tạo thành công!")
    print(f"   Provider: {os.getenv('DEFAULT_PROVIDER', 'google')}")
    print(f"   Model: {provider.model_name}")
    print(f"   Số tools: {len(TOOLS)}")
    print()
    
    while True:
        try:
            user_input = input("🧑 Bạn: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Tạm biệt!")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print_session_stats()
            print("\n👋 Tạm biệt! Hẹn gặp lại.")
            break
        
        if user_input.lower() == "stats":
            print_session_stats()
            continue
        
        print("\n🔄 Đang xử lý...\n")
        
        try:
            answer = agent.run(user_input)
            print(f"\n🤖 Trả lời:\n{answer}\n")
        except Exception as e:
            print(f"\n❌ Lỗi: {e}\n")
            logger.error(f"Agent error: {e}")
        
        print("-" * 70)


if __name__ == "__main__":
    main()
