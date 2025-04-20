.PHONY: clean

RELEASE_DIR = release/
RELEASE_FILES = boot.py code.py moonclock_board.py typing.py circuitpython_is_version_9.txt fonts/moonclock.bdf tcv_astro/table45.bin
release: $(RELEASE_FILES) $(wildcard lib/**/*) $(wildcard tcv_astro/*.py)
	mkdir -p $(RELEASE_DIR)
	for fname in $(RELEASE_FILES); do echo $$fname; cp -f $$fname $(RELEASE_DIR); done
	cp -R lib $(RELEASE_DIR)

clean:
	rm -rf $(RELEASE_DIR)
