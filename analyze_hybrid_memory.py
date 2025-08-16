#!/usr/bin/env python3
"""
🔍 Phân tích Hybrid Memory và Web App
"""

def analyze_hybrid_memory_necessity():
    """Phân tích xem Hybrid Memory có cần thiết không"""
    
    print("🔍 PHÂN TÍCH HYBRID MEMORY VÀ WEB APP")
    print("=" * 50)
    
    # 1. Test import hybrid memory
    print("1️⃣ Testing Hybrid Memory Import...")
    try:
        from hybrid_memory_fix import RAGExpenseMemoryIntegration
        print("✅ Hybrid Memory import thành công")
        
        # Test khởi tạo
        hybrid = RAGExpenseMemoryIntegration()
        print("✅ Hybrid Memory khởi tạo thành công")
        
    except Exception as e:
        print(f"❌ Hybrid Memory import thất bại: {e}")
        return False
    
    # 2. Phân tích mục đích của Hybrid Memory
    print("\n2️⃣ Mục đích của Hybrid Memory:")
    print("📋 Vấn đề gốc: Chi phí kê khai ở đầu cuộc trò chuyện bị mất")
    print("   khi conversation buffer window (10 messages) bị đầy")
    print("📝 Giải pháp: Lưu trữ chi phí riêng biệt, độc lập với chat memory")
    print("🎯 Tính năng:")
    print("   - Extract chi phí từ user input tự động")
    print("   - Lưu trữ persistent trong session")
    print("   - Generate báo cáo từ toàn bộ chi phí đã lưu")
    
    # 3. Kiểm tra web app hiện tại
    print("\n3️⃣ Phân tích Web App hiện tại...")
    
    # Kiểm tra database.py - có lưu trữ expenses không?
    try:
        from database import ExpenseDB
        db = ExpenseDB()
        print("✅ ExpenseDB có sẵn")
        
        # Check methods của ExpenseDB
        db_methods = [method for method in dir(db) if not method.startswith('_')]
        expense_methods = [m for m in db_methods if 'expense' in m.lower()]
        print(f"📊 ExpenseDB có {len(expense_methods)} expense methods: {expense_methods}")
        
        if expense_methods:
            print("✅ Database đã có tính năng lưu trữ expenses")
        else:
            print("⚠️ Database chưa có tính năng lưu trữ expenses")
            
    except Exception as e:
        print(f"❌ Không thể load ExpenseDB: {e}")
    
    # 4. Kiểm tra smart memory
    print("\n4️⃣ Phân tích Smart Memory...")
    try:
        from smart_memory_integration import SmartConversationMemory
        print("✅ Smart Memory có sẵn")
        print("📝 Smart Memory có thể thay thế một phần Hybrid Memory")
    except Exception as e:
        print(f"❌ Smart Memory không có: {e}")
    
    # 5. Kết luận
    print("\n5️⃣ KẾT LUẬN:")
    print("🤔 Hybrid Memory có cần thiết không?")
    
    return True

def check_webapp_current_features():
    """Kiểm tra tính năng hiện tại của webapp"""
    
    print("\n" + "=" * 50)
    print("📱 PHÂN TÍCH WEBAPP HIỆN TẠI")
    print("=" * 50)
    
    # Kiểm tra functions.py
    try:
        from functions import (
            calculate_reimbursement, 
            validate_expense, 
            format_expense_summary,
            EXPENSE_CATEGORIES
        )
        print("✅ Functions.py có đầy đủ expense functions:")
        print(f"   - calculate_reimbursement: ✅")
        print(f"   - validate_expense: ✅") 
        print(f"   - format_expense_summary: ✅")
        print(f"   - EXPENSE_CATEGORIES: {len(EXPENSE_CATEGORIES)} categories")
        
    except Exception as e:
        print(f"❌ Functions.py có vấn đề: {e}")
    
    # Kiểm tra user session manager
    try:
        from user_session_manager import UserSessionManager
        print("✅ User Session Manager có sẵn")
        print("📝 Có thể lưu expense data trong user session")
    except Exception as e:
        print(f"❌ User Session Manager không có: {e}")
        
    # Kiểm tra RAG integration
    try:
        from rag_integration import get_rag_integration
        rag = get_rag_integration()
        if rag and rag.is_rag_available():
            print("✅ RAG Integration hoạt động tốt")
            print("📝 RAG có thể handle expense queries")
        else:
            print("⚠️ RAG Integration không sẵn sàng")
    except Exception as e:
        print(f"❌ RAG Integration có vấn đề: {e}")

def recommendation():
    """Đưa ra khuyến nghị"""
    
    print("\n" + "=" * 50)
    print("💡 KHUYẾN NGHỊ")
    print("=" * 50)
    
    print("🎯 Hybrid Memory FIX có cần thiết không?")
    print()
    print("✅ CẦN THIẾT nếu:")
    print("   - User kê khai nhiều chi phí trong 1 session dài")
    print("   - Cần tạo báo cáo từ toàn bộ chi phí session")
    print("   - Chat memory bị giới hạn và làm mất data")
    print()
    print("❌ KHÔNG CẦN THIẾT nếu:")
    print("   - Database đã lưu expenses persistent")
    print("   - User session manager đã handle expense data")
    print("   - Smart memory đã đủ mạnh")
    print()
    print("🔧 GIẢI PHÁP THAY THẾ:")
    print("   1. Sử dụng ExpenseDB + User Session")
    print("   2. Enhance Smart Memory để handle expenses")
    print("   3. RAG Integration tự động extract và lưu")
    print("   4. Simple expense state trong session storage")

if __name__ == "__main__":
    success = analyze_hybrid_memory_necessity()
    if success:
        check_webapp_current_features()
    recommendation()
