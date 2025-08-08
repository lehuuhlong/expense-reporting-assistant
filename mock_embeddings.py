#!/usr/bin/env python3
"""
🔧 Mock Embeddings for Workshop 4 Demo

Tạo mock embedding system khi OpenAI embeddings không khả dụng
để có thể demo RAG system functionality.

Author: Workshop 4 Team  
Date: August 2025
"""

import numpy as np
import json
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MockEmbeddings:
    """
    Mock embedding class sử dụng TF-IDF để simulate vector embeddings
    cho demo purposes khi OpenAI embeddings không available.
    """
    
    def __init__(self):
        """Initialize TF-IDF vectorizer"""
        self.vectorizer = TfidfVectorizer(
            max_features=384,  # Simulate embedding dimension
            stop_words=None,
            ngram_range=(1, 2),
            lowercase=True
        )
        self.is_fitted = False
        self.documents_cache = []
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed documents using TF-IDF
        
        Args:
            texts: List of text documents to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            # Add to cache for fitting
            self.documents_cache.extend(texts)
            
            # Fit vectorizer if not fitted or refit with new documents
            if not self.is_fitted or len(texts) > 100:
                print(f"🔧 Fitting TF-IDF vectorizer with {len(self.documents_cache)} documents...")
                self.vectorizer.fit(self.documents_cache)
                self.is_fitted = True
            
            # Transform texts to vectors
            vectors = self.vectorizer.transform(texts)
            
            # Convert to list of lists (dense format)
            embeddings = vectors.toarray().tolist()
            
            print(f"✅ Generated {len(embeddings)} mock embeddings (dim: {len(embeddings[0]) if embeddings else 0})")
            
            return embeddings
            
        except Exception as e:
            print(f"❌ Mock embedding error: {e}")
            # Return random embeddings as fallback
            return [[0.1] * 384 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        try:
            if not self.is_fitted:
                # Fit with cached documents if available
                if self.documents_cache:
                    self.vectorizer.fit(self.documents_cache)
                    self.is_fitted = True
                else:
                    # Fit with just the query text
                    self.vectorizer.fit([text])
                    self.is_fitted = True
            
            # Transform query to vector
            vector = self.vectorizer.transform([text])
            embedding = vector.toarray()[0].tolist()
            
            return embedding
            
        except Exception as e:
            print(f"❌ Mock query embedding error: {e}")
            # Return random embedding as fallback
            return [0.1] * 384

class MockFAISS:
    """
    Mock FAISS class để simulate vector store functionality
    khi FAISS hoặc embeddings không khả dụng.
    """
    
    def __init__(self, documents, embeddings):
        """
        Initialize mock FAISS store
        
        Args:
            documents: List of Document objects
            embeddings: Embedding model (unused in mock)
        """
        self.documents = documents
        self.embeddings = embeddings
        self.vectors = None
        self.texts = [doc.page_content for doc in documents]
        
        # Use mock embeddings if OpenAI fails
        try:
            # Try to generate embeddings
            if hasattr(embeddings, 'embed_documents'):
                self.vectors = embeddings.embed_documents(self.texts)
            else:
                raise Exception("No embed_documents method")
        except Exception as e:
            print(f"⚠️  Using mock embeddings due to: {e}")
            mock_embeddings = MockEmbeddings()
            self.vectors = mock_embeddings.embed_documents(self.texts)
            
        print(f"✅ Mock FAISS created with {len(self.documents)} documents")
    
    def similarity_search(self, query: str, k: int = 5):
        """
        Perform similarity search using cosine similarity
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of most similar documents
        """
        try:
            # Get query embedding using mock embeddings instead of OpenAI
            mock_embeddings = MockEmbeddings()
            mock_embeddings.documents_cache = self.texts
            query_vector = [mock_embeddings.embed_query(query)]
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_vector, self.vectors)[0]
            
            # Get top-k most similar documents
            top_indices = np.argsort(similarities)[::-1][:k]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0.01:  # Minimum similarity threshold
                    results.append(self.documents[idx])
            
            print(f"🔍 Found {len(results)} similar documents for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            print(f"❌ Mock search error: {e}")
            # Return first k documents as fallback
            return self.documents[:k]
    
    def as_retriever(self, search_type="similarity", search_kwargs=None):
        """Return a retriever interface"""
        if search_kwargs is None:
            search_kwargs = {"k": 5}
        
        class MockRetriever:
            def __init__(self, vector_store, k=5):
                self.vector_store = vector_store
                self.k = k
            
            def get_relevant_documents(self, query):
                return self.vector_store.similarity_search(query, k=self.k)
        
        k = search_kwargs.get("k", 5)
        return MockRetriever(self, k)
    
    def get_stats(self):
        """Get statistics about the vector store"""
        return {
            "total_documents": len(self.documents),
            "embedding_dimension": len(self.vectors[0]) if self.vectors and len(self.vectors) > 0 else 0,
            "has_vectors": self.vectors is not None
        }

def create_mock_vectorstore(documents, embeddings):
    """
    Create mock vector store khi FAISS.from_documents fails
    
    Args:
        documents: List of Document objects
        embeddings: Embedding model
        
    Returns:
        Mock vector store object
    """
    return MockFAISS(documents, embeddings)

# Export for easy import
__all__ = [
    'MockEmbeddings',
    'MockFAISS', 
    'create_mock_vectorstore'
]
