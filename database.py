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
        results = self.policies.query(
            query_texts=[query],
            n_results=limit
        )
        return results['documents'][0] if results['documents'] else []
    
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
        self.client.delete_collection("expense_policies")
        self.client.delete_collection("expense_categories")
        self.client.delete_collection("expense_reports")

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