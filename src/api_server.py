#!/usr/bin/env python3
"""
PDF Translation API Server
FastAPI server for German to English PDF translation service
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
import tempfile
import logging
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from pdf_translator import PDFTranslator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF Translation Service",
    description="German to English PDF translation with layout preservation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CONFIG = {
    "model_path": os.getenv("MODEL_PATH", "./models/Helsinki-NLP/opus-mt-de-en"),
    "upload_path": Path(os.getenv("UPLOAD_PATH", "./uploads")),
    "output_path": Path(os.getenv("OUTPUT_PATH", "./outputs")),
    "temp_path": Path(os.getenv("TEMP_PATH", "./temp")),
    "max_file_size": int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024,  # 50MB
    "cleanup_interval": int(os.getenv("CLEANUP_INTERVAL", "3600")),  # 1 hour
}

# Create directories
for path in [CONFIG["upload_path"], CONFIG["output_path"], CONFIG["temp_path"]]:
    path.mkdir(exist_ok=True)

# Global translator instance
translator = None
translation_tasks = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the translation model on startup."""
    global translator
    try:
        logger.info("Initializing PDF translator...")
        translator = PDFTranslator(CONFIG["model_path"])
        translator.force_offline = True  # Use offline mode
        await asyncio.get_event_loop().run_in_executor(None, translator.load_model)
        logger.info("PDF translator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize translator: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down PDF translation service...")
    # Cleanup any ongoing tasks
    for task_id in list(translation_tasks.keys()):
        if not translation_tasks[task_id].get("completed", False):
            logger.info(f"Cancelling incomplete task: {task_id}")

async def cleanup_old_files():
    """Background task to cleanup old files."""
    try:
        current_time = datetime.now()
        for directory in [CONFIG["upload_path"], CONFIG["output_path"], CONFIG["temp_path"]]:
            for file_path in directory.glob("*"):
                if file_path.is_file():
                    file_age = current_time - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age.total_seconds() > CONFIG["cleanup_interval"]:
                        file_path.unlink()
                        logger.info(f"Cleaned up old file: {file_path}")
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")

def perform_translation(task_id: str, input_path: str, output_path: str, 
                       preserve_formatting: bool = True, batch_size: int = 16):
    """Perform PDF translation in background."""
    try:
        logger.info(f"Starting translation task {task_id}")
        translation_tasks[task_id]["status"] = "processing"
        translation_tasks[task_id]["progress"] = 0
        
        # Perform translation
        success = translator.translate_pdf(
            input_path,
            output_path,
            batch_size=batch_size,
            preserve_formatting=preserve_formatting
        )
        
        if success:
            translation_tasks[task_id]["status"] = "completed"
            translation_tasks[task_id]["progress"] = 100
            translation_tasks[task_id]["output_file"] = output_path
            logger.info(f"Translation task {task_id} completed successfully")
        else:
            translation_tasks[task_id]["status"] = "failed"
            translation_tasks[task_id]["error"] = "Translation failed"
            logger.error(f"Translation task {task_id} failed")
            
    except Exception as e:
        logger.error(f"Translation task {task_id} error: {e}")
        translation_tasks[task_id]["status"] = "failed"
        translation_tasks[task_id]["error"] = str(e)

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "PDF Translation API",
        "version": "1.0.0",
        "status": "running",
        "model": CONFIG["model_path"],
        "endpoints": {
            "health": "/health",
            "translate": "/translate",
            "status": "/status/{task_id}",
            "download": "/download/{task_id}",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes."""
    global translator
    if translator is None or translator.model is None:
        raise HTTPException(status_code=503, detail="Translation model not loaded")
    
    return {
        "status": "healthy",
        "model_loaded": translator.model is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/translate")
async def translate_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    preserve_formatting: bool = True,
    batch_size: int = 16
):
    """Upload and translate a German PDF to English."""
    
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Check file size
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > CONFIG["max_file_size"]:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size: {CONFIG['max_file_size'] // (1024*1024)}MB"
        )
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Save uploaded file
    input_filename = f"{task_id}_input.pdf"
    output_filename = f"{task_id}_output.pdf"
    input_path = CONFIG["upload_path"] / input_filename
    output_path = CONFIG["output_path"] / output_filename
    
    with open(input_path, "wb") as buffer:
        buffer.write(content)
    
    # Initialize task tracking
    translation_tasks[task_id] = {
        "status": "queued",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "input_file": str(input_path),
        "output_file": str(output_path),
        "original_filename": file.filename,
        "preserve_formatting": preserve_formatting,
        "batch_size": batch_size
    }
    
    # Start background translation
    background_tasks.add_task(
        perform_translation,
        task_id,
        str(input_path),
        str(output_path),
        preserve_formatting,
        batch_size
    )
    
    # Schedule cleanup
    background_tasks.add_task(cleanup_old_files)
    
    return {
        "task_id": task_id,
        "status": "queued",
        "message": "Translation started. Use /status/{task_id} to check progress.",
        "status_url": f"/status/{task_id}",
        "download_url": f"/download/{task_id}"
    }

@app.get("/status/{task_id}")
async def get_translation_status(task_id: str):
    """Get the status of a translation task."""
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = translation_tasks[task_id]
    response = {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "created_at": task["created_at"]
    }
    
    if task["status"] == "failed":
        response["error"] = task.get("error", "Unknown error")
    elif task["status"] == "completed":
        response["download_url"] = f"/download/{task_id}"
    
    return response

@app.get("/download/{task_id}")
async def download_translated_pdf(task_id: str):
    """Download the translated PDF file."""
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = translation_tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Translation not completed")
    
    output_path = Path(task["output_file"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Translated file not found")
    
    # Generate download filename
    original_name = task["original_filename"]
    download_name = f"translated_{original_name}"
    
    return FileResponse(
        path=str(output_path),
        filename=download_name,
        media_type="application/pdf"
    )

@app.get("/tasks")
async def list_tasks():
    """List all translation tasks (for debugging)."""
    return {
        "active_tasks": len(translation_tasks),
        "tasks": {
            task_id: {
                "status": task["status"],
                "created_at": task["created_at"],
                "progress": task["progress"]
            }
            for task_id, task in translation_tasks.items()
        }
    }

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a translation task and its files."""
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = translation_tasks[task_id]
    
    # Clean up files
    for file_path_str in [task.get("input_file"), task.get("output_file")]:
        if file_path_str:
            file_path = Path(file_path_str)
            if file_path.exists():
                file_path.unlink()
    
    # Remove task
    del translation_tasks[task_id]
    
    return {"message": f"Task {task_id} deleted successfully"}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF Translation API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
        reload=False
    )