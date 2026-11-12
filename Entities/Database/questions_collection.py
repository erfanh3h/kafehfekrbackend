from typing import List, Dict, Optional
import random


class QuestionsCollectionManager:
    def __init__(self, collection):
        self.collection = collection

    def count_questions(self) -> int:
        try:
            return self.collection.count_documents({})
        except Exception:
            return 0

    def seed_questions(self, questions_list: List[Dict]):
        if not questions_list:
            return
        # Bulk insert in chunks of 1000
        chunk_size = 1000
        for i in range(0, len(questions_list), chunk_size):
            chunk = questions_list[i:i + chunk_size]
            docs = []
            for item in chunk:
                doc = {
                    "question_id": item["id"],
                    "category_id": item.get("category_id", 0),
                    "category_title": item.get("category_title", "اطلاعات عمومی"),
                    "question": item["question"],
                    "options": item["options"],
                    "correct": item["correct"]
                }
                docs.append(doc)
            try:
                self.collection.insert_many(docs, ordered=False)
            except Exception as e:
                print(f"[QuestionsCollectionManager] Seed chunk error: {e}")

    def get_random_questions(self, count: int = 10) -> List[Dict]:
        try:
            cursor = self.collection.aggregate([{"$sample": {"size": count}}])
            results = []
            for doc in cursor:
                results.append({
                    "id": doc.get("question_id", doc.get("_id")),
                    "category_id": doc.get("category_id", 0),
                    "category_title": doc.get("category_title", "اطلاعات عمومی"),
                    "question": doc.get("question"),
                    "options": doc.get("options"),
                    "correct": doc.get("correct")
                })
            return results
        except Exception as e:
            print(f"[QuestionsCollectionManager] Sample error: {e}")
            return []
