"""Action-id codec: every id decodes and fits the 64-byte callback_data budget."""

from __future__ import annotations

from app.bot import actions
from app.channels.base import CALLBACK_DATA_MAX


def test_all_actions_fit_callback_budget():
    for action in actions.all_actions():
        assert actions.is_valid(action), action
        assert len(action.encode("utf-8")) <= CALLBACK_DATA_MAX


def test_decode_round_trips_namespaced_ids():
    assert actions.decode("fx:cc:AED") == ("fx", ["cc", "AED"])
    assert actions.decode("hs:s:leo") == ("hs", ["s", "leo"])


def test_decode_rejects_unknown_or_empty():
    assert actions.decode("") is None
    assert actions.decode("bogus:x") is None
    assert actions.decode("nav") is None


def test_share_action_is_valid():
    assert actions.is_valid(actions.share("fx"))
