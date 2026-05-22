"""Каждый предмет (1–48): использование и ожидаемый эффект."""

from __future__ import annotations

import pytest

from backend.items.catalog import get_item
from backend.items.effects import EffectContext, apply_item_effect
from backend.items.instant import apply_instant_wheel_effect
from backend.items.inventory import grant_inventory_item, has_item
from backend.items.use import use_inventory_item
from backend.models import PlayerGame, PlayerInventoryItem, PlayerModifier, User, db
from backend.services.turn_service import create_player_game

from backend.config import TRALLALERO_CELL_ID

from tests.conftest import grant_item, mod_keys, player, reset_player, use_item_api

TRAP_TARGETS = "zhenek"


def _ctx(user: User, item_id: int, **opts) -> EffectContext:
    item = get_item(item_id)
    assert item
    return EffectContext(
        user_id=user.id,
        item=item,
        actor_username=user.username,
        options=opts,
    )


def _instant(user: User, item_id: int, **opts) -> list[str]:
    ctx = _ctx(user, item_id, **opts)
    apply_instant_wheel_effect(ctx, user)
    return ctx.factors


def _use(user: User, item_id: int, **opts) -> dict:
    tid = None
    if opts.get("targetUsername"):
        t = User.query.filter_by(username=opts["targetUsername"]).first()
        tid = t.id if t else None
    if opts.get("targetUserId"):
        tid = int(opts["targetUserId"])
    result = use_inventory_item(
        user,
        item_id,
        target_user_id=tid,
        options=opts,
    )
    if isinstance(result, tuple):
        raise AssertionError(result[0])
    return result


@pytest.mark.parametrize("item_id,expected_mod", [
    (1, "cheat_dice_ready"),
    (2, "huubik_dice_ready"),
    (3, "ez_glasses"),
    (4, "rambo_band"),
    (8, "wheel_crown_pick"),
    (10, "reverse_boots"),
    (20, "totem_moshnya"),
])
def test_charge_buff_items(app, actor, item_id, expected_mod):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, item_id)
        _use(actor, item_id)
        assert expected_mod in mod_keys(actor.id)


def test_mutual_destroy_ez_rambo(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 3)
        grant_item(actor.id, 4)
        assert not has_item(actor.id, 3)
        assert not has_item(actor.id, 4)


def test_item_5_reroll_sets_wheel_ready(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_item(u.id, 5)
        create_player_game(u, "Test Game", u.position, "3+4")
        u.turn_phase = "playing"
        db.session.commit()
        _use(u, 5)
        u = player("andryuha")
        assert u.turn_phase == "wheel_ready"


def test_item_6_guide_orb(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 6)
        r = _use(actor, 6)
        assert r["ok"]


def test_traps_on_target(app, actor, second_player):
    with app.app_context():
        reset_player(actor)
        reset_player(second_player)
        cases = [
            (12, "trap_shawarma"),
            (14, "trap_choker"),
            (44, "trap_rake"),
            (45, "trap_slime"),
            (46, "trap_rat"),
        ]
        for iid, key in cases:
            grant_item(actor.id, iid)
            _use(actor, iid, targetUsername=second_player.username)
            assert key in mod_keys(second_player.id), f"item {iid}"

        grant_item(second_player.id, 3)
        grant_item(actor.id, 42)
        r = _use(actor, 42, targetUsername=second_player.username)
        assert not has_item(second_player.id, 3) or "Ржавчик" in " ".join(r.get("factors", []))


def test_trap_fisting_slave(app, actor, second_player):
    with app.app_context():
        reset_player(actor)
        reset_player(second_player)
        grant_item(actor.id, 19)
        _use(actor, 19, targetUsername=second_player.username)
        assert "slave" in mod_keys(second_player.id)


def test_trap_pig_eats_item(app, actor, second_player):
    with app.app_context():
        reset_player(actor)
        reset_player(second_player)
        grant_item(second_player.id, 6)
        grant_item(actor.id, 43)
        _use(actor, 43, targetUsername=second_player.username)
        assert not has_item(second_player.id, 6)


def test_four_leaf_modes(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        grant_item(u.id, 13)
        pts_before = u.points
        _use(u, 13, mode="block_trap")
        grant_item(u.id, 13)
        u.position = TRALLALERO_CELL_ID
        db.session.commit()
        _use(u, 13, mode="cell_bonus")
        u = player("andryuha")
        assert u.points >= pts_before + 2


def test_item_21_notebook_passive(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 21)
        _use(actor, 21)
        assert has_item(actor.id, 21)


def test_ez_attaches_to_game(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 3)
        _use(actor, 3)
        game = create_player_game(actor, "EZ Game", actor.position, "2+3")
        tags = game._parse_gameplay_tags()
        assert any("EZ" in str(t.get("label", t)) for t in tags)
        assert "ez_glasses" in mod_keys(actor.id)
        from backend.items.gameplay import tick_buffs_after_game

        tick_buffs_after_game(actor.id)
        assert "ez_glasses" not in mod_keys(actor.id)


@pytest.mark.parametrize(
    "item_id,key",
    [
        (22, "wheel_ready"),
        (23, "wheel_ready"),
        (24, None),
        (25, None),
        (26, None),
        (27, None),
        (28, None),
        (29, "wheel_extra_spins"),
        (30, "wheel_extra_spins"),
        (31, None),
        (32, None),
        (33, None),
        (34, "help_laggard"),
        (35, "lucky_loser"),
        (36, "hurry"),
        (37, "trinity_dice"),
        (38, "coin_dice"),
        (39, None),
        (40, "chat_law"),
        (41, "i_am_law"),
        (47, "base_only_next"),
        (48, "hour_growth"),
    ],
)
def test_wheel_instant_items(app, actor, item_id, key):
    with app.app_context():
        reset_player(actor)
        item = get_item(item_id)
        assert item and item.kind == "none"
        factors = _instant(actor, item_id)
        assert factors
        if key == "wheel_ready":
            assert actor.turn_phase == "wheel_ready"
        elif key:
            assert key in mod_keys(actor.id)


def test_bandit_clears_inventory(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 6)
        grant_item(actor.id, 7)
        _instant(actor, 26)
        rows = PlayerInventoryItem.query.filter_by(user_id=actor.id).all()
        assert sum(r.quantity for r in rows) == 0
        assert "wheel_extra_spins" in mod_keys(actor.id)


def test_dirtykin_eats_buff(app, actor):
    with app.app_context():
        reset_player(actor)
        grant_item(actor.id, 3)
        _instant(actor, 27)
        assert not has_item(actor.id, 3)


def test_swap_inventories(app):
    with app.app_context():
        from backend.items import inventory as inv

        u = player("andryuha")
        other = player("zhenek")
        reset_player(u)
        reset_player(other)
        grant_item(u.id, 3, 1)
        grant_item(other.id, 6, 1)
        inv.swap_inventories(u.id, other.id)
        assert has_item(u.id, 6)
        assert has_item(other.id, 3)


def test_instant_swap_inv_random(app):
    with app.app_context():
        from unittest.mock import patch

        u = player("andryuha")
        other = player("zhenek")
        reset_player(u)
        reset_player(other)
        grant_item(u.id, 3)
        grant_item(other.id, 6)
        others = User.query.filter(
            User.is_player == True, User.id != u.id
        ).all()
        with patch("backend.items.instant.choice", lambda xs: other):
            factors = _instant(u, 33)
        assert has_item(u.id, 6)
        assert "Mine now" in " ".join(factors) or "обмен" in " ".join(factors).lower()


def test_first_aid_modes(app):
    with app.app_context():
        u = player("andryuha")
        reset_player(u)
        from backend.items.modifiers import _add_mod

        _add_mod(u.id, "hurry", "1", 1, polarity="debuff", label="Торопыга")
        pts = u.points
        _instant(u, 31, mode="drop_debuff")
        u = player("andryuha")
        assert u.points == pts - 1
        assert "hurry" not in mod_keys(u.id)


def test_api_use_all_inventory_items(app, player_client, actor, second_player):
    """HTTP: каждый предмет kind=item успешно отрабатывает или даёт понятную ошибку."""
    with app.app_context():
        reset_player(actor)
        for iid in range(1, 22):
            item = get_item(iid)
            if not item or item.kind != "item":
                continue
            grant_item(actor.id, iid)
            body = {"itemId": iid}
            if item.kind == "trap" or item.effect.startswith("trap_"):
                body["targetUsername"] = second_player.username
            if iid == 11:
                body["partnerUsername"] = second_player.username
            if iid == 9:
                grant_item(actor.id, 6)
                body["targetItemId"] = 6
            if iid == 13:
                body["mode"] = "block_trap"
            if item.kind == "trap":
                body["targetUsername"] = second_player.username
            r = player_client.post("/api/inventory/use", json=body)
            assert r.status_code == 200, (iid, r.get_json())


def test_catalog_effect_handlers_exist(app):
    """У каждого предмета есть обработчик (не заглушка «уточните»)."""
    with app.app_context():
        user = User.query.filter_by(username="andryuha").first()
        for iid in range(1, 49):
            item = get_item(iid)
            ctx = _ctx(user, iid, targetUsername="zhenek", partnerUsername="zhenek")
            apply_item_effect(ctx, user, db)
            assert ctx.factors
            assert "уточните реализацию" not in " ".join(ctx.factors).lower()
