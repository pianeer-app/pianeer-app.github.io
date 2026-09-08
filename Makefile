# Pianeer site. No build step — these are checks and a local preview.

.PHONY: check serve

## Validate structure, links, anchors, assets and shared chrome.
check:
	@python3 tools/check.py

## Preview the site at http://localhost:8000
serve:
	@python3 -m http.server 8000
