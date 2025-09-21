from fastapi import FastAPI
from openai import AsyncOpenAI #type: ignore
from openai import OpenAIError #type: ignore
from agents import Agent, OpenAIChatCompletionsModel,set_tracing_disabled, Runner ,function_tool ,TResponseInputItem #type: ignore
from dotenv import load_dotenv #type: ignore
from pydantic import BaseModel #type: ignore
from typing import Any, Dict, List, Optional
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from datetime import datetime
import uuid
import os
from pymongo import MongoClient # type: 
from db_config.database import get_db_client
set_tracing_disabled(True)

load_dotenv()
# def get_db_client():
#     try:
#         client = MongoClient(os.getenv("MONGODB_URI"))
#         print("Connected to the database successfully")
#         return client
#     except Exception as e:
#         print(f"Error connecting to the database: {e}")
#         return None
db_client = get_db_client()
if db_client is None:
    raise Exception("Failed to connect to the database.")
db = db_client["smit_students_db"]
if db is None:
    raise Exception("Failed to access the database 'smit_students_db'.")
class Message(BaseModel):
    message: str

    

# Ensure the API key is set
gemini_api_key = os.getenv('GEMINI_API_KEY')
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

@function_tool
async def cafeteria_timings() -> str:
    """
    Retrieves cafeteria operating hours.
    """
    try:
        # Simulate fetching cafeteria hours from a database or API
        details = "Cafeteria is open from 8 AM to 8 PM on weekdays and 9 AM to 5 PM on weekends."
        return details
    except Exception as e:
        print(f"Error retrieving cafeteria timings: {e}")
        return f"Error retrieving cafeteria timings: {e}"

@function_tool
async def library_hours() -> str:
    """
    Retrieves library operating hours.
    """
    try:
        # Simulate fetching library hours from a database or API
        details = "Library is open from 9 AM to 10 PM on weekdays and 10 AM to 6 PM on weekends."
        return details
    except Exception as e:
        print(f"Error retrieving library hours: {e}")
        return f"Error retrieving library hours: {e}"

@function_tool
async def general_info() -> str:
    """
    Retrieves general information about the campus.
    """
    try:
        # Simulate fetching general information from a database or API
        details = """Campus Name: Saylani Mass Traning Program --- 
        Departments: Faculty of Engineering & Technology: Computer Science,
        Software Engineering, Electrical Engineering, Mechanical Engineering,
        Civil Engineering. Faculty of Business & Management Sciences: 
        Accounting & Finance, Business Administration, Marketing, Human Resource Management
        . Faculty of Arts & Social Sciences: Psychology, Media & Communication Studies,
        Sociology, English Literature. Faculty of Health & Life Sciences: Pharmacy,
        Doctor of Physical Therapy (DPT), Biological Sciences. --- Class Timings: 
        Monday to Friday, with two sessions. Morning session: 9:00 AM to 1:00 PM.
        Afternoon session: 2:00 PM to 6:00 PM. Each class period is 1 hour and 30 minutes.
        --- Fee Details: Fees are on a per-semester basis. BS Computer Science: 
        Admission Fee: $500, Security Deposit: $200, Per Semester Fee: $2,500. BBA: 
        Admission Fee: $500, Security Deposit: $200, Per Semester Fee: $2,200.
        BA Psychology: Admission Fee: $400, Security Deposit: $150, Per Semester Fee
        : $1,800. DPT: Admission Fee: $600, Security Deposit: $250, Per Semester Fee:
        $3,000. Note: Fees are subject to a 10% annual increase. 
        Merit-based scholarships are available, offering 25% to 75% waivers on tuition fees
            """
        return details.strip()
    except Exception as e:
        print(f"Error retrieving general information: {e}")
        return f"Error retrieving general information: {e}"


faq_agent = Agent(
    name="Campus FAQ Agent",
    handoff_description="A helpful agent that can answer questions about the campus like library operating hours and cafeteria timings .",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a Campus FAQ agent with tools to:
get_cafeteria_timings(): Retrieves cafeteria operating hours.
Ex: "What are the cafeteria timings?"
get_library_hours(): Retrieves library operating hours.
Ex: "What are the library hours?
get_general_info(): Retrieves general information about the campus.
Ex: "Tell me about the campus facilities and departments.


""",
    model=OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=client),
    tools=[cafeteria_timings, library_hours, general_info],
)



class Student(BaseModel):
    name:str
    student_id:int
    department:str
    email:str


@function_tool
def add_student(student: Student) -> str:
    """
    Goal: Add student record to database
    input:  name:str, id:int, department:str, email:str
    Return: Success or error message

    """

    try:
        student_data = student.model_dump()
        student_data['onboarded_at'] = datetime.now()
        db.students.insert_one(student_data)
        return f"Student {student.name} added successfully."
    except Exception as e:
        print(f"Error adding student: {e}")
        return f"Error adding student: {e}"
    
@function_tool
def get_student_by_id(id: int) -> str:
    """
    Goal: Retrieve student record by ID
    input: id (int) - student ID to search for
    Return: Student data as string or error message
    """
    try:
        student = db.students.find_one({"student_id": id})
        if student:
            # Remove MongoDB's _id field for cleaner output
            if '_id' in student:
                del student['_id']
            return f"Student found: {student}"
        else:
            return f"No student found with ID: {id}"
    except Exception as e:
        print(f"Error retrieving student: {e}")
        return f"Error retrieving student: {e}"
    
class UpdateStudent(BaseModel):
    student_id: int
    field: str
    new_value: str
@function_tool
def update_student(student: UpdateStudent) -> str:
    """
    Goal: Update a specific field of a student record like name, email, department . if u
    input: 
    - id (int) of student whos record to update
    - field to update,
    - new_value (str) - new value for the field
    Return: Success or error message
    """
    try:
        # Check if student exists
        existing_student = db.students.find_one({"student_id": student.student_id})
        if not existing_student:
            return f"No student found with ID: {student.student_id}"
        
        # Validate field name
        valid_fields = ["name", "department", "email"]
        if student.field not in valid_fields:
            return f"Invalid field: {student.field}. Valid fields are: {', '.join(valid_fields)}"
        
        # Special handling for student_id updates
        if student.field == "student_id":
            return "Error: Cannot update student_id. This field is immutable."

        
        # Update the document
        result = db.students.update_one(
            {"student_id": student.student_id},
            {"$set": {student.field: student.new_value}}
        )
        
        if result.modified_count > 0:
            return f"Student ID {student.student_id}: {student.field} updated to '{student.new_value}' successfully."
        else:
            return f"No changes made to student ID {student.student_id}."

    except Exception as e:
        print(f"Error updating student: {e}")
        return f"Error updating student: {e}"

@function_tool
def delete_student(id: int) -> str:
    """
    Goal: Delete a student record by student ID
    input: id (int) - student ID to delete
    Return: Success or error message
    """
    try:
        # Check if student exists first
        existing_student = db.students.find_one({"student_id": id})
        if not existing_student:
            return f"No student found with ID: {id}"
        
        # Delete the student
        result = db.students.delete_one({"student_id": id})
        
        if result.deleted_count > 0:
            return f"Student with ID {id} deleted successfully."
        else:
            return f"Failed to delete student with ID {id}."
            
    except Exception as e:
        print(f"Error deleting student: {e}")
        return f"Error deleting student: {e}"
    
@function_tool
def list_students_json() -> List[Dict[str, Any]]:
    """
    Goal: List all student records as structured data
    input: None
    Return: List of student dictionaries or empty list
    """
    try:
        students = list(db.students.find({}, {"_id": 0}))
        return students
    except Exception as e:
        print(f"Error listing students: {e}")
        return []


student_management_agent = Agent(
    name="Student Management Agent",
    handoff_description="A helpful agent that can manage student records and assist with enrollment, updates, and inquiries.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a Student Management agent with access to a student database, capable of:
add_student(name, id, department, email): Adds a new student.
Ex: Add student records"John Doe, ID123, Math, john@example.com."
get_student(id): Retrieves student details by ID.
Ex: "Find student with ID123."
update_student(id, field, new_value): Updates a student's field (e.g., name, email).
Ex: "Update ID123's email to new@example.com."
delete_student(id): Deletes a student's record by ID.
Ex: "Remove student ID123."
list_students(): Lists all student records.
Ex: "Show all students.
if you don't have information or tools to answer user query then respond with 'I am unable to assist with that request.""",
   model=OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=client),
   tools=[add_student,get_student_by_id,update_student,delete_student,list_students_json],
   handoffs=[faq_agent],

)

     


triage_agent = Agent(
    name="Campus Supervisory Agent",
    handoff_description="A triage Campus Supervisory Agent that can delegate tasks  to the appropriate agent.",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX} 
You are a helpful Campus Supervisory Agent.
You task is to help user with their queries first check if user is asking from your context history if Yes then respond it yourself 
if No then delegate questions to other appropriate agents. If question is Student related, delegate to Student Management Agent,
 if question is Campus Analytics related, delegate to Campus Analytics Agent, if question is Campus FAQs related, delegate to Campus FAQs Agent.
   If you are unsure which agent to delegate to, respond it yourself. 
   If the question is not related to any of these topics, respond with 'I am unable to assist with that request."""
    ,
    model=OpenAIChatCompletionsModel(model="gemini-2.5-flash", openai_client=client),
    handoffs=[faq_agent, student_management_agent],
)
faq_agent.handoffs.append(triage_agent)

student_management_agent.handoffs.append(triage_agent)


history:list[TResponseInputItem]= []


