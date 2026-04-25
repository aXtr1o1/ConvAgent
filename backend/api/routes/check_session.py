# scripts/check_session.py
from backend.utils.utilities import db

conversation_id = "187c2f37-a473-4cbf-afb7-17dc416a6c91"

resp = db.table("diagnostic_sessions")\
    .select("*")\
    .eq("conversation_id", conversation_id)\
    .execute()

print("All sessions for this conversation:")
for s in resp.data:
    print(f"  session_id: {s['session_id']}")
    print(f"  status:     {s['status']}")
    print(f"  dtc_code:   {s['dtc_code']}")
    print(f"  step:       {s['current_step']}")
    print()

# Check active only
active = db.table("diagnostic_sessions")\
    .select("*")\
    .eq("conversation_id", conversation_id)\
    .eq("status", "active")\
    .execute()

print(f"Active sessions: {len(active.data)}")