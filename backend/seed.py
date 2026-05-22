from backend.accounts import ADMIN_ACCOUNT, PLAYER_ACCOUNTS
from backend.models import User, db


def seed_users() -> None:
    for acc in PLAYER_ACCOUNTS:
        user = User.query.filter_by(username=acc["username"]).first()
        if not user:
            user = User(username=acc["username"])
            db.session.add(user)
        user.set_password(acc["password"])
        user.is_player = True
        user.is_admin = False
        user.is_judge = False

    admin = User.query.filter_by(username=ADMIN_ACCOUNT["username"]).first()
    if not admin:
        admin = User(username=ADMIN_ACCOUNT["username"])
        db.session.add(admin)
    admin.set_password(ADMIN_ACCOUNT["password"])
    admin.is_player = False
    admin.is_admin = True
    admin.is_judge = False
    admin.position = 0
    admin.turn_phase = "idle"

    for u in User.query.all():
        if u.username == ADMIN_ACCOUNT["username"]:
            continue
        if u.username not in {a["username"] for a in PLAYER_ACCOUNTS}:
            continue
        u.is_player = True
        if u.turn_phase not in (
            "idle",
            "dice_choice",
            "rolling",
            "wheel_ready",
            "wheel",
            "playing",
            "reward_items",
            "durka",
        ):
            u.turn_phase = "idle"

    db.session.commit()
