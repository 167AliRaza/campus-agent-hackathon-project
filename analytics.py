from fastapi import APIRouter, HTTPException
from db_config.database import get_db_client
from typing import Dict, Any, List

# Create a FastAPI router instance
analytics_router = APIRouter()

# Database setup
try:
    db_client = get_db_client()
    if db_client is None:
        raise Exception("Failed to connect to the database.")
    db = db_client["smit_students_db"]
    if db is None:
        raise Exception("Failed to access the database 'smit_students_db'.")
except Exception as e:
    db = None
    print(f"Database connection error: {e}")

# Refactored functions to return data structures (dicts, lists)

def get_total_students_data() -> Dict[str, Any]:
    """
    Refactored to return the total count of students as a dictionary.
    """
    if db is None:
        return {"error": "Database connection not available."}
    try:
        total_count = db.students.count_documents({})
        return {"total_students": total_count}
    except Exception as e:
        return {"error": f"Error counting students: {str(e)}"}

def get_students_by_department_data() -> Dict[str, Any]:
    """
    Refactored to return department-wise student counts as a dictionary.
    """
    if db is None:
        return {"error": "Database connection not available."}
    try:
        pipeline = [
            {"$group": {
                "_id": "$department",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        result = list(db.students.aggregate(pipeline))
        
        if not result:
            return {"students_by_department": {}, "message": "No students found in any department."}
            
        department_counts = {item['_id']: item['count'] for item in result}
        return {"students_by_department": department_counts}
    except Exception as e:
        return {"error": f"Error getting students by department: {str(e)}"}

def get_recent_onboarded_students_data(limit: int = 5) -> Dict[str, Any]:
    """
    Refactored to return a list of recent students as a dictionary.
    """
    if db is None:
        return {"error": "Database connection not available."}
    try:
        sample_doc = db.students.find_one()
        if not sample_doc:
            return {"recent_students": [], "message": "No students found in the database."}
        
        timestamp_fields = ['created_at', 'onboarded_at', 'date_added', 'registration_date']
        available_field = next((field for field in timestamp_fields if field in sample_doc), None)
        
        sort_key = available_field if available_field else "_id"
        
        recent_students = list(
            db.students.find({}, {"_id": 0})
            .sort(sort_key, -1)
            .limit(limit)
        )
        
        if not recent_students:
            return {"recent_students": [], "message": "No recent students found."}
        
        return {"recent_students": recent_students}
        
    except Exception as e:
        return {"error": f"Error getting recent students: {str(e)}"}

# FastAPI endpoint to combine and return all statistics
@analytics_router.get("/student-statistics", response_model=Dict[str, Any])
def get_student_statistics():
    """
    Endpoint to retrieve and combine various student statistics into a single JSON response.
    """
    if db is None:
        raise HTTPException(status_code=503, detail="Database connection failed.")
    
    # Get data from each refactored function
    total_students = get_total_students_data()
    students_by_dept = get_students_by_department_data()
    recent_students = get_recent_onboarded_students_data()
    
    # Combine the results into a single dictionary
    combined_statistics = {
        "summary": total_students,
        "department_statistics": students_by_dept,
        "recent_students": recent_students
    }
    
    return combined_statistics