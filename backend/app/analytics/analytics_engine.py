import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import OccupancyLog, ParkingSession, EventLog

class AnalyticsService:
    @staticmethod
    async def get_live_metrics(db: AsyncSession, camera_id: int) -> dict:
        """
        Returns latest count metric.
        """
        stmt = select(OccupancyLog).where(OccupancyLog.camera_id == camera_id).order_by(OccupancyLog.timestamp.desc()).limit(1)
        result = await db.execute(stmt)
        latest_log = result.scalar_one_or_none()
        
        if latest_log:
            return {
                "total_capacity": latest_log.total_capacity,
                "occupied": latest_log.occupied_spots,
                "available": latest_log.available_spots,
                "utilization": (latest_log.occupied_spots / max(1, latest_log.total_capacity)) * 100
            }
        return {"total_capacity": 10, "occupied": 0, "available": 10, "utilization": 0.0}

    @staticmethod
    async def get_historical_trends(db: AsyncSession, camera_id: int, hours: int = 24) -> list:
        """
        Returns occupancy logs aggregated hourly for the last N hours.
        """
        since_time = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        stmt = (
            select(
                func.strftime('%Y-%m-%d %H:00:00', OccupancyLog.timestamp).label("hour"),
                func.avg(OccupancyLog.occupied_spots).label("avg_occupied"),
                func.avg(OccupancyLog.available_spots).label("avg_available")
            )
            .where(and_(OccupancyLog.camera_id == camera_id, OccupancyLog.timestamp >= since_time))
            .group_by("hour")
            .order_by("hour")
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        return [
            {
                "time": row.hour,
                "occupied": round(float(row.avg_occupied), 1),
                "available": round(float(row.avg_available), 1)
            }
            for row in rows
        ]

    @staticmethod
    async def get_peak_hours(db: AsyncSession, camera_id: int) -> list:
        """
        Identifies hours of the day with the highest average occupancy.
        """
        stmt = (
            select(
                func.strftime('%H', OccupancyLog.timestamp).label("hour_of_day"),
                func.avg(OccupancyLog.occupied_spots).label("avg_occupied")
            )
            .where(OccupancyLog.camera_id == camera_id)
            .group_by("hour_of_day")
            .order_by(func.avg(OccupancyLog.occupied_spots).desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        return [
            {"hour": int(row.hour_of_day), "avg_occupied": round(float(row.avg_occupied), 1)}
            for row in rows
        ]

    @staticmethod
    async def get_average_duration(db: AsyncSession, camera_id: int) -> float:
        """
        Calculates average parking duration in minutes.
        """
        stmt = select(func.avg(ParkingSession.duration_seconds)).where(
            and_(ParkingSession.camera_id == camera_id, ParkingSession.duration_seconds.is_not(None))
        )
        result = await db.execute(stmt)
        avg_seconds = result.scalar()
        
        return round(float(avg_seconds) / 60.0, 1) if avg_seconds else 0.0

    @staticmethod
    async def get_spatial_heatmap(db: AsyncSession, camera_id: int) -> list:
        """
        Calculates how many times each spot has been occupied.
        Returns: List of occupancy counts per spot_id.
        """
        stmt = (
            select(
                ParkingSession.spot_id,
                func.count(ParkingSession.id).label("occupancy_count")
            )
            .where(ParkingSession.camera_id == camera_id)
            .group_by(ParkingSession.spot_id)
        )
        result = await db.execute(stmt)
        rows = result.all()
        
        return [{"spot_id": row.spot_id, "count": int(row.occupancy_count)} for row in rows]
