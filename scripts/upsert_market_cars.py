"""Upsert current hot-market car data into the local demo database."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import init_db, SessionLocal
from backend.models.models import Car, Inventory, KnowledgeChunk, KnowledgeDocument
from backend.seed_data import SEED_CARS, SEED_INVENTORIES, SEED_KNOWLEDGE


def upsert_market_data() -> dict[str, int]:
    init_db()
    db = SessionLocal()
    stats = {"cars": 0, "inventories": 0, "knowledge": 0, "chunks": 0}
    try:
        for car_data in SEED_CARS:
            car = db.query(Car).filter(Car.model == car_data["model"]).first()
            if not car:
                db.add(Car(**car_data))
                stats["cars"] += 1
            else:
                for key, value in car_data.items():
                    setattr(car, key, value)

        db.flush()
        car_map = {car.model: car.id for car in db.query(Car).all()}

        for inv_data in SEED_INVENTORIES:
            car_id = car_map.get(inv_data["model"])
            if not car_id:
                continue
            existing = db.query(Inventory).filter(
                Inventory.car_id == car_id,
                Inventory.city == inv_data["city"],
                Inventory.store_name == inv_data["store"],
                Inventory.color == inv_data["color"],
            ).first()
            if not existing:
                db.add(Inventory(
                    car_id=car_id,
                    city=inv_data["city"],
                    store_name=inv_data["store"],
                    color=inv_data["color"],
                    stock_count=inv_data["stock"],
                    delivery_time=inv_data["delivery"],
                ))
                stats["inventories"] += 1
            else:
                existing.stock_count = inv_data["stock"]
                existing.delivery_time = inv_data["delivery"]

        for doc_data in SEED_KNOWLEDGE:
            doc = db.query(KnowledgeDocument).filter(
                KnowledgeDocument.title == doc_data["title"]
            ).first()
            if doc:
                doc.doc_type = doc_data["doc_type"]
                doc.content = doc_data["content"]
                db.query(KnowledgeChunk).filter(
                    KnowledgeChunk.document_id == doc.id
                ).delete()
            else:
                doc = KnowledgeDocument(
                    title=doc_data["title"],
                    doc_type=doc_data["doc_type"],
                    content=doc_data["content"],
                )
                db.add(doc)
                stats["knowledge"] += 1
            db.flush()

            paragraphs = [p.strip() for p in doc_data["content"].split("\n") if p.strip()]
            for index, paragraph in enumerate(paragraphs):
                db.add(KnowledgeChunk(
                    document_id=doc.id,
                    chunk_text=paragraph,
                    chunk_metadata={"chunk_index": index, "title": doc_data["title"]},
                ))
                stats["chunks"] += 1

        db.commit()
        return stats
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    result = upsert_market_data()
    print(
        "upsert complete: "
        f"{result['cars']} new cars, "
        f"{result['inventories']} new inventory rows, "
        f"{result['knowledge']} new knowledge docs, "
        f"{result['chunks']} rebuilt chunks"
    )
