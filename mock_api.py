"""
Mock RentAHuman API Server
Provides realistic bounty data for testing the Discord bot
NO API KEY REQUIRED - Run locally or deploy
"""

from fastapi import FastAPI, Query, Header
from fastapi.responses import JSONResponse
from typing import Optional
import random
from datetime import datetime, timedelta
import uvicorn

app = FastAPI(title="Mock RentAHuman API", version="1.0.0")

# Sample bounty data
LOCATIONS = [
    "Remote", "San Francisco, CA", "New York, NY", "Austin, TX",
    "Seattle, WA", "London, UK", "Berlin, Germany", "Tokyo, Japan",
    "Singapore", "Toronto, Canada", "Sydney, Australia", "Paris, France"
]

TITLES = [
    "Build a Discord Bot for Trading Alerts",
    "Create AI-Powered Resume Parser",
    "Develop Chrome Extension for Productivity",
    "Design Landing Page for SaaS Product",
    "Write Technical Documentation for API",
    "Build Stripe Payment Integration",
    "Create Automated Testing Suite",
    "Develop Mobile App Prototype",
    "Build Real-Time Analytics Dashboard",
    "Create Web Scraper for Job Postings",
    "Develop API Integration with Slack",
    "Build Authentication System with OAuth",
    "Create Data Visualization Dashboard",
    "Develop Shopify Plugin for Inventory",
    "Build Telegram Bot for Notifications",
    "Create Email Marketing Automation",
    "Develop React Component Library",
    "Build Python CLI Tool for DevOps",
    "Create WordPress Plugin for SEO",
    "Develop FastAPI Backend Service"
]

DESCRIPTIONS = [
    "We need an experienced developer to build a production-ready solution. Must have strong communication skills and deliver clean, documented code.",
    "Looking for someone who can start immediately and work independently. Prior experience with similar projects required.",
    "Seeking a detail-oriented developer for this challenging project. Must be comfortable with modern development practices.",
    "This is a straightforward project for someone with the right skills. Quick turnaround expected.",
    "Great opportunity to work on an exciting project with potential for ongoing work. Portfolio review required.",
]

REWARDS = ["$500", "$750", "$1,000", "$1,500", "$2,000", "$2,500", "$3,000", "$5,000"]

# Store generated bounties to simulate persistence
bounties_cache = []
last_generated = None

def generate_bounties(count: int = 20) -> list:
    """Generate realistic bounty data"""
    global bounties_cache, last_generated
    
    # Regenerate every 5 minutes to simulate new bounties
    current_time = datetime.utcnow()
    if last_generated and (current_time - last_generated).seconds < 300 and bounties_cache:
        return bounties_cache
    
    bounties = []
    base_id = int(datetime.utcnow().timestamp())
    
    for i in range(count):
        bounty_id = base_id + i
        posted_at = datetime.utcnow() - timedelta(hours=random.randint(0, 48))
        deadline = datetime.utcnow() + timedelta(days=random.randint(3, 30))
        
        bounty = {
            "id": str(bounty_id),
            "title": random.choice(TITLES),
            "description": random.choice(DESCRIPTIONS),
            "location": random.choice(LOCATIONS),
            "reward": random.choice(REWARDS),
            "deadline": deadline.strftime("%Y-%m-%d"),
            "posted_at": posted_at.isoformat(),
            "url": f"https://rentahuman.ai/bounty/{bounty_id}",
            "status": "open",
            "skills": random.sample([
                "Python", "JavaScript", "React", "Node.js", "FastAPI",
                "PostgreSQL", "Docker", "AWS", "API Design", "UI/UX"
            ], k=random.randint(2, 4)),
            "applicants": random.randint(0, 15),
            "budget_type": random.choice(["fixed", "hourly"])
        }
        bounties.append(bounty)
    
    # Sort by posted_at descending (newest first)
    bounties.sort(key=lambda x: x["posted_at"], reverse=True)
    
    bounties_cache = bounties
    last_generated = current_time
    
    return bounties

@app.get("/")
def root():
    """API info endpoint"""
    return {
        "message": "Mock RentAHuman API",
        "version": "1.0.0",
        "endpoints": {
            "/bounties": "Get bounties (supports pagination)",
            "/health": "Health check"
        },
        "note": "This is a mock API for testing. No authentication required."
    }

@app.get("/bounties")
def get_bounties(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    location: Optional[str] = Query(None, description="Filter by location"),
    authorization: Optional[str] = Header(None)
):
    """
    Get bounties with pagination and optional filtering
    
    No authentication required for mock API
    Returns realistic bounty data
    """
    # Generate fresh bounties
    all_bounties = generate_bounties(50)
    
    # Filter by location if provided
    if location:
        all_bounties = [b for b in all_bounties if location.lower() in b["location"].lower()]
    
    # Pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_bounties = all_bounties[start_idx:end_idx]
    
    # Return with metadata
    return {
        "bounties": paginated_bounties,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": len(all_bounties),
            "total_pages": (len(all_bounties) + per_page - 1) // per_page
        },
        "filters": {
            "location": location
        }
    }

@app.get("/bounty/{bounty_id}")
def get_bounty(bounty_id: str):
    """Get single bounty by ID"""
    all_bounties = generate_bounties(50)
    
    for bounty in all_bounties:
        if bounty["id"] == bounty_id:
            return bounty
    
    return JSONResponse(
        status_code=404,
        content={"error": "Bounty not found"}
    )

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "bounties_cached": len(bounties_cache)
    }

if __name__ == "__main__":
    print("Starting Mock RentAHuman API Server")
    print("API will be available at: http://localhost:8000")
    print("Documentation at: http://localhost:8000/docs")
    print("Test endpoint: http://localhost:8000/bounties")
    print("\nPress Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)