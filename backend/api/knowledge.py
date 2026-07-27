"""
知识库 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import KnowledgeDocument, KnowledgeChunk
from backend.schemas.schemas import (
    KnowledgeSearchRequest, KnowledgeSearchResponse, KnowledgeDoc,
    KnowledgeUploadRequest,
)
from backend.rag.rag import simple_vector_search

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.get("")
def list_knowledge(db: Session = Depends(get_db)):
    """List knowledge documents with chunk counts for the management UI."""
    rows = (
        db.query(KnowledgeDocument)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )
    docs = []
    for doc in rows:
        chunks_count = (
            db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.document_id == doc.id)
            .count()
        )
        docs.append({
            "id": doc.id,
            "title": doc.title,
            "doc_type": doc.doc_type,
            "content": doc.content[:220],
            "chunks_count": chunks_count,
            "created_at": doc.created_at.isoformat() if doc.created_at else "",
        })
    return {"docs": docs}


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(req: KnowledgeSearchRequest):
    """检索知识库"""
    docs = simple_vector_search(req.query, top_k=req.top_k)
    return KnowledgeSearchResponse(
        docs=[
            KnowledgeDoc(
                id=d.id,
                title=getattr(d, 'title', ''),
                content=d.chunk_text[:500],
                doc_type=getattr(d, 'doc_type', 'general'),
                score=getattr(d, 'score', 0.0),
            )
            for d in docs
        ]
    )


@router.post("/upload")
def upload_knowledge(req: KnowledgeUploadRequest, db: Session = Depends(get_db)):
    """上传知识文档（含自动分块）"""
    doc = KnowledgeDocument(
        title=req.title,
        doc_type=req.doc_type,
        content=req.content,
        doc_metadata=req.metadata,
    )
    db.add(doc)
    db.flush()

    # 分块（按段落和句子切分）
    chunks = _chunk_text(req.content)
    for i, chunk_text in enumerate(chunks):
        chunk = KnowledgeChunk(
            document_id=doc.id,
            chunk_text=chunk_text,
            chunk_metadata={"chunk_index": i, **req.metadata},
        )
        db.add(chunk)

    db.commit()
    return {
        "document_id": doc.id,
        "chunks": len(chunks),
        "message": "文档已上传并分块",
    }


def _chunk_text(text: str, max_chars: int = 300) -> list[str]:
    """文本分块"""
    chunks = []
    paragraphs = text.split("\n")
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) < max_chars:
            current += para + "\n"
        else:
            if current:
                chunks.append(current.strip())
            # 如果段落本身就很长，按句子拆分
            if len(para) > max_chars:
                import re
                sentences = re.split(r"(?<=[。！？])", para)
                for sent in sentences:
                    if sent:
                        chunks.append(sent.strip())
            else:
                current = para + "\n"

    if current:
        chunks.append(current.strip())

    # 确保没有空块
    return [c for c in chunks if c]
