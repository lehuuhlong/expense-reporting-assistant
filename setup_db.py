from database import ExpenseDB
from functions import EXPENSE_POLICIES, EXPENSE_CATEGORIES, MOCK_EXPENSE_REPORTS, SAMPLE_USER_QUERIES, GENERAL_FAQS, COMPANY_KNOWLEDGE_BASE

def check_database_health():
    """Kiểm tra tình trạng database"""
    print("🏥 Checking database health...")
    
    try:
        db = ExpenseDB()
        
        # Test each collection
        test_queries = [
            ("policies", "chính sách"),
            ("faqs", "FAQ"),
            ("knowledge_base", "kiến thức")
        ]
        
        healthy = 0
        
        for collection_type, description in test_queries:
            try:
                if collection_type == "policies":
                    result = db.search_policies("test", limit=1)
                elif collection_type == "faqs":
                    result = db.search_faqs("test", limit=1)
                elif collection_type == "knowledge_base":
                    result = db.search_knowledge_base("test", limit=1)
                
                print(f"✅ {description}: OK")
                healthy += 1
                
            except Exception as e:
                print(f"❌ {description}: ERROR - {e}")
        
        return healthy == len(test_queries)
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def setup_database():
    """Initialize and populate the ChromaDB database"""
    print("🔧 Setting up database...")
    
    try:
        db = ExpenseDB()
        
        # Clear existing data
        print("🧹 Clearing existing data...")
        db.clear_all()
        
        # Re-initialize db to recreate collections after clearing
        db = ExpenseDB()
        
        # Add existing data
        print("📝 Adding data to collections...")
        db.add_policies(EXPENSE_POLICIES)
        db.add_categories(EXPENSE_CATEGORIES)
        db.add_expense_reports(MOCK_EXPENSE_REPORTS)
        db.add_sample_questions(SAMPLE_USER_QUERIES)
        
        # Add new enhanced data
        db.add_faqs(GENERAL_FAQS)
        db.add_knowledge_base(COMPANY_KNOWLEDGE_BASE)
        
        print("✅ Database setup complete!")
        print(f"Added:")
        print(f"- {len(EXPENSE_POLICIES)} policy categories")
        print(f"- {len(EXPENSE_CATEGORIES)} expense categories")
        print(f"- {len(MOCK_EXPENSE_REPORTS)} sample reports")
        print(f"- {len(SAMPLE_USER_QUERIES)} sample questions")
        print(f"- {len(GENERAL_FAQS)} FAQs")
        print(f"- {len(COMPANY_KNOWLEDGE_BASE)} knowledge base items")
        
        # Verify setup
        print("\n🔍 Verifying database health...")
        is_healthy = check_database_health()
        
        if is_healthy:
            print("🎉 Database is ready for use!")
            return True
        else:
            print("⚠️ Database setup completed but some issues detected")
            return False
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

if __name__ == "__main__":
    print("🩺 DATABASE SETUP & HEALTH CHECK")
    print("=" * 40)
    
    success = setup_database()
    
    if success:
        print("\n✅ All done! Database is ready for use.")
        exit(0)
    else:
        print("\n❌ Setup completed with issues. Please check the logs.")
        exit(1)