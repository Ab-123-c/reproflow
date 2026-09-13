from reproflow.alpha5.history import HistoryStore, RunRecord, RunStatus


def test_history_round_trip(tmp_path) -> None:
    store = HistoryStore(tmp_path)
    record = RunRecord(
        run_id=store.next_run_id(),
        issue="unicode crash",
        status=RunStatus.VERIFIED,
        runs=3,
        successful_runs=3,
        score=96,
    )
    store.append(record)
    loaded = store.list()
    assert len(loaded) == 1
    assert loaded[0].status is RunStatus.VERIFIED
    assert loaded[0].score == 96
    assert store.next_run_id() == "002"
