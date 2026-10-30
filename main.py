"""Download the pin pages linked from one Pinterest board.

The board this was written for collects printable bookmarks. The script
reads the board page, follows every pin link it finds, and saves each pin
page into the current folder under the last part of its URL.

Run it with:  python3 main.py
Requires:     requests, beautifulsoup4  (pip install requests beautifulsoup4)
"""
import sys

import requests
from bs4 import BeautifulSoup

# The board URL lives in one place at the top because it is the only thing
# a user of this script is expected to change.
BOARD_URL = "https://www.pinterest.com/karenfrye376/printable-bookmarks/"

# Pinterest renames its CSS classes without notice. This class name is the
# pin-link marker as the board's markup had it when the script was written;
# when Pinterest changes it, the script finds no pins and says so (see
# main), instead of silently downloading nothing.
PIN_LINK_CLASS = "GrowthUnauthPinImage"

# Every request gets a timeout. Without one, a stalled connection hangs
# the script forever with no message, which reads exactly like it working.
TIMEOUT = 15


def fetch(url):
    """GET one URL, or return None and say why it did not work."""
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"Could not load {url}: {exc}")
        return None
    if response.status_code != 200:
        print(f"Could not load {url}: HTTP {response.status_code}")
        return None
    return response


def filename_for(url):
    """Last path segment of the URL, made safe to use as a file name.

    Pin hrefs can be relative ("/pin/123/") or carry a query string, so the
    URL is parsed properly instead of split by hand: urlparse separates the
    host from the path, which a plain split cannot (for a board-root URL it
    would happily return the domain name as the "file" name). The "or"
    guard covers a URL whose path is empty.
    """
    from urllib.parse import urlparse
    path = urlparse(url).path.rstrip("/")
    name = path.rsplit("/", 1)[-1]
    return name or "bookmark"


def download_printable_bookmark(url):
    response = fetch(url)
    if response is None:
        return False
    file_name = filename_for(url)
    with open(file_name, "wb") as fh:
        fh.write(response.content)
    print(f"Downloaded bookmark: {file_name}")
    return True


def find_printable_bookmarks(board_url):
    """Download every pin linked from the board. Returns how many saved."""
    response = fetch(board_url)
    if response is None:
        return 0
    soup = BeautifulSoup(response.content, "html.parser")
    # Pin hrefs are relative paths, so resolve them against the board URL
    # instead of handing requests a path it cannot use on its own.
    saved = 0
    for pin in soup.find_all("a", {"class": PIN_LINK_CLASS}):
        href = pin.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.pinterest.com" + href
        if download_printable_bookmark(href):
            saved += 1
    return saved


def main():
    saved = find_printable_bookmarks(BOARD_URL)
    if saved == 0:
        # Zero downloads used to mean the script printed nothing at all,
        # which is indistinguishable from success. Say which thing happened:
        # an empty board, or markup that no longer matches PIN_LINK_CLASS.
        print("No bookmarks downloaded. Either the board is empty or "
              "Pinterest changed its page markup; check the board in a "
              "browser.")
        return 1
    print(f"Done: {saved} bookmark(s) downloaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
