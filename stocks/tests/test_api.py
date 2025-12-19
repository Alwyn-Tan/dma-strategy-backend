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


@pytest.mark.django_db
def test_stock_data_include_meta_returns_meta_and_headers(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    csv = (
        "date,open,high,low,close,volume\n"
        "2025-01-01,1,1,1,1,100\n"
        "2025-01-02,1,1,1,2,100\n"
        "2025-01-03,1,1,1,3,100\n"
        "2025-01-04,1,1,1,4,100\n"
    )
    (tmp_path / "AAPL.csv").write_text(csv)

    resp = client.get(
        "/api/stock-data/?code=AAPL&short_window=2&long_window=3&end_date=2025-01-04&include_meta=true"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body and "meta" in body
    assert body["meta"]["data_status"] == "up_to_date"
    assert resp["X-Data-Status"] == "up_to_date"


@pytest.mark.django_db
def test_stock_data_include_performance_returns_series(client, settings, tmp_path):
    settings.DATA_DIR = tmp_path
    csv = (
        "date,open,high,low,close,volume\n"
        "2025-01-01,10,10,10,10,100\n"
        "2025-01-02,10,10,10,11,100\n"
        "2025-01-03,11,11,11,12,100\n"
        "2025-01-04,12,12,12,13,100\n"
    )
    (tmp_path / "AAPL.csv").write_text(csv)

    resp = client.get(
        "/api/stock-data/?code=AAPL&short_window=2&long_window=3&include_performance=true&end_date=2025-01-04"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body and "performance" in body
    assert len(body["performance"]["strategy"]) == len(body["data"])
