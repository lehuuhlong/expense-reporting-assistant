"""
🔗 INTEGRATION MODULE: Smart Conversation Memory
===============================================

Module tích hợp conversation summarizer vào existing system
với các optimizations cho expense reporting domain.

Features:
- Drop-in replacement cho existing conversation history
- Automatic summarization với domain-specific knowledge
- Token cost optimization
- Seamless integration với web app và expense assistant
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from openai import OpenAI

from conversation_summarizer import IntelligentConversationSummarizer, create_summarizer


class SmartConversationMemory:
    """
    🧠 Smart wrapper cho conversation management với auto-summarization
    
    Thay thế existing conversation_history arrays với intelligent memory
    có tính năng tự động tóm tắt và tối ưu tokens.
    """
    
    def __init__(self, openai_client: OpenAI, session_id: str = None):
        """
        Khởi tạo smart conversation memory
        
        Args:
            openai_client: OpenAI client instance
            session_id: Unique session identifier
        """
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.summarizer = create_summarizer(openai_client)
        
        # Compatibility với existing ExpenseAssistant interface
        self._system_prompt = None
        self._conversation_history = []  # For compatibility
        
        # Metrics tracking
        self.total_tokens_saved = 0
        self.total_messages = 0
        self.summaries_created = 0
    
    def append(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thêm message vào conversation với auto-summarization
        
        Compatible với existing conversation_history.append() calls
        """
        self.total_messages += 1
        
        # Add to summarizer
        result = self.summarizer.add_message(self.session_id, message)
        
        # Update metrics
        if result.get('summarized'):
            self.total_tokens_saved += result.get('tokens_saved', 0)
            self.summaries_created += 1
        
        # Maintain compatibility list
        self._conversation_history.append(message)
        if len(self._conversation_history) > 10:  # Keep only recent for compatibility
            self._conversation_history = self._conversation_history[-10:]
        
        return result
    
    def get_optimized_history(self, include_summaries: bool = True) -> List[Dict[str, Any]]:
        """
        Lấy conversation history được tối ưu hóa để gửi lên AI
        
        Returns:
            List of messages bao gồm summaries và recent messages
        """
        messages = []
        
        # Add system prompt nếu có
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        
        if include_summaries:
            # Get conversation context (summaries + recent messages)
            context = self.summarizer.get_conversation_context(self.session_id, max_summaries=2)
            
            if context.strip():
                # Add context như một system message
                context_message = {
                    "role": "system", 
                    "content": f"📚 CONTEXT TỪ HỘI THOẠI TRƯỚC:\n{context}\n\n---CUỘC TRÒ CHUYỆN HIỆN TẠI---"
                }
                messages.append(context_message)
        
        # Add recent active messages
        if self.session_id in self.summarizer.active_conversations:
            active_messages = self.summarizer.active_conversations[self.session_id]['messages']
            messages.extend(active_messages[-5:])  # Chỉ lấy 5 messages gần nhất
        
        return messages
    
    def get_full_history(self) -> List[Dict[str, Any]]:
        """
        Lấy full conversation history (compatibility method)
        Trả về recent messages trong memory
        """
        return self._conversation_history.copy()
    
    def clear(self):
        """Clear conversation history"""
        self._conversation_history = []
        if self._system_prompt:
            self._conversation_history.append({"role": "system", "content": self._system_prompt})
    
    def set_system_prompt(self, prompt: str):
        """Set system prompt"""
        self._system_prompt = prompt
        
        # Clear and re-add system prompt
        self._conversation_history = [{"role": "system", "content": prompt}]
    
    def get_stats(self) -> Dict[str, Any]:
        """Lấy thống kê performance"""
        summarizer_stats = self.summarizer.get_session_stats(self.session_id)
        
        return {
            **summarizer_stats,
            'total_messages_processed': self.total_messages,
            'total_tokens_saved': self.total_tokens_saved,
            'summaries_created': self.summaries_created,
            'efficiency_ratio': f"{(self.total_tokens_saved / max(1, self.total_messages * 50)) * 100:.1f}%"
        }
    
    # Compatibility properties để work với existing code
    @property
    def conversation_history(self):
        """Compatibility property"""
        return self._conversation_history
    
    @conversation_history.setter
    def conversation_history(self, value):
        """Compatibility setter"""
        self._conversation_history = value
    
    def __len__(self):
        """Support len() calls"""
        return len(self._conversation_history)
    
    def __getitem__(self, index):
        """Support indexing"""
        return self._conversation_history[index]
    
    def __iter__(self):
        """Support iteration"""
        return iter(self._conversation_history)


class ExpenseAssistantMemoryUpgrade:
    """
    🚀 Upgrade existing ExpenseAssistant với smart conversation memory
    
    Drop-in replacement cho conversation management
    """
    
    @staticmethod
    def upgrade_assistant(assistant_instance, openai_client: OpenAI) -> 'ExpenseAssistant':
        """
        Upgrade existing ExpenseAssistant instance với smart memory
        
        Args:
            assistant_instance: Existing ExpenseAssistant instance
            openai_client: OpenAI client
            
        Returns:
            Enhanced assistant với smart conversation memory
        """
        # Tạo smart memory
        smart_memory = SmartConversationMemory(
            openai_client=openai_client,
            session_id=f"assistant_{id(assistant_instance)}"
        )
        
        # Migrate existing conversation history
        if hasattr(assistant_instance, 'conversation_history') and assistant_instance.conversation_history:
            for msg in assistant_instance.conversation_history:
                smart_memory.append(msg)
        
        # Replace conversation_history với smart memory
        assistant_instance._original_conversation_history = assistant_instance.conversation_history
        assistant_instance.conversation_history = smart_memory._conversation_history
        assistant_instance._smart_memory = smart_memory
        
        # Patch methods để sử dụng smart memory
        original_add_user_message = getattr(assistant_instance, 'add_user_message', None)
        original_add_assistant_message = getattr(assistant_instance, 'add_assistant_message', None)
        
        def enhanced_add_user_message(content):
            message = {"role": "user", "content": content}
            result = smart_memory.append(message)
            
            # Call original method nếu có
            if original_add_user_message:
                return original_add_user_message(content)
        
        def enhanced_add_assistant_message(content):
            message = {"role": "assistant", "content": content}
            result = smart_memory.append(message)
            
            # Call original method nếu có
            if original_add_assistant_message:
                return original_add_assistant_message(content)
        
        # Patch get_response để sử dụng optimized history
        original_get_response = getattr(assistant_instance, 'get_response', None)
        
        def enhanced_get_response(user_input, **kwargs):
            # Add user message
            enhanced_add_user_message(user_input)
            
            # Get optimized history cho AI call
            optimized_history = smart_memory.get_optimized_history()
            
            # Temporarily replace conversation_history
            original_history = assistant_instance.conversation_history
            assistant_instance.conversation_history = optimized_history
            
            try:
                # Call original method
                if original_get_response:
                    result = original_get_response(user_input, **kwargs)
                    
                    # Extract assistant response từ result
                    if isinstance(result, dict) and 'content' in result:
                        enhanced_add_assistant_message(result['content'])
                    
                    # Add performance metrics
                    if isinstance(result, dict):
                        stats = smart_memory.get_stats()
                        result['memory_stats'] = {
                            'tokens_saved': stats.get('total_tokens_saved', 0),
                            'summaries_created': stats.get('summaries_created', 0),
                            'efficiency': stats.get('efficiency_ratio', '0%')
                        }
                    
                    return result
                else:
                    return {"error": "No get_response method found"}
                    
            finally:
                # Restore original history
                assistant_instance.conversation_history = original_history
        
        # Apply patches
        assistant_instance.add_user_message = enhanced_add_user_message
        assistant_instance.add_assistant_message = enhanced_add_assistant_message
        assistant_instance.get_response = enhanced_get_response
        
        # Add utility methods
        assistant_instance.get_memory_stats = smart_memory.get_stats
        assistant_instance.get_optimized_conversation = smart_memory.get_optimized_history
        
        return assistant_instance


class WebAppMemoryIntegration:
    """
    🌐 Integration cho Flask web application
    
    Upgrade web app sessions với smart conversation memory
    """
    
    @staticmethod
    def upgrade_session(session_data: Dict[str, Any], openai_client: OpenAI) -> Dict[str, Any]:
        """
        Upgrade web app session với smart memory
        
        Args:
            session_data: Existing session data dict
            openai_client: OpenAI client
            
        Returns:
            Enhanced session data với smart memory
        """
        session_id = session_data.get('session_id', f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Tạo smart memory cho session
        smart_memory = SmartConversationMemory(
            openai_client=openai_client,
            session_id=session_id
        )
        
        # Add to session data
        session_data['smart_memory'] = smart_memory
        session_data['memory_type'] = 'smart_conversation'
        session_data['memory_stats'] = smart_memory.get_stats()
        
        return session_data
    
    @staticmethod
    def process_message_with_smart_memory(session_data: Dict[str, Any], 
                                        user_message: str, 
                                        assistant_response: str) -> Dict[str, Any]:
        """
        Process message exchange với smart memory
        
        Returns:
            Updated session data với memory metrics
        """
        if 'smart_memory' not in session_data:
            return session_data
        
        smart_memory = session_data['smart_memory']
        
        # Add user message
        user_result = smart_memory.append({"role": "user", "content": user_message})
        
        # Add assistant response
        assistant_result = smart_memory.append({"role": "assistant", "content": assistant_response})
        
        # Update session stats
        session_data['memory_stats'] = smart_memory.get_stats()
        
        # Add performance info
        session_data['last_memory_result'] = {
            'user_message_result': user_result,
            'assistant_message_result': assistant_result
        }
        
        return session_data
    
    @staticmethod
    def get_context_for_ai(session_data: Dict[str, Any]) -> str:
        """
        Lấy context được tối ưu hóa để gửi cùng request lên AI
        """
        if 'smart_memory' not in session_data:
            return ""
        
        smart_memory = session_data['smart_memory']
        return smart_memory.summarizer.get_conversation_context(smart_memory.session_id)


# Factory functions để dễ dàng integrate
def create_smart_memory_for_session(openai_client: OpenAI, session_id: str = None) -> SmartConversationMemory:
    """Factory function tạo smart memory cho session"""
    return SmartConversationMemory(openai_client, session_id)


def upgrade_existing_assistant(assistant_instance, openai_client: OpenAI):
    """Upgrade existing assistant với smart memory"""
    return ExpenseAssistantMemoryUpgrade.upgrade_assistant(assistant_instance, openai_client)


if __name__ == "__main__":
    # Demo integration
    print("🧠 Smart Conversation Memory Integration Demo")
    print("=" * 50)
    
    # Mock OpenAI client for demo
    class MockOpenAI:
        pass
    
    client = MockOpenAI()
    
    # Demo 1: Smart Memory
    print("1. Creating Smart Memory...")
    smart_memory = create_smart_memory_for_session(client, "demo_session")
    
    # Demo conversation
    messages = [
        {"role": "user", "content": "Kê khai chi phí ăn trưa 150k"},
        {"role": "assistant", "content": "Đã ghi nhận chi phí ăn trưa"},
        {"role": "user", "content": "Chi phí taxi 50k"},
        {"role": "assistant", "content": "Đã ghi nhận chi phí taxi"}
    ]
    
    for msg in messages:
        result = smart_memory.append(msg)
        print(f"   Added message: {msg['content'][:30]}... | Summarized: {result.get('summarized', False)}")
    
    print(f"   Memory stats: {smart_memory.get_stats()}")
    
    # Demo 2: Web App Integration  
    print("\n2. Web App Integration Demo...")
    session_data = {'session_id': 'web_demo'}
    upgraded_session = WebAppMemoryIntegration.upgrade_session(session_data, client)
    print(f"   Session upgraded: {upgraded_session.get('memory_type')}")
    
    print("\n✅ Integration demos completed successfully!")
