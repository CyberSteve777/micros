from uuid import UUID
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from ..models.notification import Notification as NotificationModel
from ..schemas.notification import Notification as NotificationSchema


class NotificationRepo:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def create_notification(self, notification: NotificationModel) -> NotificationModel:
        db_notification = NotificationSchema(**notification.model_dump())
        self.db.add(db_notification)
        self.db.commit()
        self.db.refresh(db_notification)
        return NotificationModel.model_validate(db_notification)

    def get_notification_by_id(self, notification_id: UUID) -> NotificationModel:
        notification = self.db.query(NotificationSchema).filter(
            NotificationSchema.notification_id == notification_id
        ).first()
        if not notification:
            raise KeyError(f"Notification with id={notification_id} not found")
        return NotificationModel.model_validate(notification)

    def get_user_notifications(self, user_id: UUID, page: int, page_size: int):
        query = self.db.query(NotificationSchema).filter(
            NotificationSchema.user_id == user_id
        ).order_by(desc(NotificationSchema.sent_at))

        total_items = query.count()
        total_pages = (total_items + page_size - 1) // page_size
        notifications = query.offset((page - 1) * page_size).limit(page_size).all()

        return [NotificationModel.model_validate(n) for n in notifications], total_items, total_pages

    def mark_as_read(self, notification_id: UUID) -> NotificationModel:
        notification = self.db.query(NotificationSchema).filter(
            NotificationSchema.notification_id == notification_id
        ).first()
        if not notification:
            raise KeyError(f"Notification with id={notification_id} not found")

        notification.status = "read"
        self.db.commit()
        self.db.refresh(notification)
        return NotificationModel.model_validate(notification)
