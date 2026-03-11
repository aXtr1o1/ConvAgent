from backend.utils.utilities import db

def user_authFunc(username: str):

    response = db.table("users") \
        .select("userid, bs64encode") \
        .eq("username", username) \
        .limit(1) \
        .execute()

    if response.data:
        user = response.data[0]

        return {
            "user_id": user["userid"],
            "bs64": user["bs64encode"]
        }

    return None