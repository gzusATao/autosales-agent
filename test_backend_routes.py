from pathlib import Path


main_py = Path("backend/main.py").read_text(encoding="utf-8")
knowledge_py = Path("backend/api/knowledge.py").read_text(encoding="utf-8")
requirements = Path("backend/requirements.txt").read_text(encoding="utf-8")

mount_index = main_py.index('app.mount("/", StaticFiles')
health_index = main_py.index('@app.get("/api/health")')
websocket_index = main_py.index('@app.websocket("/ws/chat")')

assert health_index < mount_index, "health route must be registered before the catch-all static mount"
assert websocket_index < mount_index, "chat websocket must be registered before the catch-all static mount"
assert '@router.get("")' in knowledge_py, "knowledge API should expose a document list endpoint"
assert "chunks_count" in knowledge_py, "knowledge document list should include chunk counts for management UI"
assert '"/upload-file"' in knowledge_py, "knowledge API should support document file upload"
assert "UploadFile" in knowledge_py and "File(" in knowledge_py, "file upload should use FastAPI multipart handling"
assert "clean_knowledge_text_with_pandas" in knowledge_py, "uploaded documents should be cleaned before chunking"
assert "pandas" in requirements, "pandas should be available for document cleaning"
assert "python-multipart" in requirements, "multipart upload dependency should be declared"
assert "python-docx" in requirements, "Word document parsing dependency should be declared"
assert "pypdf" in requirements, "PDF parsing dependency should be declared"

print("backend route order checks passed")
