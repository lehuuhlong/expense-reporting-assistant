# Giao Diện Dòng Lệnh cho Trợ Lý Chi Phí
"""
Giao diện dòng lệnh tương tác để kiểm tra chatbot với 
cuộc hội thoại nhiều lượt, hiển thị phản hồi và quản lý trạng thái cuộc trò chuyện.
"""

import json
from typing import List, Dict, Any
from expense_assistant import ExpenseAssistant, create_client
from functions import MOCK_EXPENSE_REPORTS, EXPENSE_POLICIES, AVAILABLE_FUNCTIONS, SAMPLE_USER_QUERIES

def display_response(response_data: Dict[str, Any]):
    """Hiển thị phản hồi đã được định dạng từ assistant."""
    print("\n" + "="*50)
    print("🤖 PHẢN HỒI TỪ TRỢ LÝ:")
    print("="*50)
    
    # Nội dung phản hồi chính
    if response_data.get("content"):
        print(response_data["content"])
    
    # Chi tiết các lần gọi hàm
    if response_data.get("tool_calls"):
        print("\n🔧 CÁC CHỨC NĂNG ĐÃ SỬ DỤNG:")
        for i, tool_call in enumerate(response_data["tool_calls"], 1):
            print(f"\n   {i}. {tool_call['function']}()")
            print(f"      Tham số: {json.dumps(tool_call['arguments'], indent=6, ensure_ascii=False)}")
            print(f"      Kết quả: {json.dumps(tool_call['result'], indent=6, ensure_ascii=False)}")
    
    # Sử dụng token
    if response_data.get("total_tokens"):
        print(f"\n📊 Tokens đã sử dụng: {response_data['total_tokens']}")
    
    print("="*50)

def run_interactive_chat():
    """Chạy phiên chat tương tác với assistant."""
    print("🚀 Bắt Đầu Chat Tương Tác với Trợ Lý Chi Phí")
    print("="*60)
    print("💡 Mẹo:")
    print("   • Gõ 'help' để xem câu hỏi mẫu")
    print("   • Gõ 'clear' để đặt lại cuộc trò chuyện")
    print("   • Gõ 'summary' để xem thống kê cuộc trò chuyện")
    print("   • Gõ 'quit' hoặc 'exit' để kết thúc phiên")
    print("="*60)
    
    # Khởi tạo assistant
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
    
    while True:
        try:
            # Nhận đầu vào từ người dùng
            user_input = input("\n👤 Bạn: ").strip()
            
            # Xử lý các lệnh đặc biệt
            if user_input.lower() in ['quit', 'exit', 'q', 'thoat']:
                print("\n👋 Cảm ơn bạn đã sử dụng Trợ Lý Chi Phí! Tạm biệt!")
                break
            
            elif user_input.lower() in ['clear', 'xoa']:
                assistant.clear_conversation()
                print("\n🔄 Cuộc trò chuyện đã được xóa. Bắt đầu mới!")
                continue
            
            elif user_input.lower() in ['summary', 'tong-ket']:
                print(f"\n{assistant.get_conversation_summary()}")
                continue
            
            elif user_input.lower() in ['help', 'giup-do']:
                print("\n📚 CÂU HỎI MẪU:")
                for i, query in enumerate(SAMPLE_USER_QUERIES[:5], 1):
                    print(f"   {i}. {query}")
                print("\n💰 TÍNH TOÁN CHI PHÍ MẪU:")
                print("   Tính hoàn tiền cho: ăn trưa 900.000 VNĐ, taxi 600.000 VNĐ, văn phòng phẩm 1.800.000 VNĐ")
                continue
            
            elif not user_input:
                print("   Vui lòng nhập tin nhắn hoặc lệnh.")
                continue
            
            # Nhận và hiển thị phản hồi
            print("\n🤔 Đang xử lý...")
            response = assistant.get_response(user_input)
            display_response(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Chat bị gián đoạn. Tạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {str(e)}")
            print("   Vui lòng thử lại hoặc gõ 'quit' để thoát.")

def run_batch_chat(queries: List[str], batch_size: int = 3) -> List[Dict[str, Any]]:
    """
    Chạy batch chat với nhiều queries cùng lúc.
    
    Args:
        queries: Danh sách các câu hỏi/queries
        batch_size: Kích thước batch
        
    Returns:
        Danh sách kết quả
    """
    print(f"🚀 Bắt Đầu Batch Chat với {len(queries)} queries")
    print("="*60)
    
    # Khởi tạo assistant
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
    
    # Process batch
    results = assistant.process_batch_requests(queries, batch_size)
    
    # Hiển thị kết quả
    print(f"\n📋 CHI TIẾT KẾT QUẢ BATCH:")
    print("="*60)
    
    for i, result in enumerate(results, 1):
        print(f"\n--- Kết quả {i}/{len(results)} ---")
        print(f"🔹 Input: {result['input']}")
        print(f"🔹 Batch: {result.get('batch_index', 'N/A')}")
        print(f"🔹 Tokens: {result.get('total_tokens', 0)}")
        
        if "error" in result:
            print(f"❌ Lỗi: {result['error']}")
        else:
            content = result['content']
            if len(content) > 150:
                print(f"💬 Phản hồi: {content[:150]}...")
            else:
                print(f"💬 Phản hồi: {content}")
            
            if result.get('tool_calls'):
                print(f"🔧 Functions gọi: {len(result['tool_calls'])}")
                for tool_call in result['tool_calls']:
                    print(f"   • {tool_call['function']}()")
    
    return results

def run_expense_batch_processing(expenses: List[Dict] = None) -> Dict[str, Any]:
    """
    Xử lý batch các chi phí để tính toán và xác thực hàng loạt.
    
    Args:
        expenses: Danh sách chi phí (mặc định sử dụng MOCK_EXPENSE_REPORTS)
        
    Returns:
        Kết quả xử lý batch
    """
    if expenses is None:
        expenses = MOCK_EXPENSE_REPORTS
    
    print(f"💰 Bắt Đầu Xử Lý Batch Chi Phí")
    print("="*60)
    print(f"📊 Đang xử lý {len(expenses)} chi phí...")
    
    # Khởi tạo assistant
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
    
    # Process expense batch
    result = assistant.process_expense_batch(expenses)
    
    # Hiển thị kết quả chi tiết
    print(f"\n📋 KẾT QUẢ XỬ LÝ BATCH:")
    print("="*60)
    
    stats = result["statistics"]
    print(f"📊 THỐNG KÊ TỔNG QUAN:")
    print(f"   • Tổng chi phí: {stats['total_submitted']:,.0f} VNĐ")
    print(f"   • Tổng hoàn trả: {stats['total_reimbursed']:,.0f} VNĐ")
    print(f"   • Tiết kiệm: {stats['savings']:,.0f} VNĐ")
    print(f"   • Chi phí hợp lệ: {stats['valid_count']}/{result['total_expenses']}")
    print(f"   • Chi phí có cảnh báo: {stats['warnings_count']}")
    print(f"   • Chi phí không hợp lệ: {stats['invalid_count']}")
    
    print(f"\n💰 CHI TIẾT HOÀN TRẢ:")
    for item in result["reimbursement_calculation"]["breakdown"]:
        print(f"   • {item['category']}: {item['amount_submitted']:,.0f} VNĐ → {item['amount_reimbursed']:,.0f} VNĐ")
        print(f"     {item['note']}")
    
    print(f"\n⚠️  CẢNH BÁO VÀ LỖI:")
    for validation in result["validation_results"]:
        if validation["warnings"] or validation["errors"]:
            expense = validation["expense"]
            print(f"   • Chi phí #{validation['expense_index']}: {expense.get('description', 'N/A')}")
            for warning in validation["warnings"]:
                print(f"     ⚠️  {warning}")
            for error in validation["errors"]:
                print(f"     ❌ {error}")
    
    return result

def quick_batch_demo():
    """Demo nhanh tính năng batching."""
    print("🎯 DEMO NHANH TÍNH NĂNG BATCHING")
    print("="*50)
    
    # Demo 1: Batch chat queries
    print("\n1️⃣ DEMO BATCH CHAT:")
    sample_queries = [
        "Giới hạn chi phí ăn uống là bao nhiều?",
        "Tôi có cần hóa đơn cho taxi 300.000 VNĐ không?",
        "Tính hoàn trả cho ăn uống 1.200.000 VNĐ",
        "Chính sách về chi phí đi lại là gì?"
    ]
    
    batch_results = run_batch_chat(sample_queries, batch_size=2)
    
    print(f"\n📊 Kết quả batch chat: {len(batch_results)} phản hồi")
    
    # Demo 2: Batch expense processing
    print(f"\n2️⃣ DEMO BATCH EXPENSE PROCESSING:")
    expense_results = run_expense_batch_processing()
    
    print(f"\n✅ Demo hoàn thành! Đã xử lý {len(batch_results)} queries và {expense_results['total_expenses']} chi phí.")

def run_batch_test(queries: List[str]) -> List[Dict]:
    """
    Chạy kiểm tra hàng loạt với nhiều truy vấn.
    
    Args:
        queries: Danh sách các truy vấn kiểm tra
        
    Returns:
        Danh sách dữ liệu phản hồi cho mỗi truy vấn
    """
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
    
    print(f"🧪 Chạy kiểm tra hàng loạt với {len(queries)} truy vấn...")
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Kiểm tra {i}/{len(queries)} ---")
        print(f"Truy vấn: {query}")
        
        response = assistant.get_response(query)
        results.append({
            "query": query,
            "response": response,
            "has_function_calls": len(response.get("tool_calls", [])) > 0,
            "token_count": response.get("total_tokens", 0)
        })
        
        print(f"Phản hồi: {response['content'][:100]}..." if len(response['content']) > 100 else response['content'])
        print(f"Gọi hàm: {len(response.get('tool_calls', []))}")
    
    return results

def quick_test():
    """Chạy kiểm tra nhanh của assistant."""
    print("🚀 Kiểm Tra Nhanh Trợ Lý Chi Phí")
    print("="*40)
    
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
    
    test_queries = [
        "Giới hạn chi phí ăn uống là bao nhiều?",
        "Tính hoàn tiền cho: ăn uống 900.000 VNĐ, taxi 600.000 VNĐ, công tác 24.000.000 VNĐ",
        "Tôi có cần hóa đơn cho tất cả chi phí không?",
        "Tôi có chi phí văn phòng phẩm 3.000.000 VNĐ, được phép không?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🧪 Kiểm tra {i}: {query}")
        response = assistant.get_response(query)
        print(f"✅ Phản hồi: {response['content']}")
        if response.get('tool_calls'):
            print(f"🔧 Đã sử dụng {len(response['tool_calls'])} lần gọi hàm")

def quick_demo():
    """Chạy demo nhanh hiển thị chức năng cốt lõi."""
    print("⚡ DEMO NHANH - Chức Năng Cốt Lõi")
    print("="*40)
    
    client = create_client()
    assistant = ExpenseAssistant(client, model="GPT-4o-mini")
    
    test_query = "Tính hoàn tiền cho: ăn trưa 900.000 VNĐ, taxi 600.000 VNĐ, văn phòng phẩm 2.400.000 VNĐ"
    print(f"Truy vấn kiểm tra: {test_query}")
    
    response = assistant.get_response(test_query)
    print(f"\nPhản hồi: {response['content']}")
    
    if response.get('tool_calls'):
        print(f"Gọi hàm: {len(response['tool_calls'])}")
        for tc in response['tool_calls']:
            print(f"  • {tc['function']}() → {tc['result']}")

if __name__ == "__main__":
    print("🎬 Giao Diện Dòng Lệnh Trợ Lý Chi Phí")
    print("="*30)
    print("Các lệnh có sẵn:")
    print("1. run_interactive_chat() - Bắt đầu phiên tương tác")
    print("2. quick_test() - Chạy kiểm tra chức năng nhanh")
    print("3. quick_demo() - Demo nhanh")
    print("4. run_batch_test(queries) - Chạy kiểm tra hàng loạt")
    print("5. run_batch_chat(queries, batch_size) - 🆕 Batch chat mới")
    print("6. run_expense_batch_processing(expenses) - 🆕 Batch xử lý chi phí")
    print("7. quick_batch_demo() - 🆕 Demo tính năng Batching")
    
    print("\n🚀 TÍNH NĂNG BATCHING MỚI:")
    print("   • Xử lý nhiều request cùng lúc")
    print("   • Tối ưu hiệu suất và token usage")
    print("   • Batch processing cho chi phí")
    print("   • Thống kê và báo cáo chi tiết")
    
    print("\n💡 Thử ngay:")
    print("   quick_batch_demo()     # Demo đầy đủ tính năng batching")
    print("   run_batch_chat([...])  # Chat với nhiều queries")
    print("   run_expense_batch_processing()  # Xử lý batch chi phí")
    
    print("\nChọn một tùy chọn:")
    print("1 - Chat tương tác")
    print("2 - Kiểm tra nhanh")
    print("3 - Demo nhanh")
    print("4 - Demo Batching 🆕")
    print("5 - Thoát")
    
    choice = input("\nNhập lựa chọn (1-5): ").strip()
    
    if choice == "1":
        run_interactive_chat()
    elif choice == "2":
        quick_test()
    elif choice == "3":
        quick_demo()
    elif choice == "4":
        quick_batch_demo()
    elif choice == "5":
        print("👋 Tạm biệt!")
    else:
        print("Lựa chọn không hợp lệ. Chạy chat tương tác mặc định...")
        run_interactive_chat()
