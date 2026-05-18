import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "conversations"


class ConversationStore:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)

    def _guest_file(self, guest_id):
        return self.data_dir / f"{guest_id}.json"

    def get_guest(self, guest_id):
        path = self._guest_file(guest_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"guest_id": guest_id, "conversations": [], "preferences": {}}

    def save_guest(self, data):
        path = self._guest_file(data["guest_id"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_conversation(self, guest_id, message, role="guest"):
        data = self.get_guest(guest_id)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "message": message,
        }
        data["conversations"].append(entry)
        self.save_guest(data)
        return data

    def update_preferences(self, guest_id, preferences):
        data = self.get_guest(guest_id)
        data["preferences"].update(preferences)
        self.save_guest(data)

    def get_recent_quotes(self, guest_id, limit=5):
        data = self.get_guest(guest_id)
        quotes = [c for c in data["conversations"] if "quote" in c]
        return quotes[-limit:]

    def update_conversion_status(self, guest_id, status):
        data = self.get_guest(guest_id)
        data["conversion_status"] = status
        data["conversion_date"] = datetime.now().isoformat()
        self.save_guest(data)

    def get_stats(self):
        stats = {
            "total_guests": 0,
            "total_conversations": 0,
            "conversions": 0,
            "quotes_sent": 0,
        }
        for path in self.data_dir.glob("*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            stats["total_guests"] += 1
            stats["total_conversations"] += len(data.get("conversations", []))
            if data.get("conversion_status") == "booked":
                stats["conversions"] += 1
            quotes = [c for c in data.get("conversations", []) if "quote" in c]
            stats["quotes_sent"] += len(quotes)
        return stats
