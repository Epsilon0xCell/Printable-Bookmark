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

# I keep the board URL in one place at the top because it is the only
# thing a user of this script is expected to change. If I scattered it
# through the functions, retargeting the script would mean hunting.
BOARD_URL = "https://www.pinterest.com/karenfrye376/printable-bookmarks/"

# Pinterest renames its CSS classes without notice. I treat this class
# name as a maintenance point, not a constant I can trust forever. It is
# the pin-link marker as the board markup had it when I wrote the script.
# When Pinterest changes it, I find no pins and I say so in main, instead
# of silently downloading nothing.
PIN_LINK_CLASS = "GrowthUnauthPinImage"

# I give every request a timeout. Without one, a stalled connection hangs
# the script forever with no message, which reads exactly like it working.
# I set it per request, not for the whole run, so a board with many pins
# can still take longer than 15 seconds in total without being cut off.
TIMEOUT = 15


def fetch(url):
    """GET one URL, or return None and say why it did not work."""
    # I return the whole response, not the content, because my two callers
    # both want the content and I want the status check in exactly one
    # place. I also keep the network error and the HTTP error as separate
    # messages, since they point at different fixes.
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
    # I strip the trailing slash before I take the last segment. Pin URLs
    # end in a slash, and an earlier version that skipped this step got an
    # empty name and crashed when it tried to write the file.
    # I add no extension here. I save the pin page bytes exactly as they
    # arrived, and guessing an extension would claim a format I never
    # checked.
    path = urlparse(url).path.rstrip("/")
    name = path.rsplit("/", 1)[-1]
    return name or "bookmark"


def download_printable_bookmark(url):
    response = fetch(url)
    if response is None:
        return False
    file_name = filename_for(url)
    # I write in binary mode and I do not decode first. If I opened this
    # as text, an encoding guess could corrupt a page that is not plain
    # text in the encoding I guessed.
    # One limit I know about: if two pins end in the same segment, the
    # second write overwrites the first with no warning, and my count in
    # the caller still goes up for both. I have not hit that on this
    # board, where pin ids differ, but I note it here so it is not a
    # surprise if a saved file ever seems to be missing.
    with open(file_name, "wb") as fh:
        fh.write(response.content)
    print(f"Downloaded bookmark: {file_name}")
    return True


def find_printable_bookmarks(board_url):
    """Download every pin linked from the board. Returns how many saved."""
    response = fetch(board_url)
    if response is None:
        return 0
    # I use the built in html.parser, not a faster parser, because it
    # comes with Python. That keeps my install list at the two packages
    # named at the top of this file.
    soup = BeautifulSoup(response.content, "html.parser")
    # Pin hrefs are relative paths, so I resolve them against the board
    # host instead of handing requests a path it cannot use on its own. I
    # hardcode the host here to match BOARD_URL above. If I ever point
    # this script at a board on a different host, I have to change both
    # places, or the relative links will resolve to the wrong site.
    saved = 0
    for pin in soup.find_all("a", {"class": PIN_LINK_CLASS}):
        href = pin.get("href")
        if not href:
            continue
        if href.startswith("/"):
            href = "https://www.pinterest.com" + href
        # I count only downloads that returned True. A failed pin already
        # printed its own reason inside fetch, so I do not repeat it here,
        # and I do not let it stop the pins after it.
        if download_printable_bookmark(href):
            saved += 1
    return saved


def main():
    saved = find_printable_bookmarks(BOARD_URL)
    if saved == 0:
        # Zero downloads used to mean I printed nothing at all, which is
        # indistinguishable from success. I say which thing most likely
        # happened: an empty board, or markup that no longer matches
        # PIN_LINK_CLASS. I return 1 so a caller or a script chaining off
        # this one can tell the run saved nothing.
        print("No bookmarks downloaded. Either the board is empty or "
              "Pinterest changed its page markup; check the board in a "
              "browser.")
        return 1
    print(f"Done: {saved} bookmark(s) downloaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
