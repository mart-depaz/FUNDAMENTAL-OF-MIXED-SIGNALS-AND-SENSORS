import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)

class BiometricEnrollmentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time biometric enrollment updates.
    Allows frontend to receive real-time scan confirmations from R307.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        self.enrollment_id = self.scope['url_route']['kwargs'].get('enrollment_id', 'default')
        self.group_name = f"biometric_enrollment_{self.enrollment_id}"
        
        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Join group for this enrollment session
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"User {self.user.id} connected to biometric enrollment WebSocket")
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to biometric enrollment service',
            'enrollment_id': self.enrollment_id
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"User {self.user.id} disconnected from biometric enrollment WebSocket")
    
    async def receive(self, text_data):
        """
        Handle incoming messages from frontend
        (for any bidirectional communication)
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'start_enrollment':
                await self.handle_start_enrollment(data)
            elif message_type == 'cancel_enrollment':
                await self.handle_cancel_enrollment(data)
            
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send_error(str(e))
    
    async def handle_start_enrollment(self, data):
        """Handle enrollment start request"""
        template_id = data.get('template_id')
        course_ids = data.get('course_ids', [])
        
        # Broadcast enrollment started
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'enrollment_started',
                'template_id': template_id,
                'course_ids': course_ids,
                'courses_count': len(course_ids)
            }
        )
    
    async def handle_cancel_enrollment(self, data):
        """Handle enrollment cancellation"""
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'enrollment_cancelled',
                'reason': data.get('reason', 'User cancelled')
            }
        )
    
    # Event handlers - called when messages are sent to the group
    
    async def enrollment_started(self, event):
        """Send enrollment started event to client"""
        await self.send(text_data=json.dumps({
            'type': 'enrollment_started',
            'template_id': event['template_id'],
            'course_ids': event['course_ids'],
            'courses_count': event['courses_count'],
            'message': f'Enrollment started for {event["courses_count"]} course(s)'
        }))
    
    async def enrollment_cancelled(self, event):
        """Send enrollment cancelled event"""
        await self.send(text_data=json.dumps({
            'type': 'enrollment_cancelled',
            'reason': event['reason']
        }))
    
    async def scan_update(self, event):
        """Send scan update to client (slot completed)"""
        await self.send(text_data=json.dumps({
            'type': 'scan_update',
            'slot': event['slot'],
            'success': event['success'],
            'quality': event.get('quality', 0),
            'message': event.get('message', ''),
            'progress': event.get('progress', 0)
        }))
    
    async def enrollment_complete(self, event):
        """Send enrollment completion event"""
        await self.send(text_data=json.dumps({
            'type': 'enrollment_complete',
            'success': event['success'],
            'message': event.get('message', 'Enrollment complete'),
            'courses_enrolled': event.get('courses_enrolled', 0)
        }))
    
    async def enrollment_error(self, event):
        """Send enrollment error event"""
        await self.send(text_data=json.dumps({
            'type': 'enrollment_error',
            'error': event['error'],
            'message': event.get('message', 'An error occurred')
        }))
    
    # Helper methods
    
    async def send_error(self, error_message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': error_message
        }))


class BiometricStatusConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time biometric status updates.
    Broadcasts R307 status to all connected clients.
    """
    
    async def connect(self):
        """Handle connection to status channel"""
        self.user = self.scope["user"]
        
        # Join the status group (shared among all users)
        await self.channel_layer.group_add(
            "biometric_status",
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"User {self.user.id} connected to biometric status WebSocket")
    
    async def disconnect(self, close_code):
        """Handle disconnection"""
        await self.channel_layer.group_discard(
            "biometric_status",
            self.channel_name
        )
    
    async def r307_status(self, event):
        """Send R307 status update"""
        await self.send(text_data=json.dumps({
            'type': 'r307_status',
            'status': event['status'],
            'message': event.get('message', ''),
            'timestamp': event.get('timestamp'),
            'is_busy': event.get('is_busy', False)
        }))
