import json
import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(BASE_DIR, "delta_demo_geometry_state.json")

with open(STATE, "r") as f:
    state = json.load(f)

old_pos = state.get("active_position") or {}
expiry = old_pos.get("expiry", "None")
cost = old_pos.get("total_cost", 0)
print(f"Clearing stale position: expiry={expiry}, total_cost=${cost:.2f}")

state["active_position"] = None
state["is_running"] = True
state["starting"] = False
state["last_update"] = datetime.datetime.now().isoformat()

with open(STATE, "w") as f:
    json.dump(state, f, indent=4)

print("State cleared. Bot will now enter fresh scanning mode on next start.")
