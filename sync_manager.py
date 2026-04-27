import json
import time
import uuid
import threading
import queue
import logging
from typing import Callable, Dict, List, Any
from PyQt6.QtCore import QObject, pyqtSignal

# Setup logging
from performance_logger import logger as perf_logger

try:
    import websockets
    import asyncio
    SYNC_LIB_AVAILABLE = True
except ImportError:
    SYNC_LIB_AVAILABLE = False

class SyncManager(QObject):
    # Signals for Qt UI
    # Status: 0 = Disconnected (red), 1 = Reconnecting (amber), 2 = Connected (green)
    status_changed = pyqtSignal(int)
    
    def __init__(self, config_manager):
        super().__init__()
        self.config = config_manager
        self.device_id = self.config.get("device_id")
        self.room_id = self.config.get("sync_room_id", "shadow-default")
        self.server_url = self.config.get("sync_server_url", "ws://localhost:8765")
        self.sync_enabled = self.config.get("sync_enabled", False)
        
        if not SYNC_LIB_AVAILABLE:
            perf_logger.warning("[SYNC] websockets or asyncio not found. Sync disabled.")
            self.sync_enabled = False
            
        self.handlers: Dict[str, List[Callable]] = {}
        self.outbound_queue = queue.Queue()
        self.msg_history = [] # LRU-like set for msg_id deduplication
        self.history_limit = 200
        
        self._running = False
        self._thread = None
        self._loop = None
        self._ws = None

    def on(self, event: str, callback: Callable):
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(callback)

    def broadcast(self, event: str, payload: dict):
        if not self.sync_enabled:
            return
            
        envelope = {
            "event": event,
            "source": self.device_id,
            "room": self.room_id,
            "payload": payload,
            "ts": time.time(),
            "msg_id": str(uuid.uuid4())
        }
        self.outbound_queue.put(envelope)

    def start(self):
        if not self.sync_enabled or self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SyncThread")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_task())
        except Exception as e:
            if not isinstance(e, RuntimeError) or "Event loop stopped before Future completed" not in str(e):
                perf_logger.error(f"[SYNC] Main loop error: {e}")
        finally:
            self._loop.close()

    async def _main_task(self):
        backoff = 1
        while self._running:
            try:
                self.status_changed.emit(1) # Reconnecting
                async with websockets.connect(self.server_url) as websocket:
                    self._ws = websocket
                    self.status_changed.emit(2) # Connected
                    backoff = 1 # Reset backoff
                    
                    # Register
                    await websocket.send(json.dumps({
                        "register": True,
                        "room": self.room_id,
                        "device_id": self.device_id
                    }))
                    
                    # Run listener and sender concurrently
                    await asyncio.gather(
                        self._listen_task(websocket),
                        self._send_task(websocket)
                    )
            except Exception as e:
                self.status_changed.emit(0) # Disconnected
                if self._running:
                    # Log less frequently to avoid flooding
                    if backoff <= 2 or backoff >= 30:
                        perf_logger.info(f"[SYNC] Connection error: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff = min(30, backoff * 2)
                else:
                    break

    async def _listen_task(self, websocket):
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_id = data.get("msg_id")
                
                # Ignore own messages
                if data.get("source") == self.device_id:
                    continue
                    
                # Deduplicate
                if msg_id in self.msg_history:
                    continue
                
                self.msg_history.append(msg_id)
                if len(self.msg_history) > self.history_limit:
                    self.msg_history.pop(0)
                
                event = data.get("event")
                if event in self.handlers:
                    for callback in self.handlers[event]:
                        try:
                            # Note: This runs in the sync thread.
                            # Callbacks should be thread-safe or use signals.
                            callback(data.get("payload"), data)
                        except Exception as e:
                            perf_logger.error(f"[SYNC] Callback error for '{event}': {e}")
            except Exception as e:
                perf_logger.error(f"[SYNC] Listener error: {e}")

    async def _send_task(self, websocket):
        while self._running:
            try:
                # Use a non-blocking way to get from queue
                # Since we are in an async loop, we can use a small sleep or a thread-safe future
                while not self.outbound_queue.empty():
                    envelope = self.outbound_queue.get_nowait()
                    await websocket.send(json.dumps(envelope))
                await asyncio.sleep(0.1)
            except websockets.ConnectionClosed:
                break
            except Exception as e:
                perf_logger.error(f"[SYNC] Sender error: {e}")
                await asyncio.sleep(1)

sync_manager = None # Initialized in main.py
