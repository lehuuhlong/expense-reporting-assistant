import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ExpenseDB:
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./data/chromadb")
        
        # Use ChromaDB's default embedding function (no API key needed)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Initialize collections
        self.policies = self.client.get_or_create_collection(
            name="expense_policies",
            embedding_function=self.embedding_fn,
            metadata={"description": "Company expense policies"}
        )
        
        self.categories = self.client.get_or_create_collection(
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
            name="general_faqs",
            embedding_function=self.embedding_fn,
            metadata={"description": "General FAQs and common questions"}
        )
        
        self.knowledge_base = self.client.get_or_create_collection(
            name="company_knowledge",
            embedding_function=self.embedding_fn,
            metadata={"description": "Company policies and knowledge base"}
        )
    
    def add_policies(self, policies: Dict[str, List[str]]):
        """Add policies to the database"""
        for category, rules in policies.items():
            for idx, rule in enumerate(rules):
                self.policies.add(
                    documents=[rule],
                    ids=[f"{category}_{idx}"],
                    metadatas=[{"category": category}]
                )
    
    def add_categories(self, categories: Dict[str, Dict[str, Any]]):
        """Add expense categories to the database"""
        for category, details in categories.items():
            self.categories.add(
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
            results = self.policies.query(
                query_texts=[query],
                n_results=limit
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            print(f"Error searching policies: {e}")
            return []
    
    def get_category_limits(self, category: str) -> Dict[str, Any]:
        """Get category limits and rules"""
        result = self.categories.get(
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