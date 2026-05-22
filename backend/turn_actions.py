"""Общая логика хода для HTTP и WebSocket."""

from __future__ import annotations

from flask import current_app

from backend.random_utils import randbelow

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


def _is_oops_wheel_item(item: dict) -> bool:
    try:
        if int(item.get("id") or 0) == 32:
            return True
    except (TypeError, ValueError):
        pass
    effect = str(item.get("effect") or "")
    return effect.split(":")[0].strip() == "oops_neighbor"


_pending_wheel: dict[int, list[str]] = {}
_pending_item_wheel: dict[int, list[dict]] = {}
_pending_dice_choice: dict[int, dict] = {}
_pending_crown_pick: dict[int, dict] = {}
_pending_oops_pick: dict[int, dict] = {}


def _socketio():
    return current_app.extensions["socketio"]


def _emit(event: str, payload: dict) -> None:
    _socketio().emit(event, payload, room="lobby", namespace="/")


def _user_payload(user: User, **extra) -> dict:
    return {"username": user.username, "userId": user.id, **extra}


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
    if choice:
        pending = {
            "d1": d1,
            "d2": d2,
            "label": label,
            **choice,
        }
        if choice.get("type") == "trinity":
            from backend.random_utils import randint

            d3 = randint(1, 6)
            pending["dice"] = [d1, d2, d3]
        _pending_dice_choice[user.id] = pending
        user.turn_phase = "dice_choice"
        db.session.commit()
        emit_choice = {"type": choice["type"]} if choice.get("type") else choice
        payload = {
            **_user_payload(user),
            "dice": [d1, d2],
            "needsDiceChoice": emit_choice,
            "user": user.to_public_dict(),
        }
        _emit("dice_rolled", payload)
        return payload

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
    from backend.items.modifiers import apply_dice_roll

    options = options or {}
    d1, d2, steps, label, move_meta, factors = apply_dice_roll(
        user, d1, d2, use_cheat=options
    )
    user.turn_phase = "rolling"
    db.session.commit()

    payload = {
        **_user_payload(user),
        "rawDice": move_meta.get("rawDice", [d1, d2]),
        "dice": [d1, d2],
        "steps": steps,
        "label": label,
        "fromPosition": user.position,
        "moveMeta": move_meta,
        "factors": factors,
        "user": user.to_public_dict(),
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
    )
    payload["user"] = user.to_public_dict()
    return payload


def _animate_and_finish(
    user_id: int,
    steps: int,
    label: str,
    move_meta: dict,
    factors: list,
    app,
) -> None:
    import time

    from backend.items.inventory import log_turn
    from backend.items.modifiers import build_move_path, tick_turn_modifiers

    time.sleep(2.2)
    step_delay = 0.72
    backward = bool(move_meta.get("backward"))

    with app.app_context():
        user = db.session.get(User, user_id)
        if not user or user.turn_phase != "rolling":
            return

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

        time.sleep(len(path) * step_delay + 0.2)

        bonus = apply_start_bonus(user, passed) if not user.in_durka and not backward else 0
        user.position = new_pos
        user.turn_phase = "wheel_ready"
        db.session.commit()

        tick_notes = tick_turn_modifiers(user.id)
        all_factors = list(factors) + tick_notes

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


def durka_roll_for_user(user: User) -> dict | tuple[dict, int]:
    err = require_phase(user, "durka")
    if err:
        return {"error": err}, 400
    if not user.in_durka and user.position != DURKA_CELL_ID:
        return {"error": "Вы не в дурке"}, 400

    gid = game_lists.blazerd_genre_roll()
    user.turn_phase = "wheel_ready"
    db.session.commit()

    _, src = _wheel_games_for_cell(DURKA_CELL_ID, gid)
    src["genreId"] = gid
    src["durka"] = True

    payload = {
        **_user_payload(user),
        "position": user.position,
        "passedStartBonus": 0,
        "diceLabel": "дурка",
        "user": user.to_public_dict(),
        "cell": {"id": DURKA_CELL_ID, "name": "Дурка", "type": "durka"},
        "source": src,
    }
    _emit("move_finished", payload)
    payload["user"] = user.to_public_dict()
    return payload


def _recovery_wheel_payload(user: User, src: dict) -> dict | None:
    """Восстановление UI колеса после перезагрузки страницы (фаза wheel)."""
    if user.turn_phase != "wheel":
        return None
    cell_name = BOARD_BY_ID[user.position].name
    if src.get("itemWheel"):
        items = _pending_item_wheel.get(user.id, [])
        if not items:
            return None
        wheel = [i.get("wheelLabel") or i.get("name") for i in items]
        return {
            **_user_payload(user),
            "wheel": wheel,
            "wheelType": "item",
            "wheelItems": items,
            "source": src,
            "cellName": cell_name,
            "recovered": True,
            "user": user.to_public_dict(),
        }
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
    oops_pending = _pending_oops_pick.get(user.id)
    if oops_pending:
        items = oops_pending.get("items") or []
        landed = oops_pending.get("landedIndex")
        landed_item = items[landed] if landed is not None and 0 <= landed < len(items) else {}
        payload["oopsPick"] = {
            "landedIndex": landed,
            "landedTitle": landed_item.get("name"),
            "choices": oops_pending.get("choices") or [],
        }
        payload["targetIndex"] = landed
        payload["wheelType"] = "item"
        payload["wheelItems"] = items
        payload["wheel"] = [
            i.get("wheelLabel") or i.get("name") for i in items
        ]
    return payload


def open_wheel_for_user(user: User, genre_id: int | None = None) -> dict | tuple[dict, int]:
    wheel, src = _wheel_games_for_cell(user.position, genre_id)
    recovered = _recovery_wheel_payload(user, src)
    if recovered:
        return recovered

    err = require_phase(user, "wheel_ready")
    if err:
        return {"error": err}, 400
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
        }
        _emit("wheel_opened", payload)
        payload["user"] = user.to_public_dict()
        return payload

    if src.get("needsGenrePick") and not genre_id:
        user.turn_phase = "wheel"
        db.session.commit()
        payload = {
            **_user_payload(user),
            "wheel": [],
            "source": src,
            "cellName": BOARD_BY_ID[user.position].name,
            "user": user.to_public_dict(),
        }
        _emit("wheel_opened", payload)
        payload["user"] = user.to_public_dict()
        return payload

    user.turn_phase = "wheel"
    _pending_wheel[user.id] = wheel
    db.session.commit()

    payload = {
        **_user_payload(user),
        "wheel": wheel,
        "source": src,
        "cellName": BOARD_BY_ID[user.position].name,
        "user": user.to_public_dict(),
    }
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
        from backend.items.wheel_pick import choices_for_items

        payload = {
            **_user_payload(user),
            "targetIndex": target_index,
            "wheelType": "item",
            "wheel": [i.get("wheelLabel") or i.get("name") for i in items],
            "wheelItems": items,
            "user": user.to_public_dict(),
        }
        if _is_oops_wheel_item(chosen):
            choices = choices_for_items(items, target_index, four=True)
            _pending_oops_pick[user.id] = {
                "landedIndex": target_index,
                "choices": choices,
                "items": items,
            }
            payload["oopsPick"] = {
                "landedIndex": target_index,
                "landedTitle": chosen.get("name"),
                "choices": choices,
            }
        else:
            payload["selectedItemId"] = chosen.get("id")
            payload["selectedItemName"] = chosen.get("name")
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

    payload = {
        **_user_payload(user),
        "targetIndex": target_index,
        "selectedGame": selected,
        "wheel": wheel,
        "user": user.to_public_dict(),
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

    _emit("wheel_spin", payload)
    payload["user"] = user.to_public_dict()
    return payload


def confirm_wheel_for_user(user: User, data: dict | None) -> dict | tuple[dict, int]:
    err = require_phase(user, "wheel")
    if err:
        return {"error": err}, 400

    data = data or {}
    from backend.reward_wheels import confirm_reward_wheel_for_user, is_reward_wheel

    if is_reward_wheel(user.id) or data.get("wheelType") == "reward_item":
        return confirm_reward_wheel_for_user(user, data, emit=_emit)

    src = cell_game_source(user.position)
    if src.get("itemWheel") or data.get("wheelType") == "item":
        oops_pending = _pending_oops_pick.get(user.id)
        if oops_pending:
            ci = data.get("oopsChoiceIndex")
            if ci is None:
                return {"error": "Выберите один из четырёх соседних пунктов"}, 400
            try:
                ci = int(ci)
            except (TypeError, ValueError):
                return {"error": "Некорректный выбор"}, 400
            choices = oops_pending.get("choices") or []
            picked = next((c for c in choices if c.get("choiceIndex") == ci), None)
            if not picked:
                return {"error": "Некорректный выбор"}, 400
            item_id = picked.get("itemId")
            if not item_id:
                return {"error": "Не выбран предмет"}, 400
            _pending_oops_pick.pop(user.id, None)
        else:
            item_id = data.get("selectedItemId")
            if item_id is None:
                items = _pending_item_wheel.get(user.id, [])
                idx = data.get("targetIndex")
                if idx is not None and 0 <= int(idx) < len(items):
                    landed = items[int(idx)]
                    if _is_oops_wheel_item(landed):
                        return {
                            "error": "«Ой, извините»: выберите один из четырёх соседних пунктов",
                        }, 400
                    item_id = landed.get("id")
            if item_id is not None:
                from backend.items.catalog import get_item

                landed_def = get_item(int(item_id))
                if landed_def and _is_oops_wheel_item(landed_def.to_dict()):
                    return {
                        "error": "«Ой, извините»: выберите один из четырёх соседних пунктов",
                    }, 400
            if not item_id:
                return {"error": "Не выбран предмет"}, 400

        from backend.items.wheel import apply_wheel_result

        cell = BOARD_BY_ID[user.position]
        result = apply_wheel_result(
            user,
            int(item_id),
            dice_label=str(data.get("diceLabel") or "?"),
            cell_name=cell.name,
        )
        if result.get("error"):
            return result, 400
        _pending_item_wheel.pop(user.id, None)
        payload = {
            **_user_payload(user),
            **result,
            "wheelType": "item",
            "user": user.to_public_dict(),
        }
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
    payload = {
        **_user_payload(user),
        "game": game.to_dict(),
        "gameplayTags": gp,
        "user": user.to_public_dict(),
    }
    _emit("game_assigned", payload)
    return payload
