"""Общая логика хода для HTTP и WebSocket."""

from __future__ import annotations

from flask import current_app

from backend.random_utils import randbelow, random_meta

from backend.board import BOARD_BY_ID, BOARD_SIZE, DURKA_CELL_ID, START_CELL_ID
from backend.models import User, db
from backend.services import game_lists
from backend.services.turn_service import (
    apply_start_bonus,
    cell_game_source,
    create_player_game,
    roll_dice,
)
from backend.turn_logic import require_phase


from backend.pending_wheels import (
    pending_crown_pick as _pending_crown_pick,
    pending_dice_choice as _pending_dice_choice,
    pending_item_wheel as _pending_item_wheel,
    pending_shop_pick as _pending_shop_pick,
    pending_spin as _pending_spin,
    pending_wheel as _pending_wheel,
)


def _socketio():
    return current_app.extensions["socketio"]


def _emit(event: str, payload: dict) -> None:
    _socketio().emit(event, payload, room="lobby", namespace="/")


def _wheel_ui_meta(user: User) -> dict:
    from backend.items.admin_wheel import admin_wheel_vote_labels, get_active_admin_wheel
    from backend.items.gameplay import collect_vote_banners
    from backend.items.wheel_extras import extra_wheel_spins_left

    vote_labels = collect_vote_banners(user.id)
    admin_labels = admin_wheel_vote_labels(user.id)
    merged = admin_labels + [v for v in vote_labels if v not in admin_labels]
    return {
        "extraWheelSpinsRemaining": extra_wheel_spins_left(user.id),
        "voteLabels": merged,
        "adminWheelEffect": get_active_admin_wheel(user.id),
    }


def _user_payload(user: User, **extra) -> dict:
    return {"username": user.username, "displayName": user.public_name(), "userId": user.id, **extra}


def _preload_wheel_hltb(user_id: int, titles: list[str], app) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from backend.services.hltb_service import hltb_url_for_title

    with app.app_context():
        with ThreadPoolExecutor(max_workers=4) as pool:
            links = list(pool.map(hltb_url_for_title, titles))
        _emit(
            "wheel_hltb_ready",
            {
                "userId": user_id,
                "items": [
                    {"title": t, "hltbUrl": u} for t, u in zip(titles, links)
                ],
            },
        )


def _build_path(start: int, steps: int, in_durka: bool) -> tuple[list[int], int, bool]:
    if in_durka:
        return [DURKA_CELL_ID] * max(steps, 1), DURKA_CELL_ID, False

    path: list[int] = []
    pos = start
    passed_start = False
    for _ in range(steps):
        nxt = (pos + 1) % BOARD_SIZE
        if nxt == START_CELL_ID and pos != START_CELL_ID:
            passed_start = True
        pos = nxt
        path.append(pos)
    return path, pos, passed_start


def _wheel_games_for_cell(cell_id: int, genre_id: int | None = None) -> tuple[list[str], dict]:
    src = cell_game_source(cell_id)
    if genre_id:
        src["genreId"] = genre_id
    wheel: list[str] = []
    if src.get("durkaCell"):
        return [], src
    if src.get("itemWheel"):
        return [], src
    if src.get("lottery"):
        pass
    elif src.get("trallalero"):
        pool = game_lists.trallalero_games()
        wheel = game_lists.pick_random(pool, min(12, len(pool)))
    elif src.get("question"):
        pool = game_lists.question_games()
        wheel = game_lists.pick_random(pool, min(12, len(pool)))
    elif src.get("needsGenrePick"):
        pass
    elif src.get("genreId"):
        wheel = game_lists.wheel_games(src["genreId"], 12)
    return wheel, src


def roll_dice_for_user(user: User, options: dict | None = None) -> dict | tuple[dict, int]:
    from backend.services.game_history import block_new_turn_if_in_progress

    in_progress = block_new_turn_if_in_progress(user)
    if in_progress:
        return {"error": in_progress}, 400
    err = require_phase(user, "idle")
    if err:
        return {"error": err}, 400
    if user.in_durka:
        return {"error": "Сначала пройдите игру в дурке"}, 400

    options = options or {}
    user.last_position = user.position
    d1, d2, label = roll_dice()
    from backend.items.modifiers import (
        apply_dice_roll,
        cheat_replacement_pending,
        dice_choice_needed,
    )

    choice = dice_choice_needed(user, d1, d2, options)
    if choice and choice.get("type") == "trinity":
        return _begin_physics_dice_roll(user, dice_count=3)

    return _begin_physics_dice_roll(user)


def _begin_physics_dice_roll(user: User, dice_count: int = 2) -> dict:
    """Ждём физический бросок на клиенте; движение — после confirm-dice-physics."""
    user.last_position = user.position
    user.turn_phase = "rolling"
    db.session.commit()
    payload = {
        **_user_payload(user),
        "awaitingPhysics": True,
        "diceCount": dice_count,
        "user": user.to_public_dict(),
    }
    _emit("dice_rolled", payload)
    payload["user"] = user.to_public_dict()
    return payload


def _defer_cheat_after_physics(user: User, d1: int, d2: int) -> dict:
    _pending_dice_choice[user.id] = {
        "d1": d1,
        "d2": d2,
        "type": "cheat",
        "dice": [d1, d2],
    }
    user.turn_phase = "dice_choice"
    db.session.commit()
    payload = {
        **_user_payload(user),
        "dice": [d1, d2],
        "awaitingCheat": True,
        "user": user.to_public_dict(),
    }
    _emit("dice_rolled", payload)
    payload["user"] = user.to_public_dict()
    return payload


def _defer_trinity_after_physics(user: User, d1: int, d2: int, d3: int) -> dict:
    _pending_dice_choice[user.id] = {
        "d1": d1,
        "d2": d2,
        "type": "trinity",
        "dice": [d1, d2, d3],
    }
    user.turn_phase = "dice_choice"
    db.session.commit()
    payload = {
        **_user_payload(user),
        "dice": [d1, d2, d3],
        "awaitingTrinityPick": True,
        "needsDiceChoice": {"type": "trinity"},
        "user": user.to_public_dict(),
    }
    _emit("dice_rolled", payload)
    payload["user"] = user.to_public_dict()
    return payload


def confirm_dice_physics_for_user(
    user: User, data: dict | None = None
) -> dict | tuple[dict, int]:
    from backend.items.modifiers import _has_mod, cheat_replacement_pending

    err = require_phase(user, "rolling")
    if err:
        return {"error": err}, 400

    data = data or {}
    dice = data.get("dice") or []

    tri = _has_mod(user.id, "trinity_dice")
    if tri:
        if len(dice) < 3:
            return {"error": "Нужны три значения кубиков"}, 400
        try:
            d1, d2, d3 = int(dice[0]), int(dice[1]), int(dice[2])
        except (TypeError, ValueError):
            return {"error": "Некорректные значения кубиков"}, 400
        if not all(1 <= v <= 6 for v in (d1, d2, d3)):
            return {"error": "Кубик должен быть от 1 до 6"}, 400
        return _defer_trinity_after_physics(user, d1, d2, d3)

    if len(dice) < 2:
        return {"error": "Нужны два значения кубиков"}, 400
    try:
        d1, d2 = int(dice[0]), int(dice[1])
    except (TypeError, ValueError):
        return {"error": "Некорректные значения кубиков"}, 400
    if not (1 <= d1 <= 6 and 1 <= d2 <= 6):
        return {"error": "Кубик должен быть от 1 до 6"}, 400

    if cheat_replacement_pending(user, {}):
        return _defer_cheat_after_physics(user, d1, d2)

    return _finish_dice_roll(user, d1, d2, data)


def confirm_dice_roll_for_user(
    user: User, options: dict | None = None
) -> dict | tuple[dict, int]:
    err = require_phase(user, "dice_choice")
    if err:
        return {"error": err}, 400

    pending = _pending_dice_choice.pop(user.id, None)
    if not pending:
        return {"error": "Нет ожидающего выбора кубиков"}, 400

    from backend.items.modifiers import (
        _consume_mod,
        _has_mod,
        cheat_replacement_pending,
    )

    options = dict(options or {})
    d1, d2 = pending["d1"], pending["d2"]

    if pending.get("type") == "trinity":
        pick = options.get("trinityPick")
        if not pick or len(pick) != 2:
            return {"error": "Выберите два кубика из трёх"}, 400
        d1, d2 = int(pick[0]), int(pick[1])
        tri = _has_mod(user.id, "trinity_dice")
        if tri:
            _consume_mod(tri)
        options["trinityPick"] = pick
        dice = pending.get("dice") or []
        if len(dice) >= 3:
            options["trinityThird"] = dice[2]
        if cheat_replacement_pending(user, options):
            _pending_dice_choice[user.id] = {
                "d1": d1,
                "d2": d2,
                "type": "cheat",
                "dice": [d1, d2],
            }
            user.turn_phase = "dice_choice"
            db.session.commit()
            payload = {
                **_user_payload(user),
                "dice": [d1, d2],
                "awaitingCheat": True,
                "user": user.to_public_dict(),
            }
            _emit("dice_rolled", payload)
            return payload
        return _finish_dice_roll(user, d1, d2, options)

    if pending.get("type") == "cheat":
        if options.get("cheatDie") not in (1, 2) or not options.get("cheatValue"):
            return {"error": "Укажите кубик и новое значение"}, 400
        val = int(options["cheatValue"])
        if val < 1 or val > 6:
            return {"error": "Значение кубика: 1–6"}, 400
        return _finish_dice_roll(user, d1, d2, options)

    return {"error": "Неизвестный тип выбора"}, 400


def reveal_trinity_dice_for_user(user: User) -> dict | tuple[dict, int]:
    err = require_phase(user, "dice_choice")
    if err:
        return {"error": err}, 400
    pending = _pending_dice_choice.get(user.id)
    if not pending or pending.get("type") != "trinity":
        return {"error": "Нет ожидающего броска троицы"}, 400
    dice = pending.get("dice")
    if not dice or len(dice) < 3:
        from backend.random_utils import randint

        d3 = randint(1, 6)
        dice = [pending["d1"], pending["d2"], d3]
        pending["dice"] = dice
    return {"dice": dice}


def _finish_dice_roll(
    user: User, d1: int, d2: int, options: dict | None = None
) -> dict:
    from backend.items.modifiers import apply_dice_roll, build_move_path

    options = options or {}
    d1, d2, steps, label, move_meta, factors = apply_dice_roll(
        user, d1, d2, use_cheat=options
    )
    user.turn_phase = "rolling"
    db.session.commit()

    backward = bool(move_meta.get("backward"))
    path, new_pos, passed = build_move_path(
        user.position, steps, backward=backward
    )

    payload = {
        **_user_payload(user),
        "rawDice": move_meta.get("rawDice", [d1, d2]),
        "dice": [d1, d2],
        "steps": steps,
        "label": label,
        "fromPosition": user.position,
        "movePath": path,
        "stepMs": int(STEP_DELAY_SEC * 1000),
        "avatarUrl": user.avatar_url or "/avatars/default.png",
        "moveMeta": move_meta,
        "factors": factors,
        "user": user.to_public_dict(),
        **random_meta(),
    }
    _emit("dice_rolled", payload)
    _socketio().start_background_task(
        _animate_and_finish,
        user.id,
        steps,
        label,
        move_meta,
        factors,
        current_app._get_current_object(),
        path,
        new_pos,
        passed,
    )
    payload["user"] = user.to_public_dict()
    return payload


STEP_DELAY_SEC = 0.55


def _animate_and_finish(
    user_id: int,
    steps: int,
    label: str,
    move_meta: dict,
    factors: list,
    app,
    path: list | None = None,
    new_pos: int | None = None,
    passed: bool | None = None,
) -> None:
    from backend.items.inventory import log_turn
    from backend.items.modifiers import build_move_path, tick_turn_modifiers

    step_delay = STEP_DELAY_SEC
    backward = bool(move_meta.get("backward"))

    with app.app_context():
        user = db.session.get(User, user_id)
        if not user or user.turn_phase != "rolling":
            return

        if path is None or new_pos is None or passed is None:
            path, new_pos, passed = build_move_path(
                user.position, steps, backward=backward
            )

        _emit(
            "token_move_path",
            {
                **_user_payload(user),
                "fromPosition": user.position,
                "path": path,
                "stepMs": int(step_delay * 1000),
                "avatarUrl": user.avatar_url or "/avatars/default.png",
            },
        )

        skip_start_bonus = bool(user.no_start_bonus_lap)
        bonus = (
            apply_start_bonus(user, passed)
            if not user.in_durka and not backward
            else 0
        )
        user.position = new_pos
        if new_pos == DURKA_CELL_ID and not user.in_durka:
            user.turn_phase = "durka_choice"
        elif new_pos == START_CELL_ID:
            user.turn_phase = "idle"
        else:
            user.turn_phase = "wheel_ready"
        db.session.commit()

        tick_notes = tick_turn_modifiers(user.id)
        all_factors = list(factors) + tick_notes
        if skip_start_bonus and passed and bonus == 0:
            all_factors.append("Дурка на круге: без +5 за проход через старт")

        _, src = _wheel_games_for_cell(new_pos)
        cell = BOARD_BY_ID[new_pos]
        log_turn(
            user.id,
            summary=f"Ход: {label}",
            factors=all_factors,
            dice_label=label,
            cell_name=cell.name,
        )
        _emit(
            "move_finished",
            {
                **_user_payload(user),
                "position": new_pos,
                "passedStartBonus": bonus,
                "diceLabel": label,
                "factors": all_factors,
                "user": user.to_public_dict(),
                "cell": {
                    "id": cell.id,
                    "name": cell.name,
                    "type": cell.cell_type,
                },
                "source": src,
            },
        )


def _open_durka_wheel(user: User) -> dict:
    """Колесо в дурке после дропа: случайный жанр + 12 игр."""
    from backend.board import DURKA_CELL_ID, GENRE_LABELS

    if not user.in_durka:
        return {"error": "Ролл в дурке доступен только после дропа"}
    if user.position != DURKA_CELL_ID:
        return {"error": "Для ролла в дурке игрок должен быть на клетке «Дурка»"}

    gid = game_lists.blazerd_genre_roll()
    wheel = game_lists.wheel_games(gid, 12)
    if not wheel:
        return {"error": f"Нет игр для жанра {gid}"}

    user.turn_phase = "wheel"
    _pending_wheel[user.id] = wheel
    db.session.commit()

    src = {
        "cellId": DURKA_CELL_ID,
        "cellName": "Дурка",
        "cellType": "durka",
        "genreId": gid,
        "blazerdGenre": gid,
        "blazerdGenreLabel": GENRE_LABELS.get(gid, f"Жанр {gid}"),
        "durka": True,
        "durkaNoPoints": True,
    }
    payload = {
        **_user_payload(user),
        "wheel": wheel,
        "wheelType": "game",
        "source": src,
        "cellName": "Дурка",
        "blazerdGenreLabel": src["blazerdGenreLabel"],
        "user": user.to_public_dict(),
    }
    _emit("wheel_opened", payload)
    return payload


def durka_roll_for_user(user: User) -> dict | tuple[dict, int]:
    if user.turn_phase not in ("durka", "wheel_ready", "wheel"):
        err = require_phase(user, "durka")
        return {"error": err}, 400
    result = _open_durka_wheel(user)
    if "error" in result:
        return result, 400
    return result


def durka_step_for_user(user: User, direction: str) -> dict | tuple[dict, int]:
    """На клетке «Дурка» без дропа: шаг вперёд или назад → колесо целевой клетки."""
    err = require_phase(user, "durka_choice")
    if err:
        return {"error": err}, 400
    if user.position != DURKA_CELL_ID:
        return {"error": "Вы не на клетке «Дурка»"}, 400

    direction = str(direction or "").strip().lower()
    if direction in ("forward", "fwd", "вперёд", "вперед", "+1", "1"):
        new_pos = (user.position + 1) % BOARD_SIZE
        dir_label = "вперёд"
    elif direction in ("backward", "back", "назад", "-1"):
        new_pos = (user.position - 1) % BOARD_SIZE
        dir_label = "назад"
    else:
        return {"error": "Укажите direction: forward или backward"}, 400

    from backend.items.inventory import log_turn

    user.position = new_pos
    if new_pos == START_CELL_ID:
        user.turn_phase = "idle"
    else:
        user.turn_phase = "wheel_ready"
    db.session.commit()

    cell = BOARD_BY_ID[new_pos]
    _, src = _wheel_games_for_cell(new_pos)
    log_turn(
        user.id,
        summary=f"Дурка: шаг {dir_label} → {cell.name}",
        factors=[f"Клетка «Дурка»: выбран шаг {dir_label}"],
        cell_name=cell.name,
    )

    payload = {
        **_user_payload(user),
        "position": new_pos,
        "passedStartBonus": 0,
        "diceLabel": f"дурка-{dir_label}",
        "user": user.to_public_dict(),
        "cell": {"id": cell.id, "name": cell.name, "type": cell.cell_type},
        "source": src,
        "durkaStep": direction,
    }
    _emit("move_finished", payload)

    if user.turn_phase == "wheel_ready":
        opened = open_wheel_for_user(user)
        if isinstance(opened, tuple):
            return opened
        return opened
    payload["user"] = user.to_public_dict()
    return payload


def _apply_item_pick_to_recovery_payload(payload: dict, user_id: int) -> None:
    """Восстановить выбор магазина на колесе предметов."""
    shop = _pending_shop_pick.get(user_id)
    if shop:
        items = payload.get("wheelItems") or _pending_item_wheel.get(user_id, [])
        landed = shop.get("landedIndex")
        landed_item = (
            items[landed] if landed is not None and items and 0 <= landed < len(items) else {}
        )
        payload["shopPick"] = {
            "pickKind": "shop",
            "mode": shop.get("mode"),
            "landedIndex": landed,
            "landedTitle": landed_item.get("name") if landed_item else None,
            "choices": shop.get("choices") or [],
            "pickCount": 1 if shop.get("mode") == "chat" else 2,
        }
        if landed is not None:
            payload["targetIndex"] = landed
        payload["wheelType"] = "item"


def _recovery_wheel_payload(user: User, src: dict) -> dict | None:
    """Восстановление UI колеса после перезагрузки страницы (фаза wheel)."""
    if user.turn_phase != "wheel":
        return None
    cell_name = BOARD_BY_ID[user.position].name

    from backend.reward_wheels import recovery_reward_wheel_payload

    reward_rec = recovery_reward_wheel_payload(user)
    if reward_rec:
        return reward_rec

    spin = _pending_spin.get(user.id, {})
    shop_pending = _pending_shop_pick.get(user.id)
    items = _pending_item_wheel.get(user.id, [])

    is_item_wheel = bool(
        src.get("itemWheel")
        or items
        or shop_pending
        or spin.get("wheelType") == "item"
    )

    if is_item_wheel and items:
        item_src = {**src, "itemWheel": True}
        payload = {
            **_user_payload(user),
            "wheel": [i.get("wheelLabel") or i.get("name") for i in items],
            "wheelType": "item",
            "wheelItems": items,
            "source": item_src,
            "cellName": cell_name,
            "recovered": True,
            "user": user.to_public_dict(),
            **_wheel_ui_meta(user),
        }
        _apply_item_pick_to_recovery_payload(payload, user.id)
        _apply_pending_spin_to_payload(user.id, payload)
        return payload

    wheel = _pending_wheel.get(user.id, [])
    if not wheel and not src.get("lottery") and not src.get("needsGenrePick"):
        wheel, _ = _wheel_games_for_cell(user.position)
        if wheel:
            _pending_wheel[user.id] = wheel
    if not wheel and not src.get("lottery") and not src.get("needsGenrePick"):
        return None
    payload = {
        **_user_payload(user),
        "wheel": wheel,
        "source": src,
        "cellName": cell_name,
        "recovered": True,
        "user": user.to_public_dict(),
    }
    crown_pending = _pending_crown_pick.get(user.id)
    if crown_pending:
        payload["crownPick"] = {
            "landedIndex": crown_pending.get("landedIndex"),
            "choices": crown_pending.get("choices") or [],
        }
        payload["targetIndex"] = crown_pending.get("landedIndex")
    _apply_pending_spin_to_payload(user.id, payload)
    return payload


def _apply_pending_spin_to_payload(user_id: int, payload: dict) -> None:
    spin = _pending_spin.get(user_id)
    if not spin:
        return
    payload["targetIndex"] = spin.get("targetIndex")
    if spin.get("selectedItemId") is not None:
        payload["selectedItemId"] = spin["selectedItemId"]
    if spin.get("selectedItemName"):
        payload["selectedItemName"] = spin["selectedItemName"]
    if spin.get("selectedGame"):
        payload["selectedGame"] = spin["selectedGame"]
    if spin.get("shopPick"):
        payload["shopPick"] = spin["shopPick"]
    if spin.get("crownPick"):
        payload["crownPick"] = spin["crownPick"]
    if spin.get("wheelType"):
        payload["wheelType"] = spin["wheelType"]
    if spin.get("duplicateGame"):
        payload["duplicateGame"] = spin["duplicateGame"]


def open_wheel_for_user(user: User, genre_id: int | None = None) -> dict | tuple[dict, int]:
    from backend.pending_wheels import consume_chocolate_genre

    if user.in_durka and user.position == DURKA_CELL_ID:
        if user.turn_phase not in ("wheel_ready", "durka", "wheel"):
            return {"error": "Неверная фаза для ролла в дурке"}, 400
        result = _open_durka_wheel(user)
        if "error" in result:
            return result, 400
        return result

    choc_genre = consume_chocolate_genre(user.id)
    if choc_genre is not None:
        from backend.board import GENRE_LABELS

        wheel = game_lists.wheel_games(choc_genre, 12)
        src = cell_game_source(user.position)
        src = {
            **src,
            "genreId": choc_genre,
            "chocolateOverride": True,
            "blazerdGenreLabel": GENRE_LABELS.get(choc_genre, f"Жанр {choc_genre}"),
        }
        if not wheel:
            return {"error": f"Нет игр для жанра {choc_genre}"}, 400
    else:
        wheel, src = _wheel_games_for_cell(user.position, genre_id)
    recovered = _recovery_wheel_payload(user, src)
    if recovered:
        return recovered

    err = require_phase(user, "wheel_ready")
    if err:
        return {"error": err}, 400

    if src.get("startReroll") or user.position == START_CELL_ID:
        user.turn_phase = "idle"
        db.session.commit()
        return {"error": "На старте нет колеса — бросьте кубик ещё раз"}, 400

    if src.get("durkaCell") and user.turn_phase == "durka_choice":
        return {"error": "Сначала выберите шаг вперёд или назад"}, 400

    from backend.items.admin_wheel import (
        admin_wheel_genre_payload,
        admin_wheel_open,
        get_active_admin_wheel,
    )

    admin_fx = get_active_admin_wheel(user.id)
    if admin_fx:
        if genre_id is None and admin_fx.get("genreId") is not None:
            genre_id = int(admin_fx["genreId"])
        if genre_id is None:
            return admin_wheel_genre_payload(user)
        gid = int(genre_id)
        if admin_fx.get("genreId") != gid:
            from backend.board import GENRE_LABELS
            from backend.pending_wheels import set_admin_wheel

            set_admin_wheel(
                user.id,
                {
                    **admin_fx,
                    "genreId": gid,
                    "genreLabel": GENRE_LABELS.get(gid, f"Жанр {gid}"),
                },
            )
        wheel, src = admin_wheel_open(user, gid)
        if not wheel:
            return {"error": f"Нет игр для жанра {genre_id}"}, 400
        user.turn_phase = "wheel"
        _pending_wheel[user.id] = wheel
        db.session.commit()
        payload = {
            **_user_payload(user),
            "wheel": wheel,
            "wheelType": "game",
            "source": src,
            "cellName": BOARD_BY_ID[user.position].name,
            "blazerdGenreLabel": src.get("blazerdGenreLabel"),
            "user": user.to_public_dict(),
            **_wheel_ui_meta(user),
        }
        _emit("wheel_opened", payload)
        return payload

    if src.get("itemWheel"):
        from backend.items.wheel import pick_wheel_items

        picked = pick_wheel_items(12, user_id=user.id)
        _pending_item_wheel[user.id] = [i.to_dict() for i in picked]
        wheel = [i.wheel_label for i in picked]
        user.turn_phase = "wheel"
        db.session.commit()
        payload = {
            **_user_payload(user),
            "wheel": wheel,
            "wheelType": "item",
            "wheelItems": _pending_item_wheel[user.id],
            "source": src,
            "cellName": BOARD_BY_ID[user.position].name,
            "user": user.to_public_dict(),
            **_wheel_ui_meta(user),
        }
        _emit("wheel_opened", payload)
        payload["user"] = user.to_public_dict()
        return payload

    if src.get("needsGenrePick"):
        from backend.board import GENRE_LABELS, GENRE_SHORT_LABELS

        if genre_id is None:
            return {
                **_user_payload(user),
                "needsGenrePick": True,
                "source": src,
                "cellName": BOARD_BY_ID[user.position].name,
                "genres": [
                    {
                        "id": gid,
                        "label": GENRE_LABELS[gid],
                        "shortLabel": GENRE_SHORT_LABELS.get(gid, GENRE_LABELS[gid]),
                        "buttonLabel": GENRE_SHORT_LABELS.get(gid, GENRE_LABELS[gid]),
                    }
                    for gid in sorted(GENRE_LABELS)
                ],
                "user": user.to_public_dict(),
            }
        src = {
            **src,
            "genreId": int(genre_id),
            "blazerdGenre": int(genre_id),
            "needsGenrePick": False,
            "blazerdGenreLabel": GENRE_LABELS.get(int(genre_id), f"Жанр {genre_id}"),
        }
        wheel = game_lists.wheel_games(int(genre_id), 12)
        if not wheel:
            return {"error": f"Нет игр для жанра {genre_id}"}, 400
        user.turn_phase = "wheel"
        _pending_wheel[user.id] = wheel
        db.session.commit()
        payload = {
            **_user_payload(user),
            "wheel": wheel,
            "wheelType": "game",
            "source": src,
            "cellName": BOARD_BY_ID[user.position].name,
            "blazerdGenreLabel": src["blazerdGenreLabel"],
            "user": user.to_public_dict(),
        }
        _emit("wheel_opened", payload)
        return payload

    user.turn_phase = "wheel"
    _pending_wheel[user.id] = wheel
    db.session.commit()

    payload = {
        **_user_payload(user),
        "wheel": wheel,
        "wheelType": "game",
        "source": src,
        "cellName": BOARD_BY_ID[user.position].name,
        "user": user.to_public_dict(),
        **_wheel_ui_meta(user),
    }
    if src.get("blazerdGenreLabel"):
        payload["blazerdGenreLabel"] = src["blazerdGenreLabel"]
    _emit("wheel_opened", payload)
    # HLTB: только быстрые ссылки на клиенте (без тяжёлого парсинга при открытии)
    payload["user"] = user.to_public_dict()
    return payload


def spin_wheel_for_user(user: User) -> dict | tuple[dict, int]:
    err = require_phase(user, "wheel")
    if err:
        return {"error": err}, 400

    from backend.reward_wheels import is_reward_wheel, spin_reward_wheel_for_user

    if is_reward_wheel(user.id):
        return spin_reward_wheel_for_user(user, emit=_emit)

    src = cell_game_source(user.position)
    if src.get("itemWheel"):
        items = _pending_item_wheel.get(user.id, [])
        if not items:
            return {"error": "Нет предметов для колеса"}, 400
        target_index = randbelow(len(items))
        chosen = items[target_index]
        from backend.items.wheel_pick import choices_five_for_items
        from backend.pending_wheels import get_shop_repick, pop_shop_repick, set_shop_pick

        payload = {
            **_user_payload(user),
            "targetIndex": target_index,
            "wheelType": "item",
            "wheel": [i.get("wheelLabel") or i.get("name") for i in items],
            "wheelItems": items,
            "user": user.to_public_dict(),
            **_wheel_ui_meta(user),
            **random_meta(),
        }
        shop_repick = get_shop_repick(user.id)
        if shop_repick:
            mode = shop_repick.get("mode")
            choices = choices_five_for_items(items, target_index)
            pop_shop_repick(user.id)
            set_shop_pick(
                user.id,
                {
                    "mode": mode,
                    "effectItemId": shop_repick.get("effectItemId"),
                    "choices": choices,
                    "landedIndex": target_index,
                },
            )
            payload["shopPick"] = {
                "pickKind": "shop",
                "mode": mode,
                "landedIndex": target_index,
                "landedTitle": chosen.get("name"),
                "choices": choices,
                "pickCount": 1 if mode == "chat" else 2,
            }
        else:
            payload["selectedItemId"] = chosen.get("id")
            payload["selectedItemName"] = chosen.get("name")
        _pending_spin[user.id] = {
            "targetIndex": target_index,
            "selectedItemId": payload.get("selectedItemId"),
            "selectedItemName": payload.get("selectedItemName"),
            "wheelType": "item",
            "shopPick": payload.get("shopPick"),
        }
        _emit("wheel_spin", payload)
        payload["user"] = user.to_public_dict()
        return payload

    wheel = _pending_wheel.get(user.id, [])
    if not wheel and not src.get("lottery") and not src.get("itemWheel"):
        rebuilt, _ = _wheel_games_for_cell(user.position)
        if rebuilt:
            wheel = rebuilt
            _pending_wheel[user.id] = wheel
    if src.get("lottery"):
        target_index = 0
        selected = ""
    elif not wheel:
        return {"error": "Нет игр для колеса"}, 400
    else:
        target_index = randbelow(len(wheel))
        selected = wheel[target_index]

    from backend.services.game_history import player_has_game_title

    duplicate_game = bool(selected) and player_has_game_title(user.id, selected)

    payload = {
        **_user_payload(user),
        "targetIndex": target_index,
        "selectedGame": selected,
        "wheel": wheel,
        "duplicateGame": duplicate_game,
        "user": user.to_public_dict(),
        **_wheel_ui_meta(user),
        **random_meta(),
    }

    from backend.items.modifiers import _has_mod

    def _crown_active(uid: int) -> bool:
        return bool(
            _has_mod(uid, "wheel_crown_pick") or _has_mod(uid, "wheel_crown")
        )

    crown = _crown_active(user.id)
    skip_crown = bool(
        src.get("lottery") or src.get("trallalero") or src.get("itemWheel")
    )
    if crown and wheel and not skip_crown:
        from backend.items.wheel_pick import choices_for_titles

        idx = target_index
        choices = choices_for_titles(wheel, idx, four=False)
        _pending_crown_pick[user.id] = {
            "landedIndex": idx,
            "choices": choices,
            "wheel": wheel,
        }
        payload["crownPick"] = {
            "landedIndex": idx,
            "choices": choices,
        }
        payload.pop("selectedGame", None)

    _pending_spin[user.id] = {
        "targetIndex": target_index,
        "selectedGame": payload.get("selectedGame"),
        "wheelType": "game",
        "crownPick": payload.get("crownPick"),
        "duplicateGame": duplicate_game,
    }

    _emit("wheel_spin", payload)
    payload["user"] = user.to_public_dict()
    return payload


def dismiss_wheel_for_user(user: User) -> dict | tuple[dict, int]:
    err = require_phase(user, "wheel")
    if err:
        return {"error": err}, 400

    from backend.pending_wheels import pop_wheel_banner

    _pending_item_wheel.pop(user.id, None)
    _pending_wheel.pop(user.id, None)
    _pending_spin.pop(user.id, None)
    _pending_shop_pick.pop(user.id, None)
    _pending_crown_pick.pop(user.id, None)
    pop_wheel_banner(user.id)
    user.turn_phase = "wheel_ready"
    db.session.commit()
    payload = {
        **_user_payload(user),
        "user": user.to_public_dict(),
        **_wheel_ui_meta(user),
    }
    _emit("wheel_dismissed", payload)
    return payload


def confirm_wheel_for_user(user: User, data: dict | None) -> dict | tuple[dict, int]:
    data = data or {}
    from backend.reward_wheels import confirm_reward_wheel_for_user, is_reward_wheel

    if is_reward_wheel(user.id) or data.get("wheelType") == "reward_item":
        return confirm_reward_wheel_for_user(user, data, emit=_emit)

    err = require_phase(user, "wheel")
    if err:
        return {"error": err}, 400

    src = cell_game_source(user.position)
    if src.get("itemWheel") or data.get("wheelType") == "item":
        shop_pending = _pending_shop_pick.get(user.id)
        if shop_pending:
            mode = shop_pending.get("mode")
            choices = shop_pending.get("choices") or []
            effect_item_id = int(shop_pending.get("effectItemId") or (24 if mode == "chat" else 25))
            cell = BOARD_BY_ID[user.position]
            dice_label = str(data.get("diceLabel") or "?")
            items_wheel = _pending_item_wheel.get(user.id, [])
            from backend.items.admin_item_grant import resolve_admin_item_wheel
            from backend.random_utils import choice as rand_choice

            def _sector(row: dict) -> dict:
                wi = row.get("wheelIndex")
                it = items_wheel[wi] if wi is not None and 0 <= wi < len(items_wheel) else {}
                return {
                    "itemId": row.get("itemId") or it.get("id"),
                    "name": it.get("name"),
                    "wheelLabel": row.get("title") or it.get("wheelLabel") or it.get("name"),
                    "wheelIndex": wi,
                }

            if mode == "chat":
                picked = rand_choice(choices) if choices else None
                if not picked:
                    return {"error": "Нет вариантов для голосования чата"}, 400
                sectors = [_sector(picked)]
                note = f"Чат выбрал: «{picked.get('title')}»"
            elif mode == "leprechaun":
                raw = data.get("shopChoiceIndexes")
                if not isinstance(raw, list) or len(raw) != 2:
                    return {"error": "Выберите ровно 2 сектора"}, 400
                try:
                    idxs = [int(x) for x in raw]
                except (TypeError, ValueError):
                    return {"error": "Некорректный выбор"}, 400
                picked_rows = []
                for ci in idxs:
                    row = next((c for c in choices if c.get("choiceIndex") == ci), None)
                    if not row:
                        return {"error": "Некорректный выбор"}, 400
                    picked_rows.append(row)
                sectors = [_sector(r) for r in picked_rows]
                note = "Выбрано: " + ", ".join(s.get("wheelLabel") or "?" for s in sectors)
            else:
                return {"error": "Неизвестный режим магазина"}, 400

            _pending_shop_pick.pop(user.id, None)
            result = resolve_admin_item_wheel(
                user,
                effect_item_id,
                sectors,
                dice_label=dice_label,
                cell_name=cell.name,
                note=note,
            )
            _pending_item_wheel.pop(user.id, None)
            _pending_spin.pop(user.id, None)
            payload = {
                **_user_payload(user),
                **result,
                "wheelType": "item",
                "user": user.to_public_dict(),
                **_wheel_ui_meta(user),
            }
            from backend.items.wheel_extras import (
                chain_extra_item_wheel,
                finish_extra_wheel_chain,
                resume_reward_phase_if_pending,
            )

            extra = chain_extra_item_wheel(
                user,
                cell_name=cell.name,
                dice_label=dice_label,
                emit=_emit,
            )
            if extra:
                payload["openExtraWheel"] = True
                payload.update(
                    {
                        k: extra[k]
                        for k in (
                            "wheel",
                            "wheelItems",
                            "wheelType",
                            "source",
                            "cellName",
                            "extraWheelSpinsRemaining",
                        )
                        if k in extra
                    }
                )
            elif resume_reward_phase_if_pending(user):
                payload["resumeReward"] = True
                payload["rewardSpinsRemaining"] = int(user.pending_reward_spins or 0)
                payload["user"] = user.to_public_dict()
            else:
                restored = finish_extra_wheel_chain(user)
                payload["user"] = user.to_public_dict()
                if restored:
                    payload["restoredPhase"] = restored
            _emit("item_wheel_resolved", payload)
            return payload
        item_id = data.get("selectedItemId")
        if item_id is None:
            items = _pending_item_wheel.get(user.id, [])
            idx = data.get("targetIndex")
            if idx is not None and 0 <= int(idx) < len(items):
                item_id = items[int(idx)].get("id")
        if not item_id and data.get("targetIndex") is not None:
            items = _pending_item_wheel.get(user.id, [])
            idx = int(data["targetIndex"])
            if 0 <= idx < len(items):
                item_id = items[idx].get("id")
        if not item_id:
            return {"error": "Не выбран предмет"}, 400

        from backend.items.wheel import apply_wheel_result

        cell = BOARD_BY_ID[user.position]
        dice_label = str(data.get("diceLabel") or "?")

        result = apply_wheel_result(
            user,
            int(item_id),
            dice_label=dice_label,
            cell_name=cell.name,
        )
        if result.get("error"):
            return result, 400
        _pending_item_wheel.pop(user.id, None)
        _pending_spin.pop(user.id, None)
        payload = {
            **_user_payload(user),
            **result,
            "wheelType": "item",
            "user": user.to_public_dict(),
            **_wheel_ui_meta(user),
        }
        from backend.items.wheel_extras import (
            chain_extra_item_wheel,
            resume_reward_phase_if_pending,
        )

        extra = chain_extra_item_wheel(
            user,
            cell_name=cell.name,
            dice_label=dice_label,
            emit=_emit,
        )
        if extra:
            payload["openExtraWheel"] = True
            payload.update(
                {
                    k: extra[k]
                    for k in (
                        "wheel",
                        "wheelItems",
                        "wheelType",
                        "source",
                        "cellName",
                        "extraWheelSpinsRemaining",
                    )
                    if k in extra
                }
            )
        elif resume_reward_phase_if_pending(user):
            payload["resumeReward"] = True
            payload["rewardSpinsRemaining"] = int(user.pending_reward_spins or 0)
            payload["user"] = user.to_public_dict()
        else:
            from backend.items.wheel_extras import finish_extra_wheel_chain

            restored = finish_extra_wheel_chain(user)
            payload["user"] = user.to_public_dict()
            if restored:
                payload["restoredPhase"] = restored
        _emit("item_wheel_resolved", payload)
        return payload

    crown_pending = _pending_crown_pick.get(user.id)
    if crown_pending:
        ci = data.get("crownChoiceIndex")
        if ci is None:
            title_guess = str(data.get("selectedGame") or "").strip()
            if title_guess:
                for c in crown_pending.get("choices") or []:
                    if str(c.get("title") or "").strip() == title_guess:
                        ci = c.get("choiceIndex")
                        break
        if ci is None:
            return {"error": "Выберите одну из трёх игр под колесом"}, 400
        try:
            ci = int(ci)
        except (TypeError, ValueError):
            return {"error": "Некорректный выбор короны"}, 400
        choices = crown_pending.get("choices") or []
        picked = next((c for c in choices if c.get("choiceIndex") == ci), None)
        if not picked:
            return {"error": "Некорректный выбор короны"}, 400
        from backend.items.modifiers import _consume_mod, _has_mod

        for key in ("wheel_crown_pick", "wheel_crown"):
            crown_mod = _has_mod(user.id, key)
            if crown_mod:
                _consume_mod(crown_mod)
                break
        _pending_crown_pick.pop(user.id, None)
        title = str(picked.get("title") or "").strip()
    else:
        title = str(data.get("selectedGame") or "").strip()

    genre_id = data.get("genreId")
    if genre_id is None and src.get("genreId"):
        genre_id = src.get("genreId")

    from backend.items.admin_wheel import create_admin_stub_from_wheel, get_active_admin_wheel

    if get_active_admin_wheel(user.id):
        if not title:
            return {"error": "Не выбрана игра"}, 400
        cell_id = user.position
        gid = int(genre_id) if genre_id is not None else None
        stub = create_admin_stub_from_wheel(
            user,
            title,
            genre_id=gid,
            dice_label=str(data.get("diceLabel") or "?"),
            cell_id=cell_id,
        )
        _pending_wheel.pop(user.id, None)
        _pending_spin.pop(user.id, None)
        payload = {**_user_payload(user), **stub}
        _emit("game_assigned", payload)
        return payload

    cell_id = user.position
    if genre_id:
        src["genreId"] = int(genre_id)
    if not title and src.get("genreId"):
        title = game_lists.pick_one_for_cell("company", src["genreId"])
    if not title and src.get("question"):
        title = game_lists.pick_one_for_cell("question", None)
    if not title and src.get("trallalero"):
        title = game_lists.pick_one_for_cell("trallalero", None)
    if not title:
        if src.get("lottery"):
            return {"error": "Введите название игры"}, 400
        return {"error": "Не выбрана игра"}, 400

    from backend.services.game_history import player_has_game_title

    if player_has_game_title(user.id, title):
        return {"error": "Уже выпадало", "duplicateGame": True}, 400

    is_durka = user.in_durka or cell_id == DURKA_CELL_ID
    game = create_player_game(
        user,
        title,
        cell_id,
        str(data.get("diceLabel") or "?"),
        is_durka=is_durka,
        is_question=bool(src.get("question")),
        lottery_url=str(data.get("lotteryUrl") or ""),
    )
    from backend.items.gameplay import gameplay_tags_to_strings
    from backend.items.inventory import log_turn

    gp = gameplay_tags_to_strings(game._parse_gameplay_tags())
    factors = [f"Игра: {title}"]
    if gp:
        factors.append("Условия прохождения: " + "; ".join(gp))
    cell = BOARD_BY_ID[cell_id]
    log_turn(
        user.id,
        summary=f"Назначена игра: {title}",
        factors=factors,
        dice_label=str(data.get("diceLabel") or "?"),
        cell_name=cell.name,
        extra={"gameId": game.id, "gameplayTags": gp},
    )
    _pending_wheel.pop(user.id, None)
    _pending_spin.pop(user.id, None)
    payload = {
        **_user_payload(user),
        "game": game.to_dict(),
        "gameplayTags": gp,
        "user": user.to_public_dict(),
    }
    _emit("game_assigned", payload)
    return payload
