import argparse
import os
import time
from urllib.parse import quote_plus

from patchright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PAGELOAD_TIMEOUT_SECS = 10
STATE_FILE            = "mouser_auth.json"
OUTPUT_DIR            = "output"


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Mouser search results and download CSVs."
    )
    parser.add_argument(
        "list_file",
        nargs="?",
        default="external_memory_devices.txt",
        help="Text file with keywords.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Seconds to wait between requests.",
    )
    parser.add_argument(
        "--all-stock",
        action="store_true",
        help="Include out-of-stock parts.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show the browser window on screen for debugging.",
    )

    args = parser.parse_args()

    if not os.path.exists(args.list_file):
        print(f"Error: '{args.list_file}' not found.")
        return

    with open(args.list_file, "r", encoding="utf-8") as f:
        keywords = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Found {len(keywords)} keywords to process.\n")

    in_stock = not args.all_stock
    normally_stocked = not args.all_stock

    if args.debug:
        window_pos = "0,0"

        if os.path.exists(STATE_FILE):
            os.unlink(STATE_FILE)
    else:
        window_pos = "-32000,-32000"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                f"--window-position={window_pos}",
                "--window-size=1920,1080",
            ],
        )

        context_args = {
            "accept_downloads": True,
            "viewport": {"width": 1920, "height": 1080},
        }

        if os.path.exists(STATE_FILE):
            context_args["storage_state"] = STATE_FILE
            skip_homepage = True
        else:
            skip_homepage = False

        context = browser.new_context(**context_args)
        page = context.new_page()

        if not skip_homepage:
            print("-> Visiting homepage to generate session...")

            try:
                response = page.goto(
                    "https://www.mouser.com/",
                    wait_until="domcontentloaded",
                )

                if response and response.status >= 400:
                    print(
                        f"   Homepage returned HTTP {response.status}."
                    )

                    if not args.debug:
                        print(
                            "   -> Run 'make debug' to refresh your session."
                        )
                        browser.close()
                        return

                is_blocked = (
                    "Access Denied" in page.title()
                    or "Just a moment" in page.title()
                    or "403" in page.title()
                )

                while is_blocked:
                    print(
                        f"   Blocked! Status: "
                        f"{response.status if response else 'N/A'} | "
                        f"Title: {page.title()}"
                    )

                    if not args.debug:
                        print(
                            "   -> CAPTCHA detected in hidden window! "
                            "Run 'make debug' to see and solve it."
                        )
                        browser.close()
                        return

                    print("\n   *** MANUAL INTERVENTION REQUIRED ***")
                    input(
                        "   Press ENTER here ONLY when you see "
                        "the REAL Mouser homepage... "
                    )

                    is_blocked = (
                        "Access Denied" in page.title()
                        or "403" in page.title()
                        or "mouser" not in page.url.lower()
                    )

                context.storage_state(path=STATE_FILE)
                print("   Session saved successfully.\n")

            except Exception as e:
                print(f"   Homepage failed: {e}")
                browser.close()
                return

        else:
            print("-> Session loaded. Skipping homepage.\n")

        success_count = 0

        for i, kw in enumerate(keywords):
            print(f"--- Fetching: '{kw}' ---")

            params = f"q={quote_plus(kw)}"

            if in_stock:
                params += "&instock=y"

            if normally_stocked:
                params += "&normallystocked=y"

            params += "&sort=pricing&qty=1000"

            search_url = (
                f"https://www.mouser.com/en/c/semiconductors/?{params}"
            )

            try:
                # Do not wait for the page to finish loading.
                # Mouser can keep network requests open for a long time.
                response = page.goto(
                    search_url,
                    wait_until="commit",
                )

                print(
                    f"[{os.path.basename(__file__)}] "
                    f"Search URL: {search_url}"
                )

                if response and response.status >= 400:
                    print(
                        f"  -> Error: Status {response.status}. "
                        f"Session likely expired."
                    )

                    if not args.debug:
                        print(
                            "  -> Run 'make debug' to refresh your session."
                        )

                    continue

                # ----------------------------------------------------------
                # DOWNLOAD BUTTON
                #
                # This is the only signal used to determine whether the
                # search has produced downloadable results.
                #
                # Do not wait for the page itself to finish loading.
                # Instead, check for the button every 500 ms.
                # ----------------------------------------------------------

                download_btn = page.locator("#btnDownloadResults")

                print("  -> Waiting for download button...")

                deadline = time.monotonic() + PAGELOAD_TIMEOUT_SECS

                while time.monotonic() < deadline:
                    try:
                        if download_btn.is_visible():
                            print("  -> Download button found.")
                            break

                    except Exception:
                        pass

                    time.sleep(0.5)

                else:
                    print(
                        "  -> Download button did not appear within "
                        f"{PAGELOAD_TIMEOUT_SECS} seconds. "
                        f"No downloadable results for '{kw}'."
                    )
                    continue

                # ----------------------------------------------------------
                # DOWNLOAD
                # ----------------------------------------------------------

                try:
                    with page.expect_download() as download_info:
                        download_btn.click()

                    download = download_info.value

                    safe_filename = os.path.join(
                        OUTPUT_DIR,
                        kw.replace(" ", "_") + ".csv",
                    )

                    download.save_as(safe_filename)

                    print(
                        f"  -> Success! Saved to {safe_filename}"
                    )

                    success_count += 1

                except PlaywrightTimeout:
                    print("  -> Download timed out.")

                except Exception as e:
                    print(f"  -> Download error: {e}")

            except PlaywrightTimeout:
                print(
                    "  -> Navigation timed out before reaching the "
                    "search page."
                )

            except Exception as e:
                print(f"  -> Error: {e}")

            # Intentional request-rate limit.
            if args.delay > 0 and i < len(keywords) - 1:
                time.sleep(args.delay)

        browser.close()

        print(
            f"\n=== Finished! Successfully downloaded "
            f"{success_count}/{len(keywords)} CSVs. ==="
        )


if __name__ == "__main__":
    main()
