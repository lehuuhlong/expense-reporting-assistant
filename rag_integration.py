#!/usr/bin/env python3
"""
🔗 RAG Integration Module - Workshop 4

Kết nối RAG system với web application để có thể sử dụng 
retrieval-augmented generation trong chatbot interface.

Author: Workshop 4 Team
Date: August 2025
"""

import json
from typing import Dict, Any, Optional
from rag_system import get_rag_system, ExpenseRAGSystem

class RAGIntegration:
    """
    🤖 RAG Integration class để kết nối với web app
    
    Provides:
    - Easy integration với existing web app
    - Fallback mechanism nếu RAG system fail
    - Response formatting cho web interface
    """
    
    def __init__(self):
        """Initialize RAG integration"""
        self.rag_system: Optional[ExpenseRAGSystem] = None
        self._initialize_rag()
    
    def _initialize_rag(self):
        """Initialize RAG system với error handling"""
        try:
            print("🔄 Initializing RAG system for web integration...")
            self.rag_system = get_rag_system()
            print("✅ RAG system initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
            print("⚠️  Will use fallback mode without RAG")
            self.rag_system = None
    
    def is_rag_available(self) -> bool:
        """Check if RAG system is available"""
        return self.rag_system is not None
    
    def get_rag_response(self, user_input: str, use_hybrid: bool = True) -> Dict[str, Any]:
        """
        Get response from RAG system
        
        Args:
            user_input: User's question/query
            use_hybrid: Whether to use hybrid response (RAG + Function calling)
            
        Returns:
            Response dictionary compatible với web app
        """
        if not self.is_rag_available():
            return {
                "content": "RAG system không khả dụng. Vui lòng sử dụng chế độ thường.",
                "rag_used": False,
                "error": "RAG system not available"
            }
        
        try:
            if use_hybrid:
                # Sử dụng hybrid response (recommended)
                rag_result = self.rag_system.get_hybrid_response(user_input)
            else:
                # Chỉ sử dụng RAG retrieval
                rag_result = self.rag_system.get_rag_response(user_input)
            
            # Format response cho web app
            response = {
                "content": rag_result.get("answer", "Không tìm thấy câu trả lời phù hợp."),
                "rag_used": True,
                "response_type": rag_result.get("type", "unknown"),
                "function_calling_used": rag_result.get("function_calling_used", False)
            }
            
            # Add source documents nếu có
            if "rag_context" in rag_result:
                response["sources"] = rag_result["rag_context"]
            elif "source_documents" in rag_result.get("rag_result", {}):
                response["sources"] = rag_result["rag_result"]["source_documents"]
            
            # Add function call results nếu có
            if "agent_result" in rag_result:
                agent_result = rag_result["agent_result"]
                if "intermediate_steps" in agent_result:
                    response["function_calls"] = agent_result["intermediate_steps"]
            
            return response
            
        except Exception as e:
            print(f"❌ RAG response error: {e}")
            return {
                "content": f"Lỗi khi xử lý với RAG system: {str(e)}",
                "rag_used": False,
                "error": str(e)
            }
    
    def search_knowledge_base(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search knowledge base using vector similarity
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Search results
        """
        if not self.is_rag_available():
            return {
                "results": [],
                "total": 0,
                "error": "RAG system not available"
            }
        
        try:
            # Search similar documents
            docs = self.rag_system.search_similar_documents(query, k=limit)
            
            return {
                "results": docs,
                "total": len(docs),
                "query": query
            }
            
        except Exception as e:
            print(f"❌ Knowledge base search error: {e}")
            return {
                "results": [],
                "total": 0,
                "error": str(e)
            }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        if not self.is_rag_available():
            return {
                "status": "unavailable",
                "error": "RAG system not initialized"
            }
        
        try:
            stats = self.rag_system.get_statistics()
            stats["status"] = "operational"
            return stats
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

# Global RAG integration instance
rag_integration = None

def get_rag_integration() -> RAGIntegration:
    """Get or create RAG integration instance"""
    global rag_integration
    if rag_integration is None:
        rag_integration = RAGIntegration()
    return rag_integration

def is_rag_query(user_input: str) -> bool:
    """
    Determine if query should use RAG system
    
    Args:
        user_input: User's input
        
    Returns:
        True if should use RAG, False for normal processing
    """
    # Keywords indicating RAG should be used
    rag_keywords = [
        # Policy related
        "chính sách", "policy", "quy định", "quy trình", "hướng dẫn",
        
        # Knowledge base
        "thông tin", "information", "giải thích", "explain", "hỏi", "ask",
        
        # Complex queries
        "tính toán", "calculate", "validation", "kiểm tra", "check",
        
        # Search terms
        "tìm", "search", "tra cứu", "lookup", "find",
        
        # FAQ related
        "làm thế nào", "how to", "có thể", "can I", "được không"
    ]
    
    return any(keyword in user_input.lower() for keyword in rag_keywords)

# Export functions for easy import
__all__ = [
    'RAGIntegration',
    'get_rag_integration', 
    'is_rag_query'
]
