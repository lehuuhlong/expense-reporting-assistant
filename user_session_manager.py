"""
🔐 User Session Manager with Smart Memory Integration
Quản lý phiên người dùng với tích hợp bộ nhớ thông minh

Features:
- Simple login (account only, no password)
- Dual storage: ChromaDB for logged-in users, memory for guests
- Smart conversation summarization for both storage types
- Session-based memory management
"""

import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import chromadb
from chromadb.config import Settings
import os
import logging

# Import our smart memory system
from conversation_summarizer import IntelligentConversationSummarizer
from smart_memory_integration import SmartConversationMemory

logger = logging.getLogger(__name__)

class UserSessionManager:
    """
    🔐 Quản lý phiên người dùng với bộ nhớ thông minh
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.sessions: Dict[str, Dict] = {}  # Guest sessions in memory
        self.logged_in_users: Dict[str, Dict] = {}  # Active logged-in users
        
        # Initialize ChromaDB for persistent storage
        os.makedirs(f"{data_dir}/user_conversations", exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(
            path=f"{data_dir}/user_conversations",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Smart memory components - Will be initialized when needed
        self.summarizer = None
        self._initialize_summarizer()
        
        # User conversation collections in ChromaDB
        self.user_collections: Dict[str, chromadb.Collection] = {}
        
        logger.info("🔐 User Session Manager initialized")
    
    def _initialize_summarizer(self):
        """Initialize summarizer with OpenAI client"""
        try:
            # Import here to avoid circular imports
            from expense_assistant import create_client
            client = create_client()
            self.summarizer = IntelligentConversationSummarizer(client)
            logger.info("✅ Smart summarizer initialized with OpenAI client")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize summarizer: {e}")
            self.summarizer = None
    
    def create_guest_session(self) -> str:
        """
        Tạo phiên khách (không đăng nhập)
        Returns session_id for guest user
        """
        session_id = f"guest_{uuid.uuid4().hex[:12]}"
        
        # Create smart memory for guest session
        smart_memory = None
        if self.summarizer:
            # SmartConversationMemory requires openai_client, not summarizer
            smart_memory = SmartConversationMemory(
                openai_client=self.summarizer.client,  # Use the client from summarizer
                session_id=session_id
            )
        
        self.sessions[session_id] = {
            'session_id': session_id,
            'user_type': 'guest',
            'account': None,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'smart_memory': smart_memory,
            'stats': {
                'messages_count': 0,
                'tokens_saved': 0,
                'summaries_created': 0
            }
        }
        
        logger.info(f"👤 Created guest session: {session_id}")
        return session_id
    
    def login_user(self, account: str) -> Tuple[str, Dict]:
        """
        Đăng nhập người dùng (chỉ cần account)
        Returns: (session_id, user_info)
        """
        if not account or not account.strip():
            raise ValueError("Account không được để trống")
        
        account = account.strip().lower()
        
        # Check if user already has an active session
        existing_session = self._find_user_session(account)
        if existing_session:
            existing_session['last_activity'] = datetime.now()
            logger.info(f"🔄 Reusing existing session for user: {account}")
            return existing_session['session_id'], existing_session
        
        # Create new session if none exists
        session_id = f"user_{account}_{uuid.uuid4().hex[:8]}"
        
        # Get or create ChromaDB collection for this user
        collection_name = f"user_{account.replace('@', '_').replace('.', '_')}"
        
        try:
            user_collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"📚 Loaded existing collection for user: {account}")
        except:
            user_collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"user_account": account, "created_at": datetime.now().isoformat()}
            )
            logger.info(f"🆕 Created new collection for user: {account}")
        
        self.user_collections[account] = user_collection
        
        # Create smart memory with ChromaDB storage
        smart_memory = None
        if self.summarizer:
            smart_memory = SmartConversationMemory(
                openai_client=self.summarizer.client,  # Use the client from summarizer
                session_id=session_id
            )
            
            # Load existing conversation history
            self._load_user_conversation_history(smart_memory, user_collection)
        
        user_info = {
            'session_id': session_id,
            'user_type': 'logged_in',
            'account': account,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'smart_memory': smart_memory,
            'collection_name': collection_name,
            'stats': {
                'messages_count': 0,
                'tokens_saved': 0,
                'summaries_created': 0,
                'total_conversations': user_collection.count()
            }
        }
        
        self.logged_in_users[session_id] = user_info
        
        logger.info(f"🔓 User logged in: {account} (session: {session_id})")
        return session_id, user_info
    
    def _find_user_session(self, account: str) -> Optional[Dict]:
        """
        Tìm session hiện tại của user
        """
        account = account.strip().lower()
        
        # Check in logged users (correct attribute name)
        for session_id, user_info in self.logged_in_users.items():
            if user_info.get('account') == account:
                return user_info
        
        return None
    
    def _load_user_conversation_history(self, smart_memory: SmartConversationMemory, collection: chromadb.Collection):
        """
        Tải lịch sử hội thoại của người dùng từ ChromaDB
        """
        try:
            # Get recent conversations (last 10 summaries)
            results = collection.query(
                query_texts=["conversation summary"],
                n_results=min(10, collection.count()),
                include=['documents', 'metadatas']
            )
            
            if results['documents'] and results['documents'][0]:
                summaries_loaded = 0
                for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                    if metadata and metadata.get('type') == 'summary':
                        # Add summary to smart memory
                        smart_memory.summaries.append({
                            'content': doc,
                            'timestamp': metadata.get('timestamp', datetime.now().isoformat()),
                            'tokens_saved': metadata.get('tokens_saved', 0),
                            'original_length': metadata.get('original_length', 0)
                        })
                        summaries_loaded += 1
                
                logger.info(f"📖 Loaded {summaries_loaded} conversation summaries from ChromaDB")
                
        except Exception as e:
            logger.error(f"❌ Error loading conversation history: {str(e)}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        Lấy thông tin phiên
        """
        # Check logged-in users first
        if session_id in self.logged_in_users:
            user_info = self.logged_in_users[session_id]
            user_info['last_activity'] = datetime.now()
            return user_info
        
        # Check guest sessions
        if session_id in self.sessions:
            session_info = self.sessions[session_id]
            session_info['last_activity'] = datetime.now()
            return session_info
        
        return None
    
    def get_smart_memory(self, session_id: str) -> Optional[SmartConversationMemory]:
        """
        Lấy smart memory cho phiên
        """
        session_info = self.get_session_info(session_id)
        if session_info:
            return session_info.get('smart_memory')
        return None
    
    def add_conversation_turn(self, session_id: str, user_message: str, assistant_message: str) -> Dict:
        """
        Thêm lượt hội thoại và cập nhật thống kê
        """
        session_info = self.get_session_info(session_id)
        if not session_info:
            raise ValueError(f"Session không tồn tại: {session_id}")
        
        smart_memory = session_info['smart_memory']
        result = {"tokens_saved": 0, "summaries_created": 0}
        
        # Add conversation turn if smart memory is available
        if smart_memory:
            result = smart_memory.add_conversation_turn(user_message, assistant_message)
        
        # Update session stats
        session_info['stats']['messages_count'] += 2
        if result.get('tokens_saved', 0) > 0:
            session_info['stats']['tokens_saved'] += result['tokens_saved']
            session_info['stats']['summaries_created'] += 1
        
        session_info['last_activity'] = datetime.now()
        
        return {
            'session_type': session_info['user_type'],
            'account': session_info.get('account'),
            'memory_stats': session_info['stats'],
            'optimization_result': result
        }
    
    def get_conversation_history(self, session_id: str, include_summaries: bool = True) -> List[Dict]:
        """
        Lấy lịch sử hội thoại (đã được summarize)
        """
        smart_memory = self.get_smart_memory(session_id)
        if smart_memory:
            return smart_memory.get_conversation_context(include_summaries=include_summaries)
        return []
    
    def optimize_session_memory(self, session_id: str) -> Dict:
        """
        Tối ưu bộ nhớ cho phiên cụ thể
        """
        smart_memory = self.get_smart_memory(session_id)
        if not smart_memory:
            return {"tokens_saved": 0, "error": "Smart memory không khả dụng"}
        
        result = smart_memory.force_summarization()
        
        # Update stats
        session_info = self.get_session_info(session_id)
        if session_info and result.get('tokens_saved', 0) > 0:
            session_info['stats']['tokens_saved'] += result['tokens_saved']
            session_info['stats']['summaries_created'] += 1
        
        return result
    
    def logout_user(self, session_id: str) -> bool:
        """
        Đăng xuất người dùng
        """
        if session_id in self.logged_in_users:
            user_info = self.logged_in_users[session_id]
            account = user_info.get('account')
            
            # Save final state to ChromaDB
            smart_memory = user_info['smart_memory']
            if hasattr(smart_memory, 'save_to_chromadb'):
                smart_memory.save_to_chromadb()
            
            del self.logged_in_users[session_id]
            logger.info(f"🔒 User logged out: {account}")
            return True
        
        return False
    
    def cleanup_guest_sessions(self, max_age_hours: int = 2):
        """
        Dọn dẹp phiên khách cũ
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        for session_id, session_info in self.sessions.items():
            if session_info['last_activity'] < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"🧹 Cleaned up expired guest session: {session_id}")
        
        return len(expired_sessions)
    
    def get_global_stats(self) -> Dict:
        """
        Lấy thống kê tổng quan
        """
        total_guests = len(self.sessions)
        total_logged_in = len(self.logged_in_users)
        
        total_tokens_saved = 0
        total_summaries = 0
        
        # Aggregate stats from all sessions
        for session_info in list(self.sessions.values()) + list(self.logged_in_users.values()):
            stats = session_info.get('stats', {})
            total_tokens_saved += stats.get('tokens_saved', 0)
            total_summaries += stats.get('summaries_created', 0)
        
        return {
            'total_sessions': total_guests + total_logged_in,
            'guest_sessions': total_guests,
            'logged_in_users': total_logged_in,
            'total_tokens_saved': total_tokens_saved,
            'total_summaries_created': total_summaries,
            'storage_breakdown': {
                'memory_sessions': total_guests,
                'chromadb_sessions': total_logged_in
            }
        }

# Global instance
session_manager = UserSessionManager()
