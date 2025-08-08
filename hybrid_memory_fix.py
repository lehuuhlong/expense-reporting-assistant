"""
🔧 HYBRID MEMORY FIX: Giải pháp cho vấn đề lưu trữ chi phí
========================================================

VẤNH ĐỀ: "tôi kê khai chi phí ở các prompt trước thì tới prompt cuối cùng lại không tạo báo cáo chi phí được"

NGUYÊN NHÂN: ConversationBufferWindowMemory chỉ giữ 10 messages gần nhất, 
chi phí kê khai ở đầu bị mất khi memory window trượt.

GIẢI PHÁP: HybridExpenseMemory - lưu trữ chi phí riêng biệt, độc lập với conversation memory.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import re

# Import reimbursement functions
try:
    from functions import calculate_reimbursement, validate_expense, EXPENSE_CATEGORIES
except ImportError:
    # Fallback if functions module not available
    calculate_reimbursement = None
    validate_expense = None
    EXPENSE_CATEGORIES = {}


class ImprovedExpenseExtractor:
    """
    Improved expense extraction with better number parsing
    Fixes bug with 'triệu', 'nghìn' parsing
    """
    
    @staticmethod
    def extract_expense_from_text(text: str) -> Optional[Dict[str, Any]]:
        """Extract expense information from user input with improved parsing"""
        
        # Enhanced amount patterns with proper handling
        amount_patterns = [
            (r'(\d+(?:[,\.]\d+)?)\s*(?:triệu|tr)', lambda x: float(x.replace(',', '').replace('.', '')) * 1000000),
            (r'(\d+(?:[,\.]\d+)?)\s*(?:nghìn|k)', lambda x: float(x.replace(',', '').replace('.', '')) * 1000),
            (r'(\d{1,3}(?:[,\.]\d{3})*)\s*(?:VND|vnđ|đồng|vnd)', lambda x: float(x.replace(',', '').replace('.', ''))),
            (r'(\d+)', lambda x: float(x))  # Fallback for simple numbers
        ]
        
        amount = None
        for pattern, converter in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = converter(match.group(1))
                    break
                except (ValueError, AttributeError):
                    continue
        
        # Enhanced category detection
        category_keywords = {
            'meals': ['ăn', 'uống', 'meal', 'food', 'restaurant', 'nhà hàng', 'cơm', 'nước', 'cafe', 'breakfast', 'lunch', 'dinner'],
            'travel': ['đi lại', 'travel', 'xe', 'máy bay', 'tàu', 'bus', 'grab', 'taxi', 'uber', 'flight'],
            'accommodation': ['khách sạn', 'hotel', 'lưu trú', 'phòng', 'homestay', 'motel'],
            'office': ['văn phòng', 'office', 'giấy', 'bút', 'supplies', 'thiết bị', 'văn phòng phẩm', 'stationery']
        }
        
        category = 'other'
        for cat, keywords in category_keywords.items():
            if any(keyword in text.lower() for keyword in keywords):
                category = cat
                break
        
        if amount and amount > 0:
            return {
                "amount": amount,
                "category": category,
                "description": text[:100],
                "raw_text": text,
                "extracted_at": datetime.now().isoformat()
            }
        
        return None

    @staticmethod
    def extract_expenses(text: str) -> List[Dict[str, Any]]:
        """Extract multiple expenses from multi-line or compound user input.

        Cases handled:
        - Nhiều dòng, mỗi dòng một khoản chi.
        - Một dòng chứa nhiều khoản tách bằng dấu phẩy / chấm phẩy.
        - Giữ thứ tự xuất hiện.
        """
        if not text or not text.strip():
            return []

        # Chuẩn hoá về LF và tách theo dòng trước
        segments: List[str] = []
        for raw_line in text.replace('\r', '').split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            # Nếu 1 dòng có nhiều khoản bằng dấu phẩy / chấm phẩy -> tách tiếp
            if any(sep in line for sep in [';', ' , ', ' ,', ', ']):
                sub_parts = [p.strip() for p in re.split(r'[;,]', line) if p.strip()]
                segments.extend(sub_parts)
            else:
                segments.append(line)

        results: List[Dict[str, Any]] = []
        for seg in segments:
            exp = ImprovedExpenseExtractor.extract_expense_from_text(seg)
            if exp:
                # Lưu raw line riêng (nếu bị cắt)
                exp['raw_line'] = seg
                results.append(exp)
        return results


class HybridExpenseMemory:
    """
    Hybrid memory system that works alongside existing RAG memory
    Specifically designed to solve expense persistence issue
    
    Key Features:
    - Persistent expense storage independent of conversation memory
    - Automatic expense capture from any message
    - Comprehensive reporting from ALL captured expenses
    - Session management with unique identifiers
    - Compatible with existing RAG system
    """
    
    def __init__(self, existing_rag_system=None):
        self.rag_system = existing_rag_system
        self.extractor = ImprovedExpenseExtractor()
        
        # Expense-specific storage
        self.expense_store = {
            "active_session": None,
            "sessions": {},
            "current_expenses": [],
            "total_accumulated": 0.0,
            "created_at": datetime.now().isoformat()
        }
        
        # Auto-start default session
        self.start_session()
    
    def start_session(self, session_id: str = None) -> str:
        """Start new expense session"""
        if not session_id:
            session_id = f"expense_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.expense_store["active_session"] = session_id
        self.expense_store["sessions"][session_id] = {
            "created": datetime.now().isoformat(),
            "expenses": [],
            "total": 0.0,
            "last_updated": datetime.now().isoformat()
        }
        self.expense_store["current_expenses"] = []
        self.expense_store["total_accumulated"] = 0.0
        
        print(f"✅ Started expense session: {session_id}")
        return session_id
    
    def capture_expense_from_message(self, message_text: str) -> Optional[Dict[str, Any]]:
        """(Legacy) Capture first expense only for backward compatibility."""
        expenses = self.capture_expenses_from_message(message_text)
        return expenses[0] if expenses else None

    def capture_expenses_from_message(self, message_text: str) -> List[Dict[str, Any]]:
        """Capture ALL expenses from a message (multi-line / multi-expense)."""
        captured: List[Dict[str, Any]] = []
        if not self.expense_store["active_session"]:
            return captured

        all_expenses = self.extractor.extract_expenses(message_text)
        if not all_expenses:
            return captured

        session_id = self.expense_store["active_session"]
        for expense_data in all_expenses:
            expense_entry = {
                **expense_data,
                "id": len(self.expense_store["current_expenses"]) + 1,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            self.expense_store["current_expenses"].append(expense_entry)
            self.expense_store["sessions"][session_id]["expenses"].append(expense_entry)
            self.expense_store["total_accumulated"] += expense_data["amount"]
            self.expense_store["sessions"][session_id]["total"] += expense_data["amount"]
            self.expense_store["sessions"][session_id]["last_updated"] = datetime.now().isoformat()
            captured.append(expense_entry)
            # Reduced logging - only show count occasionally
            if len(captured) == 1 or len(captured) % 5 == 0:
                print(f"💰 Captured {len(captured)} expense(s)")
        return captured
    
    def generate_comprehensive_report(self, format_type: str = "detailed") -> str:
        """
        Generate comprehensive report from ALL captured expenses
        This solves the core issue: report generation from accumulated data
        """
        if not self.expense_store["current_expenses"]:
            return "📋 Không có chi phí nào được kê khai trong phiên này."
        
        expenses = self.expense_store["current_expenses"]
        session_id = self.expense_store["active_session"]
        
        if format_type == "summary":
            return self._generate_summary_report(expenses, session_id)
        else:
            return self._generate_detailed_report(expenses, session_id)
    
    def _generate_detailed_report(self, expenses: List[Dict], session_id: str) -> str:
        """Generate detailed expense report with reimbursement analysis"""
        report_lines = []
        report_lines.append(f"📊 BÁO CÁO CHI PHÍ - Session: {session_id}")
        report_lines.append("=" * 60)
        
        # Calculate reimbursement if function available
        reimbursement_data = None
        if calculate_reimbursement:
            try:
                reimbursement_data = calculate_reimbursement(expenses)
            except Exception as e:
                print(f"⚠️ Reimbursement calculation error: {e}")
        
        # Group by category with reimbursement info
        categories = {}
        for expense in expenses:
            cat = expense.get('category', 'other')
            if cat not in categories:
                categories[cat] = {"items": [], "total": 0, "reimbursed": 0}
            categories[cat]["items"].append(expense)
            categories[cat]["total"] += expense.get('amount', 0)
        
        # Add reimbursement data to categories
        if reimbursement_data:
            for breakdown_item in reimbursement_data.get("breakdown", []):
                cat = breakdown_item.get("category", "other").lower()
                if cat in categories:
                    categories[cat]["reimbursed"] += breakdown_item.get("amount_reimbursed", 0)
        
        # Report each category
        grand_total = 0
        grand_reimbursed = 0
        for category, data in categories.items():
            category_total = data["total"]
            category_reimbursed = data["reimbursed"]
            grand_total += category_total
            grand_reimbursed += category_reimbursed
            
            report_lines.append(f"\n📂 {category.upper()}")
            report_lines.append(f"   Số khoản: {len(data['items'])}")
            report_lines.append(f"   Chi phí: {category_total:,.0f} VND")
            report_lines.append(f"   Hoàn trả: {category_reimbursed:,.0f} VND")
            
            for item in data["items"][:3]:  # Limit to 3 items per category
                desc = item.get('description', 'N/A')[:30]
                amount = item.get('amount', 0)
                report_lines.append(f"   • {desc}... - {amount:,.0f} VND")
            
            if len(data["items"]) > 3:
                report_lines.append(f"   • ... và {len(data['items']) - 3} khoản khác")
        
        report_lines.append("\n" + "=" * 60)
        report_lines.append(f"💰 TỔNG CHI PHÍ: {grand_total:,.0f} VND")
        if grand_reimbursed > 0:
            report_lines.append(f"✅ SỐ TIỀN HOÀN TRẢ: {grand_reimbursed:,.0f} VND")
            report_lines.append(f"� TỰ TÚC: {grand_total - grand_reimbursed:,.0f} VND")
        report_lines.append(f"📊 Tổng số khoản: {len(expenses)}")
        
        return "\n".join(report_lines)
    
    def _generate_summary_report(self, expenses: List[Dict], session_id: str) -> str:
        """Generate summary expense report with reimbursement breakdown"""
        total_amount = sum(exp.get('amount', 0) for exp in expenses)
        categories = {}
        
        # Calculate reimbursement if available
        total_reimbursed = 0
        if calculate_reimbursement:
            try:
                reimbursement_data = calculate_reimbursement(expenses)
                total_reimbursed = reimbursement_data.get("total_reimbursed", 0)
            except Exception:
                pass
        
        for expense in expenses:
            cat = expense.get('category', 'other')
            if cat not in categories:
                categories[cat] = {"count": 0, "total": 0}
            categories[cat]["count"] += 1
            categories[cat]["total"] += expense.get('amount', 0)
        
        summary_lines = []
        summary_lines.append(f"📋 TÓM TẮT CHI PHÍ - {session_id}")
        summary_lines.append("=" * 40)
        summary_lines.append(f"💰 Tổng chi phí: {total_amount:,.0f} VND")
        if total_reimbursed > 0:
            summary_lines.append(f"✅ Hoàn trả: {total_reimbursed:,.0f} VND")
            summary_lines.append(f"� Tự túc: {total_amount - total_reimbursed:,.0f} VND")
        summary_lines.append(f"📊 Số khoản: {len(expenses)}")
        summary_lines.append("")
        
        for category, data in categories.items():
            summary_lines.append(f"• {category.upper()}: {data['count']} khoản - {data['total']:,.0f} VND")
        
        return "\n".join(summary_lines)
    
    def get_expense_summary(self) -> Dict[str, Any]:
        """Get quick expense summary"""
        return {
            "session_id": self.expense_store["active_session"],
            "total_expenses": len(self.expense_store["current_expenses"]),
            "total_amount": self.expense_store["total_accumulated"],
            "categories": len(set(exp.get('category', 'other') for exp in self.expense_store["current_expenses"])),
            "session_start": self.expense_store["sessions"].get(
                self.expense_store["active_session"], {}
            ).get("created", ""),
            "last_updated": self.expense_store["sessions"].get(
                self.expense_store["active_session"], {}
            ).get("last_updated", "")
        }
    
    def export_session_data(self) -> Dict[str, Any]:
        """Export complete session data for backup or integration"""
        return {
            "export_timestamp": datetime.now().isoformat(),
            "active_session": self.expense_store["active_session"],
            "current_session_data": self.expense_store["sessions"].get(
                self.expense_store["active_session"], {}
            ),
            "summary": self.get_expense_summary()
        }
    
    def restore_session_data(self, session_data: Dict[str, Any]) -> bool:
        """Restore session from exported data"""
        try:
            session_id = session_data.get("active_session")
            if session_id and "current_session_data" in session_data:
                self.expense_store["active_session"] = session_id
                self.expense_store["sessions"][session_id] = session_data["current_session_data"]
                self.expense_store["current_expenses"] = session_data["current_session_data"].get("expenses", [])
                self.expense_store["total_accumulated"] = session_data["current_session_data"].get("total", 0.0)
                
                print(f"✅ Restored session: {session_id}")
                return True
        except Exception as e:
            print(f"❌ Failed to restore session: {e}")
        
        return False


# Integration wrapper for easy integration with existing RAG system
class RAGExpenseMemoryIntegration:
    """
    Easy integration wrapper for existing RAG systems
    
    Usage:
    ------
    # Add to your existing chat function:
    expense_memory = RAGExpenseMemoryIntegration()
    
    def chat(user_input):
        # Your existing RAG logic
        response = rag_system.chat(user_input)
        
        # Add expense capture
        expense_memory.process_message(user_input)
        
        # Handle report requests
        if "báo cáo" in user_input.lower():
            report = expense_memory.get_report()
            return report
        
        return response
    """
    
    def __init__(self, rag_system=None):
        self.hybrid_memory = HybridExpenseMemory(rag_system)
        self.report_keywords = [
            'báo cáo', 'report', 'tổng hợp', 'summary', 
            'tổng chi phí', 'total expense', 'chi phí tổng',
            'thống kê', 'thống kê chi phí', 'thong ke'
        ]
    
    def process_message(self, user_input: str) -> List[Dict[str, Any]]:
        """Process user message for expense extraction (supports multi-line)."""
        return self.hybrid_memory.capture_expenses_from_message(user_input)
    
    def is_report_request(self, user_input: str) -> bool:
        """Check if user is requesting expense report"""
        return any(keyword in user_input.lower() for keyword in self.report_keywords)
    
    def get_report(self, format_type: str = "detailed") -> str:
        """Get comprehensive expense report"""
        return self.hybrid_memory.generate_comprehensive_report(format_type)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get expense summary"""
        return self.hybrid_memory.get_expense_summary()
    
    def start_new_session(self) -> str:
        """Start new expense session"""
        return self.hybrid_memory.start_session()


if __name__ == "__main__":
    # Demo usage
    print("🧪 DEMO: Hybrid Memory Fix")
    print("=" * 50)
    
    # Create integration
    expense_integration = RAGExpenseMemoryIntegration()
    
    # Simulate conversation with expenses
    test_messages = [
        "Tôi kê khai chi phí ăn sáng 50,000 VND",
        "Chi thêm 200k cho taxi",
        "Ăn trưa 150 nghìn", 
        "Mua văn phòng phẩm 80k",
        "Chi cafe 35,000 đồng",
        "Taxi về nhà 180k",
        "Ăn tối 300 nghìn",
        "Khách sạn 2 triệu",
        "Breakfast 45k",
        "Uber 120k",
        "Bây giờ tạo báo cáo chi phí tổng hợp"
    ]
    
    print("Processing messages:")
    for i, msg in enumerate(test_messages, 1):
        print(f"{i:2d}. {msg}")
        
        if expense_integration.is_report_request(msg):
            print("    → Report request detected!")
            report = expense_integration.get_report()
            print("\n" + report)
        else:
            expense = expense_integration.process_message(msg)
            if expense:
                print(f"    → Captured: {expense['amount']:,.0f} VND")
    
    print("\n✅ Demo completed - All expenses preserved and reported!")
