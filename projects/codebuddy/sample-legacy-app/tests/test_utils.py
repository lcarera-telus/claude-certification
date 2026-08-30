"""Tests for the helpers in utils.py."""

import utils


def test_round_money_rounds_to_two_decimals():
    assert utils.round_money(19.996) == 20.0


def test_slugify_replaces_spaces_with_hyphens():
    assert utils.slugify("Spring Sale Quote") == "spring-sale-quote"
