#!/usr/bin/env python3
"""
🚀 Workshop 5: RAG System với FAISS + Langchain + Function Calling

Expense Reporting Assistant RAG System
- FAISS vector store cho fast similarity search
- Langchain cho conversation management và retrieval chains
- OpenAI Function Calling để extend chatbot capabilities
- Mock data generation cho realistic scenarios

Author: Workshop 5 Team
Date: August 2025
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Langchain imports (updated structure)
from langchain_community.vectorstores import FAISS
try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_openai import ChatOpenAI
    from langchain.chains import ConversationalRetrievalChain
    from langchain.schema import HumanMessage, AIMessage, Document
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.memory import ConversationBufferWindowMemory
    from langchain.tools import Tool
    from langchain.agents import create_openai_functions_agent, AgentExecutor
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LangChain import error: {e}")
    print("📝 RAG system will use fallback mode without advanced features")
    LANGCHAIN_AVAILABLE = False

# OpenAI for function calling
from openai import OpenAI

# Local imports
from functions import (
    calculate_reimbursement,
    validate_expense, 
    search_policies,
    format_expense_summary,
    execute_function_call,
    EXPENSE_CATEGORIES,
    EXPENSE_POLICIES,
    GENERAL_FAQS,
    COMPANY_KNOWLEDGE_BASE
)

# Load environment variables
load_dotenv()

class ExpenseRAGSystem:
    """
    🧠 Workshop 5: Advanced RAG System for Expense Management
    
    Combines:
    - FAISS vector store for fast similarity search
    - Langchain for conversation management và retrieval chains  
    - OpenAI Function Calling để extend chatbot capabilities
    - Mock data generation for realistic scenarios
    """
    
    def __init__(self):
        """Initialize the RAG system với đầy đủ components theo workshop requirement"""
        print("🚀 Initializing Workshop 5 Expense RAG System...")
        
        if not LANGCHAIN_AVAILABLE:
            print("❌ LangChain not available - RAG system will be disabled")
            self.is_available = False
            return
        
        try:
            # Initialize OpenAI components - sử dụng config embedding riêng biệt
            self.embeddings = OpenAIEmbeddings(
                model=os.getenv("AZURE_OPENAI_EMBEDDING_MODEL"),
                openai_api_key=os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY"),
                openai_api_base=os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
            )
            
            self.llm = ChatOpenAI(
                model=os.getenv("AZURE_OPENAI_LLM_MODEL"),
                temperature=0.3,
                api_key=os.getenv("AZURE_OPENAI_LLM_API_KEY"),
                base_url=os.getenv("AZURE_OPENAI_LLM_ENDPOINT")
            )
            
            # Initialize OpenAI client for function calling
            self.openai_client = ChatOpenAI(
                api_key=os.getenv("AZURE_OPENAI_LLM_API_KEY"),
                base_url=os.getenv("AZURE_OPENAI_LLM_ENDPOINT")
            )
            
            # Initialize vector store
            self.vectorstore = None
            self.setup_vector_store()
            
            # Initialize conversation memory
            self.memory = ConversationBufferWindowMemory(
                memory_key="chat_history",
                return_messages=True,
                k=10  # Keep last 10 exchanges
            )
            
            # Setup RAG chain
            self.rag_chain = None
            self.setup_rag_chain()
            
            self.is_available = True
            print("✅ RAG System initialized successfully")
            
        except Exception as e:
            print(f"❌ Failed to initialize RAG system: {e}")
            self.is_available = False
        
        # Setup function calling tools
        self.tools = self.setup_tools()
        self.agent = self.setup_agent()
        
        print("✅ Workshop 5 RAG System initialized successfully!")
    
    def setup_vector_store(self):
        """Setup FAISS vector store with expense-related documents"""
        print("🔍 Setting up FAISS vector store...")
        
        # Prepare documents from existing data
        documents = []
        
        # Add policies
        for category, rules in EXPENSE_POLICIES.items():
            for rule in rules:
                doc = Document(
                    page_content=rule,
                    metadata={
                        "source": "policy",
                        "category": category,
                        "type": "expense_policy"
                    }
                )
                documents.append(doc)
        
        # Add FAQs
        for faq in GENERAL_FAQS:
            doc = Document(
                page_content=f"Q: {faq['question']}\nA: {faq['answer']}",
                metadata={
                    "source": "faq",
                    "category": faq['category'],
                    "type": "faq"
                }
            )
            documents.append(doc)
        
        # Add knowledge base
        for kb_item in COMPANY_KNOWLEDGE_BASE:
            doc = Document(
                page_content=f"{kb_item['topic']}: {kb_item['content']}",
                metadata={
                    "source": "knowledge_base",
                    "category": kb_item['category'],
                    "type": "knowledge"
                }
            )
            documents.append(doc)
        
        # Add expense categories info
        for category, details in EXPENSE_CATEGORIES.items():
            content = f"Category: {category}\n"
            content += f"Daily Limit: {details.get('daily_limit', 'N/A')}\n"
            content += f"Monthly Limit: {details.get('monthly_limit', 'N/A')}\n"
            content += f"Requires Receipt: {details.get('requires_receipt', False)}\n"
            content += f"Description: {details.get('description', '')}"
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": "category",
                    "category": category,
                    "type": "expense_category"
                }
            )
            documents.append(doc)
        
        # Create FAISS vector store with fallback to mock
        if documents:
            try:
                # Try to create FAISS vector store
                self.vectorstore = FAISS.from_documents(documents, self.embeddings)
                print(f"✅ FAISS vector store created with {len(documents)} documents")
            except Exception as e:
                print(f"⚠️  FAISS creation failed: {e}")
        else:
            print("❌ No documents found to create vector store")
    
    def setup_rag_chain(self):
        """Setup Conversational Retrieval Chain"""
        if not self.vectorstore:
            print("❌ Cannot setup RAG chain without vector store")
            return
        
        print("🔗 Setting up RAG chain...")
        
        try:
            # Create retriever
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}  # Top 5 similar documents
            )
            
            # Create conversational retrieval chain
            self.rag_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=self.memory,
                return_source_documents=True,
                verbose=False  # Set to False để giảm noise
            )
            
            print("✅ RAG chain setup complete")
            
        except Exception as e:
            print(f"⚠️  RAG chain setup failed: {e}")
            print("🔧 RAG chain will be disabled, using direct LLM instead")
            self.rag_chain = None
    
    def setup_tools(self) -> List[Tool]:
        """Setup function calling tools"""
        print("🛠️ Setting up function calling tools...")
        
        tools = [
            Tool(
                name="calculate_reimbursement",
                description="Calculate expense reimbursement based on list of expenses",
                func=self.calculate_reimbursement_wrapper
            ),
            Tool(
                name="validate_expense",
                description="Validate if an expense complies with company policies",
                func=self.validate_expense_wrapper
            ),
            Tool(
                name="search_policies",
                description="Search company policies by keyword or query",
                func=self.search_policies_wrapper
            ),
            Tool(
                name="check_expense_limits",
                description="Check daily/monthly limits for expense categories",
                func=self.check_limits_wrapper
            )
        ]
        
        print(f"✅ Setup {len(tools)} function calling tools")
        return tools
    
    def calculate_reimbursement_wrapper(self, query: str) -> str:
        """Wrapper for expense calculation function"""
        try:
            # Use existing function from functions.py
            from functions import calculate_reimbursement
            
            # Parse query to extract basic expense data
            import re
            
            # Extract amount
            amount_match = re.search(r'(\d+(?:\.\d+)?)', query)
            amount = float(amount_match.group(1)) if amount_match else 0
            
            # Extract category (simple keyword matching)
            category = "other"
            for cat in EXPENSE_CATEGORIES.keys():
                if cat.lower() in query.lower():
                    category = cat
                    break
            
            # Create simple expense object
            expenses = [{
                "amount": amount,
                "category": category,
                "description": query,
                "receipt_required": True,
                "date": datetime.now().strftime("%Y-%m-%d")
            }]
            
            result = calculate_reimbursement(expenses)
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            return f"Error calculating expense: {str(e)}"
    
    def validate_expense_wrapper(self, query: str) -> str:
        """Wrapper for expense validation function"""
        try:
            # Use existing function from functions.py
            from functions import validate_expense
            
            # Extract amount and category from query
            import re
            
            amount_match = re.search(r'(\d+(?:\.\d+)?)', query)
            amount = float(amount_match.group(1)) if amount_match else 0
            
            category = "other"
            for cat in EXPENSE_CATEGORIES.keys():
                if cat.lower() in query.lower():
                    category = cat
                    break
            
            # Create expense object
            expense = {
                "amount": amount,
                "category": category,
                "description": query,
                "receipt_required": True,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            
            result = validate_expense(expense)
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            return f"Error validating expense: {str(e)}"
    
    def search_policies_wrapper(self, query: str) -> str:
        """Wrapper for policy search function"""
        try:
            # Search through existing policies
            policies_found = []
            for category, rules in EXPENSE_POLICIES.items():
                for rule in rules:
                    if any(keyword.lower() in rule.lower() for keyword in query.split()):
                        policies_found.append({
                            "category": category,
                            "rule": rule
                        })
            
            return json.dumps({"policies": policies_found}, ensure_ascii=False)
            
        except Exception as e:
            return f"Error searching policies: {str(e)}"
    
    def check_limits_wrapper(self, query: str) -> str:
        """Check expense limits for categories"""
        try:
            limits_info = {}
            for category, details in EXPENSE_CATEGORIES.items():
                limits_info[category] = {
                    "daily_limit": details.get('daily_limit'),
                    "monthly_limit": details.get('monthly_limit'),
                    "requires_receipt": details.get('requires_receipt', False)
                }
            
            return json.dumps(limits_info, ensure_ascii=False)
            
        except Exception as e:
            return f"Error checking limits: {str(e)}"
    
    def setup_agent(self):
        """Setup Langchain agent with function calling"""
        print("🤖 Setting up intelligent agent...")
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Bạn là Trợ Lý Thông Minh Expense Management với khả năng RAG và Function Calling.

VAI TRÒ:
• 💰 Trợ lý báo cáo chi phí chuyên nghiệp
• 🔍 Tìm kiếm thông tin từ knowledge base với FAISS
• 🛠️ Thực hiện tính toán và validation thông qua function calling
• 📊 Cung cấp thông tin chính xác từ retrieval system

KHẢ NĂNG:
1. Retrieval: Tìm kiếm policies, FAQs, knowledge base
2. Generation: Tạo câu trả lời contextual và accurate
3. Function Calling: Tính toán, validation, search reports
4. Memory: Nhớ conversation context

TOOLS AVAILABLE:
- calculate_expense_reimbursement: Tính toán hoàn tiền
- validate_expense_policy: Kiểm tra tuân thủ policy
- search_expense_reports: Tìm kiếm báo cáo
- check_expense_limits: Kiểm tra giới hạn chi phí

Hãy sử dụng retrieval để tìm thông tin và function calling khi cần tính toán/validation.
Luôn thân thiện, chính xác và hữu ích! 😊"""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate"
        )
        
        print("✅ Agent setup complete")
        return agent_executor
    
    def get_rag_response(self, query: str) -> Dict[str, Any]:
        """Get response using RAG with knowledge base search"""
        try:
            if not self.vectorstore:
                return {"error": "Vector store not available"}
            
            # Search for relevant documents
            relevant_docs = self.vectorstore.similarity_search(query, k=3)
            
            if not relevant_docs:
                return {"error": "No relevant documents found"}
            
            # Create context from relevant documents
            context = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}"
                for doc in relevant_docs
            ])
            
            # Create RAG prompt
            rag_prompt = f"""Dựa vào thông tin sau đây, hãy trả lời câu hỏi một cách chính xác và hữu ích:

Context:
{context}

Câu hỏi: {query}

Trả lời (bằng tiếng Việt, ngắn gọn và dễ hiểu):"""
            
            # Get response from LLM
            response = self.llm.invoke(rag_prompt)
            
            answer = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "answer": answer,
                "source_documents": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    }
                    for doc in relevant_docs
                ],
                "type": "rag_response"
            }
                
        except Exception as e:
            return {"error": f"RAG response failed: {str(e)}"}
    
    def get_agent_response(self, query: str) -> Dict[str, Any]:
        """Get response using agent with function calling"""
        try:
            if not self.agent:
                return {"error": "Agent not initialized"}
            
            # Get agent response
            result = self.agent.invoke({"input": query})
            
            return {
                "answer": result["output"],
                "type": "agent_response",
                "intermediate_steps": result.get("intermediate_steps", [])
            }
            
        except Exception as e:
            return {"error": f"Agent response failed: {str(e)}"}
    
    def get_hybrid_response(self, query: str) -> Dict[str, Any]:
        """Get hybrid response combining RAG and Agent"""
        try:
            # Determine if query needs function calling
            function_keywords = [
                "tính toán", "calculate", "validation", "kiểm tra",
                "search", "tìm kiếm", "báo cáo", "report"
            ]
            
            needs_function_calling = any(
                keyword in query.lower() for keyword in function_keywords
            )
            
            if needs_function_calling:
                # Use agent for function calling
                agent_result = self.get_agent_response(query)
                
                # Also get RAG context for richer response
                rag_result = self.get_rag_response(query)
                
                return {
                    "answer": agent_result.get("answer", ""),
                    "type": "hybrid_response",
                    "agent_result": agent_result,
                    "rag_context": rag_result.get("source_documents", []),
                    "function_calling_used": True
                }
            else:
                # Use RAG for knowledge retrieval
                rag_result = self.get_rag_response(query)
                
                return {
                    "answer": rag_result.get("answer", ""),
                    "type": "hybrid_response",
                    "rag_result": rag_result,
                    "function_calling_used": False
                }
                
        except Exception as e:
            return {"error": f"Hybrid response failed: {str(e)}"}
    
    def search_similar_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents in vector store"""
        try:
            if not self.vectorstore:
                return []
            
            # Perform similarity search
            docs = self.vectorstore.similarity_search(query, k=k)
            
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": "N/A"  # FAISS doesn't return scores by default
                }
                for doc in docs
            ]
            
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []
    
    def add_documents(self, documents: List[Document]):
        """Add new documents to the vector store"""
        try:
            if self.vectorstore and documents:
                # Add documents to existing vector store
                texts = [doc.page_content for doc in documents]
                metadatas = [doc.metadata for doc in documents]
                
                self.vectorstore.add_texts(texts, metadatas=metadatas)
                print(f"✅ Added {len(documents)} new documents to vector store")
            
        except Exception as e:
            print(f"Error adding documents: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            stats = {
                "rag_enabled": self.vectorstore is not None,
                "vector_store_type": "FAISS" if hasattr(self.vectorstore, 'index') else "Mock",
                "tools_available": len(self.tools),
                "memory_messages": len(self.memory.chat_memory.messages) if self.memory else 0,
                "system_status": "operational"
            }
            
            # Add vector store stats if available
            if hasattr(self.vectorstore, 'get_stats'):
                vector_stats = self.vectorstore.get_stats()
                stats.update(vector_stats)
            elif hasattr(self.vectorstore, 'index'):
                stats["vector_store_documents"] = self.vectorstore.index.ntotal
            else:
                stats["vector_store_documents"] = len(getattr(self.vectorstore, 'documents', []))
                
            return stats
            
        except Exception as e:
            return {"error": f"Failed to get statistics: {str(e)}"}
    
    def is_rag_available(self) -> bool:
        """Check if RAG system is available and working"""
        return getattr(self, 'is_available', False)

# Singleton instance
rag_system = None

def get_rag_system() -> ExpenseRAGSystem:
    """Get or create RAG system instance"""
    global rag_system
    if rag_system is None:
        rag_system = ExpenseRAGSystem()
    return rag_system

if __name__ == "__main__":
    # Test the RAG system
    print("🧪 Testing Expense RAG System")
    print("=" * 50)
    
    # Initialize system
    system = get_rag_system()
    
    # Test queries
    test_queries = [
        "Chính sách chi phí ăn uống như thế nào?",
        "Tính toán hoàn tiền cho chi phí 500000 VND ăn uống",
        "Tôi có thể báo cáo chi phí nào?",
        "Giới hạn chi phí đi lại ra sao?"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        
        # Test RAG response
        rag_result = system.get_rag_response(query)
        print(f"📖 RAG: {rag_result.get('answer', 'N/A')[:100]}...")
        
        # Test hybrid response
        hybrid_result = system.get_hybrid_response(query)
        print(f"🤖 Hybrid: {hybrid_result.get('answer', 'N/A')[:100]}...")
        
        print("-" * 50)
    
    # Print statistics
    stats = system.get_statistics()
    print(f"\n📊 System Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
