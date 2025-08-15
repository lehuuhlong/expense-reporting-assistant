"""
🧠 INTELLIGENT CONVERSATION SUMMARIZATION SYSTEM
===================================================

Giải pháp tối ưu cho việc lưu trữ và tóm tắt lịch sử chat:
- Sliding Window Memory với auto-summarization
- Context-aware Summarization cho expense domain  
- Token-efficient Storage trong ChromaDB
- Semantic Compression để giữ thông tin quan trọng

Author: AI Expert Team
Date: August 2025
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
import tiktoken
import chromadb
from chromadb.utils import embedding_functions


@dataclass
class ConversationSegment:
    """Đại diện cho một đoạn hội thoại đã được tóm tắt"""
    start_time: str
    end_time: str
    message_count: int
    summary: str
    key_expenses: List[Dict[str, Any]]
    important_context: Dict[str, Any]
    tokens_saved: int
    original_tokens: int


class IntelligentConversationSummarizer:
    """
    🎯 Hệ thống tóm tắt hội thoại thông minh cho expense domain
    
    Features:
    - Sliding window với threshold tự động
    - Context-aware summarization
    - Expense-specific information extraction
    - Token optimization với semantic preservation
    """
    
    def __init__(self, openai_client: OpenAI, max_window_size: int = 10, 
                 summarize_threshold: int = 8, max_tokens_per_summary: int = 200):
        """
        Khởi tạo conversation summarizer
        
        Args:
            openai_client: OpenAI client instance
            max_window_size: Số messages tối đa trong active window
            summarize_threshold: Trigger summarization khi đạt threshold
            max_tokens_per_summary: Giới hạn tokens cho mỗi summary
        """
        self.client = openai_client
        self.max_window_size = max_window_size
        self.summarize_threshold = summarize_threshold
        self.max_tokens_per_summary = max_tokens_per_summary
        
        # Token counter để tối ưu cost
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        
        # ChromaDB cho lưu trữ summaries
        self.chroma_client = chromadb.PersistentClient(path="./data/conversation_summaries")
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Collection cho conversation summaries
        self.summaries_collection = self.chroma_client.get_or_create_collection(
            name="conversation_summaries",
            embedding_function=self.embedding_fn,
            metadata={"description": "Summarized conversation segments"}
        )
        
        # Collection cho active conversations
        self.active_conversations = {}
        
        # Expense domain keywords for context extraction
        self.expense_keywords = {
            'amounts': r'(\d+(?:[,\.]\d+)?)\s*(?:triệu|tr|nghìn|k|VND|vnđ|đồng)',
            'categories': ['ăn', 'uống', 'meal', 'khách sạn', 'hotel', 'đi lại', 'travel', 'văn phòng', 'office'],
            'actions': ['kê khai', 'declare', 'báo cáo', 'report', 'hoàn trả', 'reimburse'],
            'policies': ['chính sách', 'policy', 'quy định', 'giới hạn', 'limit', 'hóa đơn', 'receipt']
        }
    
    def count_tokens(self, text: str) -> int:
        """Đếm số tokens trong text"""
        return len(self.encoding.encode(text))
    
    def extract_expense_context(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Trích xuất context quan trọng liên quan đến expense từ messages
        
        Returns:
            Dict chứa expenses, policies, user intents đã được extract
        """
        context = {
            'declared_expenses': [],
            'policy_questions': [],
            'calculation_requests': [],
            'report_requests': [],
            'user_preferences': {},
            'important_numbers': []
        }
        
        for msg in messages:
            content = msg.get('content', '').lower()
            role = msg.get('role', '')
            
            # Extract declared expenses
            amounts = re.findall(self.expense_keywords['amounts'], content)
            if amounts and role == 'user':
                expense_info = {
                    'amounts': amounts,
                    'content': msg.get('content', '')[:100],
                    'timestamp': msg.get('timestamp', '')
                }
                context['declared_expenses'].append(expense_info)
            
            # Extract policy questions
            if any(keyword in content for keyword in self.expense_keywords['policies']):
                context['policy_questions'].append({
                    'question': msg.get('content', '')[:100],
                    'timestamp': msg.get('timestamp', '')
                })
            
            # Extract calculation/report requests
            if any(action in content for action in self.expense_keywords['actions']):
                if 'báo cáo' in content or 'report' in content:
                    context['report_requests'].append(msg.get('content', '')[:100])
                else:
                    context['calculation_requests'].append(msg.get('content', '')[:100])
        
        return context
    
    def create_domain_specific_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        Tạo summary tối ưu cho expense domain với focus vào thông tin quan trọng
        """
        expense_context = self.extract_expense_context(messages)
        
        # Tạo prompt tối ưu cho expense summarization
        system_prompt = """Bạn là chuyên gia tóm tắt hội thoại cho hệ thống báo cáo chi phí. 
        
        NHIỆM VỤ: Tóm tắt hội thoại sau đây, tập trung vào:
        1. 💰 Chi phí đã kê khai (số tiền, danh mục, mô tả)
        2. ❓ Câu hỏi về chính sách công ty
        3. 📊 Yêu cầu tính toán hoặc báo cáo
        4. 🎯 Context quan trọng cho cuộc trò chuyện tiếp theo
        
        ĐỊNH DẠNG OUTPUT:
        💰 CHI PHÍ: [liệt kê chi phí đã kê khai]
        ❓ CHÍNH SÁCH: [câu hỏi về policies đã được trả lời]
        📊 YÊU CẦU: [các yêu cầu tính toán/báo cáo]
        🔔 CONTEXT: [thông tin quan trọng cần nhớ]
        
        Giữ summary ngắn gọn nhưng đầy đủ thông tin quan trọng (max 300 words)."""
        
        # Chuẩn bị conversation text
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in messages[-self.summarize_threshold:]
        ])
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Hội thoại cần tóm tắt:\n\n{conversation_text}"}
                ],
                max_tokens=self.max_tokens_per_summary,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            # Fallback summary nếu API call fails
            return self.create_fallback_summary(messages, expense_context)
    
    def create_fallback_summary(self, messages: List[Dict[str, Any]], 
                               expense_context: Dict[str, Any]) -> str:
        """Tạo summary backup không cần API call"""
        summary_parts = []
        
        if expense_context['declared_expenses']:
            expenses_text = f"💰 CHI PHÍ: {len(expense_context['declared_expenses'])} khoản đã kê khai"
            summary_parts.append(expenses_text)
        
        if expense_context['policy_questions']:
            policies_text = f"❓ CHÍNH SÁCH: {len(expense_context['policy_questions'])} câu hỏi"
            summary_parts.append(policies_text)
        
        if expense_context['report_requests']:
            reports_text = f"📊 YÊU CẦU: {len(expense_context['report_requests'])} yêu cầu báo cáo"
            summary_parts.append(reports_text)
        
        summary_parts.append(f"🔔 CONTEXT: {len(messages)} tin nhắn đã được tóm tắt")
        
        return "\n".join(summary_parts)
    
    def should_summarize(self, session_id: str) -> bool:
        """Kiểm tra xem có nên trigger summarization không"""
        if session_id not in self.active_conversations:
            return False
        
        messages = self.active_conversations[session_id]['messages']
        return len(messages) >= self.summarize_threshold
    
    def add_message(self, session_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thêm message vào conversation và trigger summarization nếu cần
        
        Returns:
            Dict chứa info về summarization status và token savings
        """
        # Khởi tạo session nếu chưa tồn tại
        if session_id not in self.active_conversations:
            self.active_conversations[session_id] = {
                'messages': [],
                'summaries': [],
                'total_tokens_saved': 0,
                'created_at': datetime.now().isoformat()
            }
        
        # Thêm timestamp vào message
        message['timestamp'] = datetime.now().isoformat()
        
        # Thêm message vào active window
        self.active_conversations[session_id]['messages'].append(message)
        
        result = {
            'summarized': False,
            'tokens_saved': 0,
            'summary_created': None,
            'active_messages': len(self.active_conversations[session_id]['messages'])
        }
        
        # Kiểm tra xem có cần summarize không
        if self.should_summarize(session_id):
            summary_result = self.summarize_conversation_window(session_id)
            result.update(summary_result)
        
        return result
    
    def summarize_conversation_window(self, session_id: str) -> Dict[str, Any]:
        """
        Tóm tắt conversation window hiện tại và lưu vào ChromaDB
        """
        if session_id not in self.active_conversations:
            return {'error': 'Session not found'}
        
        messages = self.active_conversations[session_id]['messages']
        
        # Tính toán tokens trước khi summarize
        original_tokens = sum(self.count_tokens(msg.get('content', '')) for msg in messages)
        
        # Tạo summary
        summary_text = self.create_domain_specific_summary(messages)
        summary_tokens = self.count_tokens(summary_text)
        tokens_saved = original_tokens - summary_tokens
        
        # Extract key information
        expense_context = self.extract_expense_context(messages)
        
        # Tạo conversation segment
        segment = ConversationSegment(
            start_time=messages[0].get('timestamp', ''),
            end_time=messages[-1].get('timestamp', ''),
            message_count=len(messages),
            summary=summary_text,
            key_expenses=expense_context['declared_expenses'],
            important_context=expense_context,
            tokens_saved=tokens_saved,
            original_tokens=original_tokens
        )
        
        # Lưu vào ChromaDB
        segment_id = f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            self.summaries_collection.add(
                documents=[summary_text],
                ids=[segment_id],
                metadatas=[{
                    'session_id': session_id,
                    'start_time': segment.start_time,
                    'end_time': segment.end_time,
                    'message_count': segment.message_count,
                    'tokens_saved': tokens_saved,
                    'original_tokens': original_tokens,
                    'expense_count': len(expense_context['declared_expenses']),
                    'policy_questions': len(expense_context['policy_questions']),
                    'summary_type': 'conversation_segment'
                }]
            )
            
            # Lưu vào active conversation
            self.active_conversations[session_id]['summaries'].append(segment)
            self.active_conversations[session_id]['total_tokens_saved'] += tokens_saved
            
            # Giữ lại chỉ một số messages gần nhất
            keep_recent = max(2, self.max_window_size - self.summarize_threshold)
            self.active_conversations[session_id]['messages'] = messages[-keep_recent:]
            
            return {
                'summarized': True,
                'tokens_saved': tokens_saved,
                'summary_created': summary_text,
                'segment_id': segment_id,
                'active_messages': len(self.active_conversations[session_id]['messages'])
            }
            
        except Exception as e:
            return {
                'summarized': False,
                'error': f"Failed to save summary: {str(e)}",
                'tokens_saved': 0
            }
    
    def get_conversation_context(self, session_id: str, max_summaries: int = 3) -> str:
        """
        Lấy context từ summaries và active messages để gửi cùng request mới
        
        Returns:
            Context string được tối ưu hóa để gửi kèm với current conversation
        """
        if session_id not in self.active_conversations:
            return ""
        
        context_parts = []
        
        # Lấy recent summaries từ ChromaDB
        try:
            recent_summaries = self.summaries_collection.query(
                query_texts=[""],
                n_results=max_summaries,
                where={"session_id": session_id}
            )
            
            if recent_summaries['documents']:
                context_parts.append("📚 LỊCH SỬ ĐÃ TÓM TẮT:")
                for summary in recent_summaries['documents'][0]:
                    context_parts.append(f"• {summary}")
                context_parts.append("")
        except Exception:
            pass
        
        # Thêm active messages
        active_messages = self.active_conversations[session_id]['messages']
        if active_messages:
            context_parts.append("💬 TIN NHẮN GÂN ĐÂY:")
            for msg in active_messages[-5:]:  # Chỉ lấy 5 messages gần nhất
                role_emoji = "👤" if msg['role'] == 'user' else "🤖"
                context_parts.append(f"{role_emoji} {msg['content'][:100]}...")
        
        return "\n".join(context_parts)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Lấy thống kê về session"""
        if session_id not in self.active_conversations:
            return {'error': 'Session not found'}
        
        session_data = self.active_conversations[session_id]
        
        return {
            'session_id': session_id,
            'active_messages': len(session_data['messages']),
            'total_summaries': len(session_data['summaries']),
            'total_tokens_saved': session_data['total_tokens_saved'],
            'created_at': session_data['created_at'],
            'last_activity': session_data['messages'][-1]['timestamp'] if session_data['messages'] else None
        }
    
    def cleanup_old_sessions(self, days_threshold: int = 7):
        """Dọn dẹp các sessions cũ"""
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        sessions_to_remove = []
        for session_id, data in self.active_conversations.items():
            created_at = datetime.fromisoformat(data['created_at'])
            if created_at < cutoff_date:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.active_conversations[session_id]
        
        return len(sessions_to_remove)


# Utility functions để integrate với existing system
def create_summarizer(openai_client: OpenAI) -> IntelligentConversationSummarizer:
    """Factory function để tạo summarizer instance"""
    return IntelligentConversationSummarizer(
        openai_client=openai_client,
        max_window_size=10,
        summarize_threshold=8,
        max_tokens_per_summary=200
    )


def integrate_with_expense_assistant(assistant_instance, summarizer: IntelligentConversationSummarizer):
    """
    Integrate summarizer với ExpenseAssistant existing instance
    
    Patches existing methods để thêm auto-summarization
    """
    original_add_user_message = assistant_instance.add_user_message
    original_add_assistant_message = assistant_instance.add_assistant_message
    
    # Generate session ID cho assistant instance
    if not hasattr(assistant_instance, '_summarizer_session_id'):
        assistant_instance._summarizer_session_id = f"assistant_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def enhanced_add_user_message(content):
        # Gọi original method
        original_add_user_message(content)
        
        # Thêm vào summarizer
        summarizer.add_message(
            assistant_instance._summarizer_session_id,
            {'role': 'user', 'content': content}
        )
    
    def enhanced_add_assistant_message(content):
        # Gọi original method
        original_add_assistant_message(content)
        
        # Thêm vào summarizer
        summarizer.add_message(
            assistant_instance._summarizer_session_id,
            {'role': 'assistant', 'content': content}
        )
    
    # Patch methods
    assistant_instance.add_user_message = enhanced_add_user_message
    assistant_instance.add_assistant_message = enhanced_add_assistant_message
    assistant_instance._summarizer = summarizer
    
    return assistant_instance


if __name__ == "__main__":
    # Demo usage
    from openai import OpenAI
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    client = OpenAI(
        api_key=os.getenv("AZURE_OPENAI_LLM_API_KEY"),
        base_url=os.getenv("AZURE_OPENAI_LLM_ENDPOINT")
    )
    
    # Tạo summarizer
    summarizer = create_summarizer(client)
    
    # Demo conversation
    session_id = "demo_session"
    
    # Simulate conversation
    messages = [
        {"role": "user", "content": "Tôi muốn kê khai chi phí ăn trưa 150k"},
        {"role": "assistant", "content": "Đã ghi nhận chi phí ăn trưa 150,000 VND"},
        {"role": "user", "content": "Còn chi phí taxi 50k"},
        {"role": "assistant", "content": "Đã ghi nhận chi phí taxi 50,000 VND"},
        {"role": "user", "content": "Giới hạn chi phí ăn uống là bao nhiều?"},
        {"role": "assistant", "content": "Giới hạn chi phí ăn uống là 1,000,000 VND/ngày"},
        {"role": "user", "content": "Tôi cần báo cáo chi phí tháng này"},
        {"role": "assistant", "content": "Đang tạo báo cáo chi phí cho bạn..."},
        {"role": "user", "content": "Chi phí khách sạn 2 triệu có được hoàn không?"},
        {"role": "assistant", "content": "Chi phí khách sạn 2,000,000 VND được hoàn trả nếu có hóa đơn"},
    ]
    
    # Add messages và trigger summarization
    for msg in messages:
        result = summarizer.add_message(session_id, msg)
        if result['summarized']:
            print(f"✅ Summarized! Tokens saved: {result['tokens_saved']}")
            print(f"📝 Summary: {result['summary_created'][:100]}...")
    
    # Lấy context để sử dụng
    context = summarizer.get_conversation_context(session_id)
    print(f"\n🔄 Context for next conversation:\n{context}")
    
    # Session stats
    stats = summarizer.get_session_stats(session_id)
    print(f"\n📊 Session Stats: {stats}")
