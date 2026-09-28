.PHONY: install run demo test clean

install:
	python -m pip install -e .

run:
	python -m hotspot_radar.cli run

demo:
	python -m hotspot_radar.cli run --fixture tests/fixtures/articles.json --database data/demo.duckdb

test:
	python -m unittest discover -s tests -v

clean:
	rm -f data/*.duckdb data/*.duckdb.wal

