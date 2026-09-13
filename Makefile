PYTHON ?= python3
BUILD_DIR ?= build
.DEFAULT_GOAL := all

.PHONY: all fetch data native prediction test packages speech clean
all: prediction
fetch:
	$(PYTHON) tools/fetch_sources.py
data: fetch
	$(PYTHON) tools/build_data.py
native:
	cmake -S . -B $(BUILD_DIR)/native -DCMAKE_BUILD_TYPE=Release
	cmake --build $(BUILD_DIR)/native --parallel 2
prediction: data native
	$(BUILD_DIR)/native/quick-hk-build-predict $(BUILD_DIR)/data/quick_hk.predict.db < $(BUILD_DIR)/data/quick_hk.predict.tsv
test:
	PYTHONPATH=src xvfb-run -a $(PYTHON) -m pytest -q
speech:
	$(PYTHON) tools/package_linux_speech.py
packages: all
	$(PYTHON) tools/package.py
clean:
	$(PYTHON) -c "import shutil; shutil.rmtree('$(BUILD_DIR)/native', ignore_errors=True)"
