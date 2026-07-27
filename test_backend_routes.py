from pathlib import Path


main_py = Path("backend/main.py").read_text(encoding="utf-8")

mount_index = main_py.index('app.mount("/", StaticFiles')
health_index = main_py.index('@app.get("/api/health")')
websocket_index = main_py.index('@app.websocket("/ws/chat")')

assert health_index < mount_index, "health route must be registered before the catch-all static mount"
assert websocket_index < mount_index, "chat websocket must be registered before the catch-all static mount"

print("backend route order checks passed")
