#!/usr/bin/env python3
"""
🔧 IMPROVED FALLBACK RAG SYSTEM
===============================

Enhanced fallback RAG implementation when LangChain is unavailable.
Provides basic but functional RAG capabilities using ChromaDB directly.

Author: AI Expert Fix
Date: August 16, 2025
"""

import json
import time
from typing import List, Dict, Any, Optional
from database import ExpenseDB
import openai
from openai import OpenAI

class FallbackRAGSystem:
    """
    🛡️ Improved fallback RAG system using ChromaDB directly
    
    Features:
    - Multi-collection semantic search
    - Context ranking and relevance scoring
    - Query expansion for better retrieval
    - Response generation with retrieved context
    """
    
    def __init__(self, openai_client: Optional[OpenAI] = None):
        """Initialize fallback RAG system"""
        self.db = ExpenseDB()
        self.client = openai_client
        
        # RAG configuration
        self.max_context_length = 4000
        self.retrieval_limit = 5
        self.relevance_threshold = 0.7
        
        print("🛡️ Fallback RAG System initialized")
    
    def search_comprehensive(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Enhanced comprehensive search across all collections
        """
        start_time = time.time()
        
        # Search across all collections
        results = {
            "policies": self._search_with_scoring(
                self.db.expense_policies, query, limit
            ),
            "categories": self._search_with_scoring(
                self.db.expense_categories, query, limit
            ),
            "knowledge_base": self._search_with_scoring(
                self.db.knowledge_base, query, limit
            ),
            "examples": self._search_with_scoring(
                self.db.expense_examples, query, limit
            ),
            "query": query,
            "search_time": time.time() - start_time
        }
        
        # Add relevance scoring
        results["total_results"] = sum(
            len(items) for key, items in results.items() 
            if isinstance(items, list)
        )
        
        return results
    
    def _search_with_scoring(self, collection, query: str, limit: int) -> List[Dict]:
        """Enhanced search with relevance scoring"""
        try:
            # Primary search
            results = collection.query(
                query_texts=[query],
                n_results=limit
            )
            
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results.get('distances') else 1.0
                    
                    # Convert distance to relevance score (lower distance = higher relevance)
                    relevance_score = max(0, 1.0 - distance)
                    
                    # Only include results above threshold
                    if relevance_score >= self.relevance_threshold:
                        result = {
                            "content": doc,
                            "metadata": metadata,
                            "relevance_score": relevance_score,
                            "source": collection.name
                        }
                        
                        # Add specific fields based on collection
                        if collection.name == "expense_policies":
                            result["policy_id"] = metadata.get("policy_id", "")
                            result["category"] = metadata.get("category", "")
                        elif collection.name == "expense_categories":
                            result["category_id"] = metadata.get("category_id", "")
                            result["limit_amount"] = metadata.get("limit_amount", 0)
                        elif collection.name == "expense_examples":
                            result["status"] = metadata.get("status", "")
                            result["amount"] = metadata.get("amount", 0)
                        
                        formatted_results.append(result)
            
            # Sort by relevance score
            formatted_results.sort(key=lambda x: x["relevance_score"], reverse=True)
            return formatted_results
            
        except Exception as e:
            print(f"Search error in {collection.name}: {e}")
            return []
    
    def generate_rag_response(self, query: str, context_limit: int = 3) -> Dict[str, Any]:
        """
        Generate response using retrieved context
        """
        if not self.client:
            return {
                "response": "OpenAI client not available for response generation",
                "context_used": [],
                "error": "No OpenAI client"
            }
        
        # Retrieve relevant context
        search_results = self.search_comprehensive(query, context_limit)
        
        # Build context from top results
        context_parts = []
        context_used = []
        
        for collection_name, results in search_results.items():
            if isinstance(results, list) and results:
                for result in results[:2]:  # Top 2 from each collection
                    context_parts.append(f"[{collection_name}] {result['content']}")
                    context_used.append({
                        "source": collection_name,
                        "content": result['content'][:200] + "...",
                        "relevance": result['relevance_score']
                    })
        
        # Prepare prompt
        context_text = "\n".join(context_parts[:5])  # Limit context
        
        system_prompt = """Bạn là Trợ lý AI chuyên về kê khai chi phí công ty. 
Sử dụng thông tin từ knowledge base để trả lời chính xác và hữu ích.
Nếu không có thông tin liên quan, hãy nói rõ và đưa ra gợi ý chung."""
        
        user_prompt = f"""
Context từ knowledge base:
{context_text}

Câu hỏi: {query}

Hãy trả lời dựa trên context trên, nếu có. Trả lời bằng tiếng Việt.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return {
                "response": response.choices[0].message.content,
                "context_used": context_used,
                "search_results": search_results,
                "success": True
            }
            
        except Exception as e:
            return {
                "response": f"Lỗi khi tạo phản hồi: {str(e)}",
                "context_used": context_used,
                "search_results": search_results,
                "error": str(e),
                "success": False
            }
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand query with related terms for better retrieval
        """
        # Vietnamese expense-related synonyms and expansions
        expansion_map = {
            "ăn": ["ăn uống", "bữa ăn", "meal", "food"],
            "uống": ["ăn uống", "đồ uống", "beverage"],
            "taxi": ["grab", "di chuyển", "đi lại", "transport"],
            "hotel": ["khách sạn", "lưu trú", "accommodation"],
            "hóa đơn": ["receipt", "bill", "invoice", "VAT"],
            "kê khai": ["declare", "báo cáo", "report"],
            "chính sách": ["policy", "quy định", "rule"]
        }
        
        expanded_queries = [query]
        
        # Add related terms
        for term, synonyms in expansion_map.items():
            if term in query.lower():
                for synonym in synonyms:
                    if synonym not in query:
                        expanded_queries.append(query + " " + synonym)
        
        return expanded_queries[:3]  # Limit to 3 variations
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health and performance"""
        
        print("🏥 Running fallback RAG health check...")
        
        health_status = {
            "database_connection": False,
            "collections_accessible": [],
            "sample_search_performance": {},
            "openai_client": bool(self.client),
            "overall_status": "unknown"
        }
        
        # Test database connection
        try:
            collections = [
                self.db.expense_policies,
                self.db.expense_categories, 
                self.db.knowledge_base,
                self.db.expense_examples
            ]
            
            health_status["database_connection"] = True
            
            # Test each collection
            for collection in collections:
                try:
                    count = collection.count()
                    health_status["collections_accessible"].append({
                        "name": collection.name,
                        "document_count": count,
                        "status": "healthy"
                    })
                except Exception as e:
                    health_status["collections_accessible"].append({
                        "name": collection.name,
                        "status": "error",
                        "error": str(e)
                    })
            
            # Test search performance
            test_queries = ["chi phí ăn uống", "taxi", "hóa đơn"]
            for query in test_queries:
                start_time = time.time()
                results = self.search_comprehensive(query, limit=3)
                search_time = time.time() - start_time
                
                health_status["sample_search_performance"][query] = {
                    "response_time_ms": round(search_time * 1000, 2),
                    "results_found": results["total_results"]
                }
            
            # Overall status
            if (health_status["database_connection"] and 
                len(health_status["collections_accessible"]) > 0):
                health_status["overall_status"] = "healthy"
            else:
                health_status["overall_status"] = "degraded"
                
        except Exception as e:
            health_status["overall_status"] = "error"
            health_status["error"] = str(e)
        
        return health_status


def test_fallback_rag():
    """Test the fallback RAG system"""
    
    print("🧪 TESTING FALLBACK RAG SYSTEM")
    print("=" * 50)
    
    # Initialize system
    try:
        from openai import OpenAI
        import os
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "test-key"))
        rag = FallbackRAGSystem(client)
    except:
        rag = FallbackRAGSystem()
        print("⚠️ OpenAI client not available, testing search only")
    
    # Health check
    health = rag.health_check()
    print(f"\n🏥 Health Status: {health['overall_status']}")
    
    # Test search
    test_queries = [
        "chính sách ăn uống",
        "giới hạn chi phí taxi",
        "cách kê khai hóa đơn"
    ]
    
    print("\n🔍 SEARCH TESTS:")
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = rag.search_comprehensive(query, limit=2)
        
        for collection, items in results.items():
            if isinstance(items, list) and items:
                print(f"  📊 {collection}: {len(items)} results")
                if items:
                    print(f"      Top result: {items[0]['content'][:100]}...")
    
    # Test RAG response if OpenAI available
    if rag.client:
        print("\n🤖 RAG RESPONSE TEST:")
        try:
            response = rag.generate_rag_response("Tôi muốn biết về chính sách ăn uống")
            print(f"Response: {response['response'][:200]}...")
            print(f"Context sources: {len(response['context_used'])}")
        except Exception as e:
            print(f"Response generation error: {e}")
    
    print("\n✅ Fallback RAG test completed")


if __name__ == "__main__":
    test_fallback_rag()
