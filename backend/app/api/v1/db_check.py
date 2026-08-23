import sqlite3

from fastapi import APIRouter, HTTPException

from app.api.models import DbCheckResponse
from app.db.connection import get_connection

router = APIRouter()


@router.get("/db-check", response_model=DbCheckResponse)
def check_db() -> DbCheckResponse:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT vec_version();")
        row = cursor.fetchone()
        if not row or not row[0]:
            raise HTTPException(
                status_code=500, detail="Failed to retrieve sqlite-vec version"
            )
        return DbCheckResponse(sqlite_vec_version=str(row[0]))
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=500, detail="Database error during extension check"
        ) from exc
    finally:
        conn.close()
