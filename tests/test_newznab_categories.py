import pytest

from mylar import helpers


@pytest.mark.parametrize('stored, expected', [
    ('', ('', '')),
    (None, ('', '')),
    ('12345', ('12345', '')),
    ('#7000', ('', '7000')),
    ('12345#7000#7030', ('12345', '7000,7030')),
])
def test_split(stored, expected):
    assert helpers.split_newznab_uid(stored) == expected


@pytest.mark.parametrize('uid, cats, stored', [
    ('', '7000', '#7000'),
    ('12345', '7000, 7030', '12345#7000#7030'),
    ('12345', '7000 7030', '12345#7000#7030'),
    ('12345', '', '12345'),
    ('', '', ''),
    # a User ID that still carries old '#' categories takes the field's categories instead
    ('12345#7030', '7000', '12345#7000'),
])
def test_join(uid, cats, stored):
    assert helpers.join_newznab_uid(uid, cats) == stored


def test_round_trip():
    stored = helpers.join_newznab_uid('abc', '7000,7030')
    assert helpers.join_newznab_uid(*helpers.split_newznab_uid(stored)) == stored
