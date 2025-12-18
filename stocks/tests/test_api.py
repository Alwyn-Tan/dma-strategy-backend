import pytest


@pytest.mark.django_db
def test_codes_endpoint_lists_csv_files(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    (tmp_path / "AAPL_3y.csv").write_text("Price,open,high,low,close,volume\n")
    (tmp_path / "MSFT.csv").write_text("date,open,high,low,close,volume\n")

    resp = client.get("/api/codes/")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)
    assert {item["code"] for item in payload} == {"AAPL", "MSFT"}


@pytest.mark.django_db
def test_signals_endpoint_returns_meta_and_desc_sort(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    # Minimal repo-style CSV; enough rows for MA windows.
    csv = (
        "Price,open,high,low,close,volume\n"
        "Ticker,AAPL,AAPL,AAPL,AAPL,AAPL\n"
        "Date,,,,,\n"
        "2025-01-01,1,1,1,1,100\n"
        "2025-01-02,1,1,1,1,100\n"
        "2025-01-03,1,1,1,10,100\n"
        "2025-01-04,1,1,1,10,100\n"
        "2025-01-05,1,1,1,10,100\n"
        "2025-01-06,1,1,1,1,100\n"
        "2025-01-07,1,1,1,1,100\n"
    )
    (tmp_path / "AAPL_3y.csv").write_text(csv)

    resp = client.get("/api/signals/?code=AAPL&short_window=2&long_window=3&filter_sort=desc")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["returned_count"] == len(body["data"])
    dates = [s["date"] for s in body["data"]]
    assert dates == sorted(dates, reverse=True)
