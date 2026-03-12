"""
Alerts Service for StockPulse
Manages price alerts, checking conditions, and sending notifications
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.alert_models import (
    Alert, AlertCreate, AlertUpdate, AlertCondition, 
    AlertStatus, AlertPriority, AlertNotification, AlertSummary
)

logger = logging.getLogger(__name__)


class AlertsService:
    """Service for managing price alerts"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.alerts
        self._check_task: Optional[asyncio.Task] = None
        self._running = False
        self._notifications: List[AlertNotification] = []
        self._check_interval = 30  # seconds
    
    async def create_alert(self, alert_data: AlertCreate, stock_name: Optional[str] = None) -> Alert:
        """Create a new price alert"""
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"
        
        alert = Alert(
            id=alert_id,
            symbol=alert_data.symbol.upper(),
            stock_name=stock_name,
            condition=alert_data.condition,
            target_value=alert_data.target_value,
            comparison_value=alert_data.comparison_value,
            priority=alert_data.priority,
            message=alert_data.message,
            expires_at=alert_data.expires_at,
            repeat=alert_data.repeat,
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        
        doc = alert.model_dump()
        doc["created_at"] = doc["created_at"].isoformat() if doc.get("created_at") else None
        doc["expires_at"] = doc["expires_at"].isoformat() if doc.get("expires_at") else None
        
        await self.collection.insert_one(doc)
        logger.info(f"Created alert {alert_id} for {alert.symbol}")
        
        return alert
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get a specific alert by ID"""
        doc = await self.collection.find_one({"id": alert_id})
        if doc:
            doc.pop("_id", None)
            return Alert(**doc)
        return None
    
    async def get_all_alerts(
        self, 
        status: Optional[AlertStatus] = None,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get all alerts with optional filtering"""
        query = {}
        
        if status:
            query["status"] = status.value if isinstance(status, AlertStatus) else status
        if symbol:
            query["symbol"] = symbol.upper()
        
        cursor = self.collection.find(query, {"_id": 0}).limit(limit)
        alerts = []
        
        async for doc in cursor:
            try:
                alerts.append(Alert(**doc))
            except Exception as e:
                logger.error(f"Error parsing alert: {e}")
        
        return alerts
    
    async def update_alert(self, alert_id: str, updates: AlertUpdate) -> Optional[Alert]:
        """Update an existing alert"""
        update_data = updates.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await self.collection.update_one(
            {"id": alert_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await self.get_alert(alert_id)
        return None
    
    async def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert"""
        result = await self.collection.delete_one({"id": alert_id})
        return result.deleted_count > 0
    
    async def delete_all_alerts(self, symbol: Optional[str] = None) -> int:
        """Delete all alerts, optionally filtered by symbol"""
        query = {}
        if symbol:
            query["symbol"] = symbol.upper()
        
        result = await self.collection.delete_many(query)
        return result.deleted_count
    
    async def trigger_alert(
        self, 
        alert: Alert, 
        current_price: float
    ) -> AlertNotification:
        """Mark alert as triggered and create notification"""
        now = datetime.now(timezone.utc)
        
        # Generate notification message
        message = alert.message or self._generate_message(alert, current_price)
        
        notification = AlertNotification(
            alert_id=alert.id,
            symbol=alert.symbol,
            stock_name=alert.stock_name,
            condition=alert.condition,
            target_value=alert.target_value,
            current_price=current_price,
            message=message,
            priority=alert.priority,
            triggered_at=now,
        )
        
        # Update alert status
        update_data = {
            "triggered_at": now.isoformat(),
            "trigger_price": current_price,
            "trigger_count": alert.trigger_count + 1,
        }
        
        if not alert.repeat:
            update_data["status"] = AlertStatus.TRIGGERED.value
        
        await self.collection.update_one(
            {"id": alert.id},
            {"$set": update_data}
        )
        
        # Store notification in-memory (for backward compat)
        self._notifications.append(notification)

        # Persist notification to MongoDB
        notif_doc = {
            "alert_id": notification.alert_id,
            "symbol": notification.symbol,
            "stock_name": notification.stock_name,
            "condition": notification.condition.value if hasattr(notification.condition, 'value') else notification.condition,
            "target_value": notification.target_value,
            "current_price": notification.current_price,
            "message": notification.message,
            "priority": notification.priority.value if hasattr(notification.priority, 'value') else notification.priority,
            "triggered_at": now.isoformat(),
            "read": False,
        }
        try:
            await self.db.alert_notifications.insert_one(notif_doc)
        except Exception as e:
            logger.warning(f"Failed to persist notification to MongoDB: {e}")

        # Publish to Redis alert queue for real-time dispatch
        try:
            from services.cache_service import get_cache_service
            cache_svc = get_cache_service()
            if cache_svc:
                cache_svc.publish_alert({
                    "type": notification.condition.value if hasattr(notification.condition, 'value') else notification.condition,
                    "alert_id": notification.alert_id,
                    "symbol": notification.symbol,
                    "stock_name": notification.stock_name,
                    "target_value": notification.target_value,
                    "current_price": notification.current_price,
                    "message": notification.message,
                    "priority": notification.priority.value if hasattr(notification.priority, 'value') else notification.priority,
                    "triggered_at": now.isoformat(),
                })
        except Exception as e:
            logger.debug(f"Failed to publish alert to Redis queue: {e}")

        logger.info(f"Alert {alert.id} triggered at price {current_price}")
        
        return notification
    
    def _generate_message(self, alert: Alert, current_price: float) -> str:
        """Generate alert message based on condition"""
        stock = alert.stock_name or alert.symbol
        
        if alert.condition == AlertCondition.PRICE_ABOVE:
            return f"🔔 {stock} price is now ₹{current_price:.2f}, above your target of ₹{alert.target_value:.2f}"
        elif alert.condition == AlertCondition.PRICE_BELOW:
            return f"🔔 {stock} price is now ₹{current_price:.2f}, below your target of ₹{alert.target_value:.2f}"
        elif alert.condition == AlertCondition.PRICE_CROSSES:
            return f"🔔 {stock} price crossed ₹{alert.target_value:.2f}, now at ₹{current_price:.2f}"
        elif alert.condition == AlertCondition.PERCENT_CHANGE:
            pct = ((current_price - alert.target_value) / alert.target_value) * 100
            return f"🔔 {stock} has moved {pct:.2f}%, now at ₹{current_price:.2f}"
        elif alert.condition == AlertCondition.VOLUME_SPIKE:
            return f"🔔 {stock} showing unusual volume activity"
        else:
            return f"🔔 Alert triggered for {stock} at ₹{current_price:.2f}"
    
    async def check_alert_conditions(
        self, 
        prices: Dict[str, Dict],
        previous_prices: Optional[Dict[str, float]] = None
    ) -> List[AlertNotification]:
        """Check all active alerts against current prices"""
        notifications = []
        
        active_alerts = await self.get_all_alerts(status=AlertStatus.ACTIVE)
        
        for alert in active_alerts:
            # Check expiration
            if alert.expires_at:
                if datetime.now(timezone.utc) > alert.expires_at:
                    await self.collection.update_one(
                        {"id": alert.id},
                        {"$set": {"status": AlertStatus.EXPIRED.value}}
                    )
                    continue
            
            # Get current price
            symbol = alert.symbol
            if symbol not in prices:
                continue
            
            price_data = prices[symbol]
            current_price = price_data.get("price", price_data.get("current_price", 0))
            
            if current_price <= 0:
                continue
            
            # Check condition
            triggered = self._check_condition(
                alert, 
                current_price, 
                price_data,
                previous_prices.get(symbol) if previous_prices else None
            )
            
            if triggered:
                notification = await self.trigger_alert(alert, current_price)
                notifications.append(notification)
        
        return notifications
    
    def _check_condition(
        self, 
        alert: Alert, 
        current_price: float,
        price_data: Dict,
        previous_price: Optional[float] = None
    ) -> bool:
        """Check if alert condition is met"""
        target = alert.target_value
        
        if alert.condition == AlertCondition.PRICE_ABOVE:
            return current_price >= target
        
        elif alert.condition == AlertCondition.PRICE_BELOW:
            return current_price <= target
        
        elif alert.condition == AlertCondition.PRICE_CROSSES:
            if previous_price is None:
                return False
            # Check if price crossed the target
            crossed_up = previous_price < target <= current_price
            crossed_down = previous_price > target >= current_price
            return crossed_up or crossed_down
        
        elif alert.condition == AlertCondition.PERCENT_CHANGE:
            change_pct = abs(price_data.get("change_percent", 0))
            return change_pct >= target
        
        elif alert.condition == AlertCondition.VOLUME_SPIKE:
            volume = price_data.get("volume", 0)
            avg_volume = price_data.get("avg_volume", volume)
            if avg_volume > 0:
                volume_ratio = volume / avg_volume
                return volume_ratio >= target
            return False
        
        return False
    
    async def get_summary(self) -> AlertSummary:
        """Get summary of all alerts"""
        all_alerts = await self.get_all_alerts()
        
        active = len([a for a in all_alerts if a.status == AlertStatus.ACTIVE])
        
        today = datetime.now(timezone.utc).date()
        triggered_today = len([
            a for a in all_alerts 
            if a.triggered_at and a.triggered_at.date() == today
        ])
        
        by_priority = {}
        by_symbol = {}
        
        for alert in all_alerts:
            # Count by priority
            priority = alert.priority.value if hasattr(alert.priority, 'value') else alert.priority
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            # Count by symbol
            by_symbol[alert.symbol] = by_symbol.get(alert.symbol, 0) + 1
        
        return AlertSummary(
            total_alerts=len(all_alerts),
            active_alerts=active,
            triggered_today=triggered_today,
            alerts_by_priority=by_priority,
            alerts_by_symbol=by_symbol,
        )
    
    async def get_recent_notifications(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent notifications from MongoDB (falls back to in-memory)."""
        try:
            cursor = self.db.alert_notifications.find(
                {}, {"_id": 0}
            ).sort("triggered_at", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            if docs:
                return docs
        except Exception as e:
            logger.debug(f"MongoDB notification read failed, using in-memory: {e}")
        # Fallback to in-memory
        results = []
        for n in self._notifications[-limit:]:
            results.append({
                "alert_id": n.alert_id,
                "symbol": n.symbol,
                "stock_name": n.stock_name,
                "condition": n.condition.value if hasattr(n.condition, 'value') else n.condition,
                "target_value": n.target_value,
                "current_price": n.current_price,
                "message": n.message,
                "priority": n.priority.value if hasattr(n.priority, 'value') else n.priority,
                "triggered_at": n.triggered_at.isoformat() if hasattr(n.triggered_at, 'isoformat') else str(n.triggered_at),
            })
        return results

    async def clear_notifications(self):
        """Clear stored notifications."""
        self._notifications = []
        try:
            await self.db.alert_notifications.delete_many({})
        except Exception as e:
            logger.debug(f"Failed to clear MongoDB notifications: {e}")
    
    # Background task for checking alerts
    async def start_background_checker(self, price_fetcher):
        """Start background task for checking alerts"""
        if self._running:
            return
        
        self._running = True
        self._check_task = asyncio.create_task(
            self._background_check_loop(price_fetcher)
        )
        logger.info("Alert checker started")
    
    async def stop_background_checker(self):
        """Stop background checker"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Alert checker stopped")
    
    async def _background_check_loop(self, price_fetcher):
        """Background loop for checking alerts"""
        previous_prices = {}
        
        while self._running:
            try:
                # Get active alert symbols
                active_alerts = await self.get_all_alerts(status=AlertStatus.ACTIVE)
                symbols = list(set(a.symbol for a in active_alerts))
                
                if symbols:
                    # Fetch prices
                    prices = await price_fetcher(symbols)
                    
                    if prices:
                        # Check conditions
                        notifications = await self.check_alert_conditions(
                            prices, previous_prices
                        )
                        
                        if notifications:
                            logger.info(f"Triggered {len(notifications)} alerts")
                        
                        # Update previous prices
                        for symbol, data in prices.items():
                            previous_prices[symbol] = data.get("price", data.get("current_price", 0))
                
                await asyncio.sleep(self._check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(self._check_interval)


# Singleton instance (will be initialized with db in server.py)
alerts_service: Optional[AlertsService] = None


def init_alerts_service(db: AsyncIOMotorDatabase) -> AlertsService:
    """Initialize alerts service with database"""
    global alerts_service
    alerts_service = AlertsService(db)
    return alerts_service


def get_alerts_service() -> Optional[AlertsService]:
    """Get alerts service instance"""
    return alerts_service
