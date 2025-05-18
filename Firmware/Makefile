.PHONY: clean

RELEASE_DIR = release/
RELEASE_FILES = boot.py code.py moonclock_board.py circuitpython_is_version_9.txt
release: $(RELEASE_FILES) $(wildcard lib/**/*) $(wildcard tcv_astro/*.py) fonts/moonclock.bdf tcv_astro/table45.bin
	mkdir -p $(RELEASE_DIR)
	mkdir -p $(RELEASE_DIR)/tcv_astro
	mkdir -p $(RELEASE_DIR)/fonts
	cp $(RELEASE_FILES) $(RELEASE_DIR)
	cp -R lib $(RELEASE_DIR)
	cp -R tcv_astro/*.py $(RELEASE_DIR)/tcv_astro
	cp tcv_astro/table45.bin $(RELEASE_DIR)/tcv_astro
	cp fonts/moonclock.bdf $(RELEASE_DIR)/fonts

clean:
	rm -rf $(RELEASE_DIR)
