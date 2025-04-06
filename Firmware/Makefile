.PHONY: clean

RELEASE_DIR = release/
RELEASE_FILES = boot.py code.py moonclock_board.py text_display.py typing.py circuitpython_is_version_9.txt font5x8.bin
release: $(RELEASE_FILES) $(wildcard lib/**/*)
	mkdir -p $(RELEASE_DIR)
	for fname in $(RELEASE_FILES); do echo $$fname; cp -f $$fname $(RELEASE_DIR); done
	cp -R lib $(RELEASE_DIR)

clean:
	rm -rf $(RELEASE_DIR)
