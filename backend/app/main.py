from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uuid
import os
from .search import perform_google_maps_search, setup_selenium_driver
from typing import Dict, List, Any, Optional

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for tasks
tasks = {}

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.post("/api/search")
async def start_search(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    keyword: str = Form(...),
    location: str = Form(...)
):
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Save file temporarily
    file_path = f"/tmp/{task_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Read CSV file to validate
    try:
        df = pd.read_csv(file_path)
        if 'postal_code' not in df.columns:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail="CSV file must contain a 'postal_code' column")
        postal_codes = df['postal_code'].astype(str).tolist()
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Error processing CSV file: {str(e)}")
    
    # Initialize task
    tasks[task_id] = {
        "status": "in_progress",
        "progress": 0,
        "results": [],
        "total_postal_codes": len(postal_codes),
        "processed_postal_codes": 0,
        "file_path": file_path,
        "driver": None,
        "cancelled": False
    }
    
    # Start background task
    background_tasks.add_task(
        process_search,
        task_id,
        postal_codes,
        keyword,
        location
    )
    
    return {"task_id": task_id, "message": "Search started"}

async def process_search(task_id: str, postal_codes: List[str], keyword: str, location: str):
    # Setup Selenium driver
    driver = setup_selenium_driver()
    tasks[task_id]["driver"] = driver
    
    all_results = []
    total = len(postal_codes)
    
    try:
        for index, postal_code in enumerate(postal_codes):
            # Check if task was cancelled
            if tasks[task_id]["cancelled"]:
                break
            
            search_query = f"{keyword} in {postal_code}, {location}"
            results = perform_google_maps_search(driver, search_query, postal_code)
            all_results.extend(results)
            
            # Update progress
            processed = index + 1
            progress = int((processed / total) * 100)
            tasks[task_id]["progress"] = progress
            tasks[task_id]["processed_postal_codes"] = processed
            tasks[task_id]["results"] = all_results
        
        # Complete task
        if not tasks[task_id]["cancelled"]:
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        print(f"Error processing search: {str(e)}")
    finally:
        # Clean up
        if driver:
            driver.quit()
        
        # Remove temporary file
        if os.path.exists(tasks[task_id]["file_path"]):
            os.remove(tasks[task_id]["file_path"])

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    return {
        "status": task["status"],
        "progress": task["progress"],
        "results": task["results"],
        "total": task["total_postal_codes"],
        "processed": task["processed_postal_codes"]
    }

@app.delete("/api/cancel/{task_id}")
async def cancel_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tasks[task_id]["cancelled"] = True
    
    # Close browser if it's open
    if tasks[task_id]["driver"]:
        try:
            tasks[task_id]["driver"].quit()
        except:
            pass
    
    tasks[task_id]["status"] = "cancelled"
    
    return {"message": "Task cancelled successfully"}