import asyncio
import json
import logging
import websockets
from websockets.exceptions import ConnectionClosed

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("RelayServer")

# Room management: dict[room_id, set[WebSocket]]
ROOMS = {}

async def relay_handler(websocket):
    client_info = {"room": None, "device_id": None}
    
    try:
        async for message in websocket:
            logger.info(f"[DEBUG] Received raw message: {message}")
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.error(f"[ERROR] Failed to parse JSON: {message}")
                continue

            # Registration (Handle both flat and wrapped envelope formats)
            reg_data = data.get("payload") if isinstance(data.get("payload"), dict) else data
            
            if reg_data.get("register") and ("room" in reg_data or "room" in data):
                room_id = reg_data.get("room") or data.get("room")
                device_id = reg_data.get("device_id") or data.get("source") or data.get("device_id")
                
                client_info["room"] = room_id
                client_info["device_id"] = device_id
                
                if room_id not in ROOMS:
                    ROOMS[room_id] = set()
                ROOMS[room_id].add(websocket)
                
                logger.info(f"Registered device '{device_id}' in room '{room_id}'. Clients: {len(ROOMS[room_id])}")
                continue

            # Broadcast
            room_id = client_info["room"]
            if room_id and room_id in ROOMS:
                # Add source to envelope if not present
                if "source" not in data:
                    data["source"] = client_info["device_id"]
                
                payload = json.dumps(data)
                broadcast_count = 0
                
                # Broadcast to all OTHER clients in the same room
                for client in list(ROOMS[room_id]):
                    if client != websocket:
                        try:
                            await client.send(payload)
                            broadcast_count += 1
                        except ConnectionClosed:
                            ROOMS[room_id].discard(client)
                
                if broadcast_count > 0:
                    logger.info(f"Broadcast event '{data.get('event')}' from '{client_info['device_id']}' to {broadcast_count} clients.")

    except ConnectionClosed:
        pass
    finally:
        # Cleanup on disconnect
        room_id = client_info["room"]
        if room_id and room_id in ROOMS:
            ROOMS[room_id].discard(websocket)
            if not ROOMS[room_id]:
                del ROOMS[room_id]
            logger.info(f"Client '{client_info['device_id']}' disconnected from room '{room_id}'.")

async def main():
    logger.info("Starting Shadow Relay Server on 0.0.0.0:8765...")
    async with websockets.serve(relay_handler, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped.")
