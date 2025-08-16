import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import json
import os
import time
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ExpenseDB:
    def __init__(self):
        # Initialize ChromaDB client - sử dụng path nhất quán
        self.client = chromadb.PersistentClient(path="./data/chromadb")
        
        # Use ChromaDB's default embedding function (no API key needed)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Initialize collections
        self.expense_policies = self.client.get_or_create_collection(
            name="expense_policies",
            embedding_function=self.embedding_fn,
            metadata={"description": "Company expense policies"}
        )
        
        self.expense_categories = self.client.get_or_create_collection(
            name="expense_categories",
            embedding_function=self.embedding_fn,
            metadata={"description": "Expense categories and limits"}
        )
        
        self.expense_reports = self.client.get_or_create_collection(
            name="expense_reports",
            embedding_function=self.embedding_fn,
            metadata={"description": "Sample expense reports"}
        )

        # New collections for enhanced chatbot capabilities
        self.faqs = self.client.get_or_create_collection(
            name="expense_faq",  # Consistent với populate script
            embedding_function=self.embedding_fn,
            metadata={"description": "General FAQs and common questions"}
        )
        
        self.knowledge_base = self.client.get_or_create_collection(
            name="company_knowledge",
            embedding_function=self.embedding_fn,
            metadata={"description": "Company policies and knowledge base"}
        )
        
        # 🧠 Conversation summaries collection
        self.conversation_summaries = self.client.get_or_create_collection(
            name="conversation_summaries",
            embedding_function=self.embedding_fn,
            metadata={"description": "Summarized conversation segments"}
        )
        
        # 💡 Expense examples collection  
        self.expense_examples = self.client.get_or_create_collection(
            name="expense_examples",
            embedding_function=self.embedding_fn,
            metadata={"description": "Sample expense examples and outcomes"}
        )  
        self.expense_examples = self.client.get_or_create_collection(
            name="expense_examples",
            embedding_function=self.embedding_fn,
            metadata={"description": "Real expense examples for training"}
        )
    
    def add_policies(self, policies: Dict[str, List[str]]):
        """Add policies to the database"""
        for category, rules in policies.items():
            for idx, rule in enumerate(rules):
                self.expense_policies.add(
                    documents=[rule],
                    ids=[f"{category}_{idx}"],
                    metadatas=[{"category": category}]
                )
    
    def add_categories(self, categories: Dict[str, Dict[str, Any]]):
        """Add expense categories to the database"""
        for category, details in categories.items():
            self.expense_categories.add(
                documents=[json.dumps(details)],
                ids=[category],
                metadatas=[{"category": category}]
            )
    
    def add_expense_reports(self, reports: List[Dict[str, Any]]):
        """Add expense reports to the database"""
        for idx, report in enumerate(reports):
            self.expense_reports.add(
                documents=[json.dumps(report)],
                ids=[f"report_{idx}"],
                metadatas=[{"employee_id": report.get("employee_id")}]
            )
    
    def search_policies(self, query: str, limit: int = 5) -> List[str]:
        """Search policies based on query"""
        try:
            results = self.expense_policies.query(
                query_texts=[query],
                n_results=limit
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            print(f"Error searching policies: {e}")
            return []
    
    def get_category_limits(self, category: str) -> Dict[str, Any]:
        """Get category limits and rules"""
        result = self.expense_categories.get(
            ids=[category]
        )
        if result['documents']:
            return json.loads(result['documents'][0])
        return {}
    
    def get_sample_reports(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample expense reports"""
        results = self.expense_reports.query(
            query_texts=[""],
            n_results=limit
        )
        return [json.loads(doc) for doc in results['documents'][0]]

    def clear_all(self):
        """Clear all collections"""
        collections_to_clear = [
            "expense_policies", "expense_categories", "expense_reports", 
            "sample_questions", "general_faqs", "company_knowledge"
        ]
        for collection_name in collections_to_clear:
            try:
                self.client.delete_collection(collection_name)
            except Exception as e:
                print(f"Warning: Could not delete collection {collection_name}: {e}")

    def add_sample_questions(self, questions: list):
        """Add sample user queries to the database"""
        collection = self.client.get_or_create_collection(
            name="sample_questions",
            embedding_function=self.embedding_fn,
            metadata={"description": "Sample user queries"}
        )
        for idx, q in enumerate(questions):
            collection.add(
                documents=[q],
                ids=[f"question_{idx}"],
                metadatas=[{"type": "sample_question"}]
            )
    
    def add_faqs(self, faqs: List[Dict[str, Any]]):
        """Add FAQs to the database"""
        for idx, faq in enumerate(faqs):
            # Store both question and answer as searchable content
            content = f"Q: {faq['question']} A: {faq['answer']}"
            self.faqs.add(
                documents=[content],
                ids=[f"faq_{idx}"],
                metadatas={
                    "question": faq["question"],
                    "answer": faq["answer"],
                    "category": faq["category"],
                    "keywords": ",".join(faq["keywords"])
                }
            )
    
    def add_knowledge_base(self, knowledge_items: List[Dict[str, Any]]):
        """Add knowledge base items to the database"""
        for idx, item in enumerate(knowledge_items):
            content = f"{item['topic']}: {item['content']}"
            self.knowledge_base.add(
                documents=[content],
                ids=[f"kb_{idx}"],
                metadatas={
                    "topic": item["topic"],
                    "content": item["content"],
                    "category": item["category"],
                    "keywords": ",".join(item["keywords"])
                }
            )
    
    def search_faqs(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search FAQs based on query"""
        try:
            results = self.faqs.query(
                query_texts=[query],
                n_results=limit
            )
            
            faqs = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    faqs.append({
                        "question": metadata.get("question", ""),
                        "answer": metadata.get("answer", ""),
                        "category": metadata.get("category", ""),
                        "relevance_score": results['distances'][0][i] if results.get('distances') else 0
                    })
            return faqs
        except Exception as e:
            print(f"Error searching FAQs: {e}")
            return []
    
    def search_knowledge_base(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search knowledge base based on query"""
        try:
            results = self.knowledge_base.query(
                query_texts=[query],
                n_results=limit
            )
            
            knowledge_items = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    knowledge_items.append({
                        "topic": metadata.get("topic", ""),
                        "content": metadata.get("content", ""),
                        "category": metadata.get("category", ""),
                        "relevance_score": results['distances'][0][i] if results.get('distances') else 0
                    })
            return knowledge_items
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            return []
    
    def add_conversation_summary(self, user_id: str, conversation_id: str, 
                                  summary: str, metadata: Dict = None) -> str:
        """Add conversation summary to database"""
        try:
            doc_id = f"{user_id}_{conversation_id}_{int(time.time())}"
            full_metadata = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "type": "conversation_summary"
            }
            if metadata:
                full_metadata.update(metadata)
            
            self.conversation_summaries.add(
                documents=[summary],
                metadatas=[full_metadata],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            print(f"Error adding conversation summary: {e}")
            return ""

    def get_conversation_summaries(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation summaries for a user"""
        try:
            results = self.conversation_summaries.query(
                query_texts=[f"user summaries for {user_id}"],
                where={"user_id": user_id},
                n_results=limit
            )
            
            summaries = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    summaries.append({
                        "summary": doc,
                        "conversation_id": metadata.get("conversation_id", ""),
                        "timestamp": metadata.get("timestamp", ""),
                        "metadata": metadata
                    })
            return summaries
        except Exception as e:
            print(f"Error getting conversation summaries: {e}")
            return []

    def add_expense_example(self, example_id: str, description: str, amount: float,
                           category: str, status: str, reason: str, documents: list) -> str:
        """Add expense example to database"""
        try:
            content = f"{description} - {status}: {reason}"
            metadata = {
                "example_id": example_id,
                "description": description,
                "amount": amount,
                "category": category,
                "status": status,
                "reason": reason,
                "documents": ",".join(documents),
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            self.expense_examples.add(
                documents=[content],
                metadatas=[metadata],
                ids=[example_id]
            )
            return example_id
        except Exception as e:
            print(f"Error adding expense example: {e}")
            return ""

    def add_knowledge_item(self, topic: str, content: str, category: str, tags: list) -> str:
        """Add knowledge base item"""
        try:
            full_content = f"{topic}: {content}"
            metadata = {
                "topic": topic,
                "content": content,
                "category": category,
                "tags": ",".join(tags),
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            doc_id = f"kb_{topic.replace(' ', '_')}_{int(time.time())}"
            self.knowledge_base.add(
                documents=[full_content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            print(f"Error adding knowledge item: {e}")
            return ""

    def comprehensive_search(self, query: str, limit_per_source: int = 2) -> Dict[str, Any]:
        """Search across all collections for comprehensive results"""
        try:
            return {
                "policies": self.search_policies(query, limit_per_source),
                "faqs": self.search_faqs(query, limit_per_source),
                "knowledge_base": self.search_knowledge_base(query, limit_per_source),
                "query": query
            }
        except Exception as e:
            print(f"Error in comprehensive search: {e}")
            return {
                "policies": [],
                "faqs": [],
                "knowledge_base": [],
                "query": query,
                "error": str(e)
            }
    
    def system_health_check(self) -> Dict[str, Any]:
        """
        🏥 Comprehensive system health check
        
        Returns:
            Dictionary with system health status and metrics
        """
        health_status = {
            "timestamp": datetime.datetime.now().isoformat(),
            "database_connection": False,
            "collections": {},
            "total_documents": 0,
            "performance_metrics": {},
            "issues": [],
            "recommendations": [],
            "overall_status": "unknown"
        }
        
        try:
            # Test database connection
            health_status["database_connection"] = True
            
            # Check each collection
            collections = [
                ("expense_policies", self.expense_policies, "Company expense policies"),
                ("expense_categories", self.expense_categories, "Expense categories and limits"),
                ("knowledge_base", self.knowledge_base, "Conversational knowledge"),
                ("expense_examples", self.expense_examples, "Sample expense cases"),
                ("conversation_summaries", self.conversation_summaries, "User conversation history")
            ]
            
            total_docs = 0
            for name, collection, description in collections:
                try:
                    count = collection.count()
                    total_docs += count
                    
                    # Test search performance
                    start_time = time.time()
                    test_result = collection.query(query_texts=["test"], n_results=1)
                    search_time = (time.time() - start_time) * 1000
                    
                    health_status["collections"][name] = {
                        "document_count": count,
                        "description": description,
                        "search_time_ms": round(search_time, 2),
                        "status": "healthy" if count > 0 else "empty"
                    }
                    
                    # Add recommendations for empty collections
                    if count == 0:
                        health_status["recommendations"].append(
                            f"📈 {name}: Consider adding documents to improve RAG effectiveness"
                        )
                    
                except Exception as e:
                    health_status["collections"][name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_status["issues"].append(f"❌ {name}: {str(e)}")
            
            health_status["total_documents"] = total_docs
            
            # Performance recommendations
            if total_docs < 50:
                health_status["recommendations"].append(
                    "📊 Consider expanding knowledge base to 50+ documents for better RAG performance"
                )
            
            # Overall status assessment
            error_count = len(health_status["issues"])
            if error_count == 0 and total_docs > 30:
                health_status["overall_status"] = "excellent"
            elif error_count == 0 and total_docs > 10:
                health_status["overall_status"] = "good"
            elif error_count < 2:
                health_status["overall_status"] = "fair"
            else:
                health_status["overall_status"] = "poor"
                
        except Exception as e:
            health_status["overall_status"] = "error"
            health_status["issues"].append(f"❌ Database connection error: {str(e)}")
        
        return health_status
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        📊 Get comprehensive system statistics
        
        Returns:
            Dictionary with system statistics and metrics
        """
        stats = {
            "database_path": "./data/chromadb",
            "collections": {},
            "total_documents": 0,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "created_at": datetime.datetime.now().isoformat()
        }
        
        try:
            collections = [
                ("expense_policies", self.expense_policies),
                ("expense_categories", self.expense_categories),
                ("knowledge_base", self.knowledge_base),
                ("expense_examples", self.expense_examples),
                ("conversation_summaries", self.conversation_summaries)
            ]
            
            for name, collection in collections:
                try:
                    count = collection.count()
                    stats["collections"][name] = count
                    stats["total_documents"] += count
                except Exception as e:
                    stats["collections"][name] = f"Error: {str(e)}"
                    
        except Exception as e:
            stats["error"] = str(e)
            
        return stats