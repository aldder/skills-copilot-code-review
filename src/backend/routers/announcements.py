"""
Endpoints for managing announcements in the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime
from bson.objectid import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements(include_expired: bool = Query(False)) -> List[Dict[str, Any]]:
    """
    Get all announcements
    
    - include_expired: If False (default), only returns active announcements
    """
    announcements = []
    now = datetime.now().isoformat()
    
    for announcement in announcements_collection.find():
        # Convert ObjectId to string for JSON serialization
        announcement["_id"] = str(announcement["_id"])
        
        # Check if announcement is active
        if not include_expired:
            start_date = announcement.get("start_date")
            end_date = announcement.get("end_date")
            
            # Skip if start_date is in the future
            if start_date and start_date > now:
                continue
            
            # Skip if end_date has passed
            if end_date and end_date < now:
                continue
        
        announcements.append(announcement)
    
    return announcements


@router.get("/{announcement_id}", response_model=Dict[str, Any])
def get_announcement(announcement_id: str) -> Dict[str, Any]:
    """Get a specific announcement by ID"""
    try:
        announcement = announcements_collection.find_one(
            {"_id": ObjectId(announcement_id)}
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    announcement["_id"] = str(announcement["_id"])
    return announcement


@router.post("", response_model=Dict[str, Any])
def create_announcement(
    title: str,
    message: str,
    end_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Create a new announcement
    
    - Requires teacher/admin authentication
    - title: Announcement title
    - message: Announcement message/content
    - start_date: Optional start date (ISO format). If not provided, announcement is active immediately
    - end_date: Required end date (ISO format)
    - teacher_username: Username of authenticated teacher
    """
    # Check authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required to create announcements"
        )
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")
    
    # Validate dates
    try:
        if start_date:
            datetime.fromisoformat(start_date)
        datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)"
        )
    
    # Create announcement
    announcement = {
        "title": title,
        "message": message,
        "start_date": start_date,
        "end_date": end_date,
        "created_by": teacher_username,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.insert_one(announcement)
    
    announcement["_id"] = str(result.inserted_id)
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    title: Optional[str] = None,
    message: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Update an existing announcement
    
    - Requires teacher/admin authentication
    - Only the fields provided will be updated
    """
    # Check authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required to update announcements"
        )
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")
    
    # Verify announcement exists
    try:
        announcement = announcements_collection.find_one(
            {"_id": ObjectId(announcement_id)}
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Build update document with only provided fields
    update_data = {"updated_at": datetime.now().isoformat()}
    
    if title is not None:
        update_data["title"] = title
    if message is not None:
        update_data["message"] = message
    if start_date is not None:
        try:
            datetime.fromisoformat(start_date)
            update_data["start_date"] = start_date
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    if end_date is not None:
        try:
            datetime.fromisoformat(end_date)
            update_data["end_date"] = end_date
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid end_date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    # Update announcement
    result = announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update announcement")
    
    # Return updated announcement
    updated_announcement = announcements_collection.find_one(
        {"_id": ObjectId(announcement_id)}
    )
    updated_announcement["_id"] = str(updated_announcement["_id"])
    return updated_announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """
    Delete an announcement
    
    - Requires teacher/admin authentication
    """
    # Check authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required to delete announcements"
        )
    
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")
    
    # Verify announcement exists and delete
    try:
        result = announcements_collection.delete_one(
            {"_id": ObjectId(announcement_id)}
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
