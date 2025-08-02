from database import ExpenseDB
from functions import EXPENSE_POLICIES, EXPENSE_CATEGORIES, MOCK_EXPENSE_REPORTS, SAMPLE_USER_QUERIES

def setup_database():
    """Initialize and populate the ChromaDB database"""
    db = ExpenseDB()
    
    # Clear existing data
    db.clear_all()
    
    # Re-initialize db to recreate collections after clearing
    db = ExpenseDB()
    
    # Add policies
    db.add_policies(EXPENSE_POLICIES)
    
    # Add categories
    db.add_categories(EXPENSE_CATEGORIES)
    
    # Add sample reports
    db.add_expense_reports(MOCK_EXPENSE_REPORTS)
    
    # Add sample user queries
    db.add_sample_questions(SAMPLE_USER_QUERIES)
    
    print("✅ Database setup complete!")
    print(f"Added:")
    print(f"- {len(EXPENSE_POLICIES)} policy categories")
    print(f"- {len(EXPENSE_CATEGORIES)} expense categories")
    print(f"- {len(MOCK_EXPENSE_REPORTS)} sample reports")

if __name__ == "__main__":
    setup_database()