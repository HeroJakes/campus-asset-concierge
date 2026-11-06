import pytest

from campus_asset_concierge.seed_demo import main


def test_seed_refuses_overwrite_unless_replace_is_explicit(local_app, capsys):
    _, store = local_app
    main(["spare_available", "--advance-minutes", "61"], store=store)
    saved = store.load()
    assert saved["scenario"] == "spare_available"
    assert saved["elapsed_minutes"] == 61
    assert saved["loans"]["active-projector"]["status"] == "active"
    with pytest.raises(SystemExit) as failure:
        main(["spare_unavailable"], store=store)
    assert failure.value.code == 1
    assert store.load() == saved
    main(["spare_unavailable", "--replace"], store=store)
    assert store.load()["scenario"] == "spare_unavailable"
    assert store.load()["elapsed_minutes"] == 0
    output = capsys.readouterr().out
    assert store.document.path in output
    assert "demo-campus-asset-concierge" in output


@pytest.mark.parametrize("args", [[], ["invalid"], ["spare_available", "--advance-minutes", "-1"],
                                  ["spare_available", "--advance-minutes", "1441"]])
def test_seed_rejects_invalid_arguments_without_writes(local_app, args):
    _, store = local_app
    with pytest.raises(SystemExit) as failure:
        main(args, store=store)
    assert failure.value.code == 2
    assert store.load() is None
