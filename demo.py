# Demo và Cách Sử Dụng Mẫu
"""
Trình diễn khả năng của chatbot với các cuộc hội thoại mẫu 
và giới thiệu các tính năng chính.
"""

import json
from expense_assistant import ExpenseAssistant, create_client
from functions import MOCK_EXPENSE_REPORTS, calculate_reimbursement, search_policies, validate_expense, format_expense_summary

def run_demo():
    """Chạy demo toàn diện về khả năng của Trợ Lý Chi Phí."""
    print("🎬 DEMO TRỢ LÝ CHI PHÍ")
    print("="*60)
    print("Trình diễn các tính năng và khả năng chính...\n")
    
    # Tạo assistant mới cho demo
    client = create_client()
    demo_assistant = ExpenseAssistant(client)
    
    # Các kịch bản demo
    demo_scenarios = [
        {
            "title": "📋 Hỏi Đáp Chính Sách",
            "description": "Hỏi về chính sách chi phí công ty",
            "query": "Giới hạn chi phí ăn uống cho công tác trong nước là bao nhiều?"
        },
        {
            "title": "💰 Tính Toán Chi Phí",
            "description": "Tính toán hoàn tiền cho nhiều chi phí",
            "query": "Tính hoàn tiền cho: ăn trưa 900.000 VNĐ, taxi 600.000 VNĐ, văn phòng phẩm 1.800.000 VNĐ, khách sạn 3.600.000 VNĐ"
        },
        {
            "title": "✅ Xác Thực Chi Phí",
            "description": "Xác thực chi phí so với chính sách",
            "query": "Tôi có chi phí ăn tối 4.000.000 VNĐ không có hóa đơn từ tháng trước. Có được không?"
        },
        {
            "title": "🔍 Tìm Kiếm Chính Sách",
            "description": "Tìm kiếm thông tin chính sách cụ thể",
            "query": "Quy định về chi phí đi lại và phê duyệt trước là gì?"
        },
        {
            "title": "🧮 Tính Toán Xăng Xe",
            "description": "Tính toán hoàn tiền xăng xe",
            "query": "Tôi lái xe 300 km để thăm khách hàng. Được hoàn bao nhiều?"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(demo_scenarios, 1):
        print(f"\n🎯 Demo {i}: {scenario['title']}")
        print(f"   {scenario['description']}")
        print(f"   Truy vấn: \"{scenario['query']}\"")
        print("-" * 50)
        
        response = demo_assistant.get_response(scenario['query'])
        
        print(f"🤖 Phản hồi: {response['content']}")
        
        if response.get('tool_calls'):
            print(f"\n🔧 Gọi Hàm: {len(response['tool_calls'])}")
            for j, tool_call in enumerate(response['tool_calls'], 1):
                print(f"   {j}. {tool_call['function']}()")
        
        print(f"\n📊 Tokens: {response.get('total_tokens', 0)}")
        
        results.append({
            "scenario": scenario['title'],
            "query": scenario['query'],
            "response": response['content'],
            "function_calls": len(response.get('tool_calls', [])),
            "tokens": response.get('total_tokens', 0)
        })
    
    # Tóm tắt demo
    print(f"\n🏆 TÓM TẮT DEMO")
    print("="*60)
    total_functions = sum(r['function_calls'] for r in results)
    total_tokens = sum(r['tokens'] for r in results)
    
    print(f"   Kịch bản đã trình diễn: {len(results)}")
    print(f"   Tổng số lần gọi hàm: {total_functions}")
    print(f"   Tổng tokens sử dụng: {total_tokens}")
    print(f"   Trung bình tokens mỗi truy vấn: {total_tokens/len(results):.1f}")
    
    return results

def demonstrate_conversation_flow():
    """Trình diễn khả năng hội thoại nhiều lượt."""
    print("💬 DEMO HỘI THOẠI NHIỀU LƯỢT")
    print("="*50)
    
    # Tạo assistant mới cho demo hội thoại
    client = create_client()
    conv_assistant = ExpenseAssistant(client)
    
    conversation_flow = [
        "Chào bạn, tôi cần giúp đỡ về báo cáo chi phí",
        "Giới hạn chi phí ăn uống là bao nhiều?",
        "Hôm nay tôi ăn trưa hết 1.300.000 VNĐ. Được hoàn bao nhiều?",
        "Còn nếu là công tác quốc tế thì sao?",
        "Tuyệt! Bây giờ tính hoàn tiền cho: ăn uống quốc tế 1.300.000 VNĐ, taxi 900.000 VNĐ, khách sạn 4.000.000 VNĐ",
        "Tôi có cần hóa đơn cho tất cả những chi phí này không?"
    ]
    
    print("Bắt đầu cuộc hội thoại...\n")
    
    for i, message in enumerate(conversation_flow, 1):
        print(f"👤 Người dùng ({i}): {message}")
        
        response = conv_assistant.get_response(message)
        print(f"🤖 Trợ lý: {response['content']}")
        
        if response.get('tool_calls'):
            print(f"   [Đã sử dụng {len(response['tool_calls'])} lần gọi hàm]")
        
        print("-" * 40)
    
    print(f"\n📊 {conv_assistant.get_conversation_summary()}")

def showcase_features():
    """Giới thiệu các tính năng kỹ thuật cụ thể."""
    print("⚡ GIỚI THIỆU TÍNH NĂNG KỸ THUẬT")
    print("="*50)
    
    # Trình diễn các tính năng
    features = [
        {
            "name": "Gọi Hàm",
            "demo": lambda: calculate_reimbursement([
                {"category": "meals", "amount": 900000},
                {"category": "taxi", "amount": 600000}
            ])
        },
        {
            "name": "Tìm Kiếm Chính Sách",
            "demo": lambda: search_policies("yêu cầu hóa đơn")
        },
        {
            "name": "Xác Thực Chi Phí",
            "demo": lambda: validate_expense({
                "category": "meals",
                "amount": 1500000,
                "has_receipt": False,
                "date": "2024-07-15"
            })
        },
        {
            "name": "Tóm Tắt Chi Phí",
            "demo": lambda: format_expense_summary(MOCK_EXPENSE_REPORTS[:3])
        }
    ]
    
    for feature in features:
        print(f"\n🔧 {feature['name']}:")
        try:
            result = feature['demo']()
            print(f"   Kết quả: {json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, dict) else result}")
        except Exception as e:
            print(f"   Lỗi: {str(e)}")

def quick_demo():
    """Chạy demo nhanh hiển thị chức năng cốt lõi."""
    print("⚡ DEMO NHANH - Chức Năng Cốt Lõi")
    print("="*40)
    
    client = create_client()
    quick_assistant = ExpenseAssistant(client)
    
    test_query = "Tính hoàn tiền cho: ăn trưa 900.000 VNĐ, taxi 600.000 VNĐ, văn phòng phẩm 2.400.000 VNĐ"
    print(f"Truy vấn kiểm tra: {test_query}")
    
    response = quick_assistant.get_response(test_query)
    print(f"\nPhản hồi: {response['content']}")
    
    if response.get('tool_calls'):
        print(f"Gọi hàm: {len(response['tool_calls'])}")
        for tc in response['tool_calls']:
            print(f"  • {tc['function']}() → {tc['result']}")

if __name__ == "__main__":
    print("🎬 Demo Trợ Lý Chi Phí")
    print("="*30)
    print("Chọn demo:")
    print("1. Demo nhanh")
    print("2. Demo đầy đủ")
    print("3. Dòng hội thoại")
    print("4. Tính năng kỹ thuật")
    
    choice = input("\nNhập lựa chọn (1-4): ").strip()
    
    if choice == "1":
        quick_demo()
    elif choice == "2":
        run_demo()
    elif choice == "3":
        demonstrate_conversation_flow()
    elif choice == "4":
        showcase_features()
    else:
        print("Lựa chọn không hợp lệ. Chạy demo nhanh...")
        quick_demo()
