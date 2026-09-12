import os
import asyncio
import urllib.parse
from playwright.async_api import async_playwright

USER_DATA_DIR = os.path.abspath("./browser_session")
_playwright_instance = None
_context_instance = None

async def get_browser_context():
    """
    Maintains a persistent browser instance across tasks without crashing or closing.
    """
    global _playwright_instance, _context_instance
    if _context_instance is None:
        _playwright_instance = await async_playwright().start()
        _context_instance = await _playwright_instance.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",  # Uses your system's Google Chrome
            headless=False,
            slow_mo=300,
            args=["--start-maximized"]
        )
    return _context_instance

async def automate_calendar_schedule_and_save(title: str, start_time_iso: str = "", end_time_iso: str = "") -> dict:
    context = await get_browser_context()
    page = await context.new_page()

    encoded_title = urllib.parse.quote(title)
    dates_param = f"&dates={start_time_iso}/{end_time_iso}" if start_time_iso and end_time_iso else ""
    url = f"https://calendar.google.com/calendar/r/eventedit?text={encoded_title}{dates_param}"

    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")

    status = "Draft event displayed"
    try:
        save_btn = page.locator("button:has-text('Save'), div[role='button']:has-text('Save')").first
        await save_btn.wait_for(state="visible", timeout=3000)
        await save_btn.click()
        await asyncio.sleep(1)
        status = "Saved to Google Calendar"
    except Exception:
        status = "Event prefilled on screen (Sign in once to auto-save)"

    return {"action": "calendar_save", "title": title, "status": status}

async def automate_youtube_and_queue(video_query: str) -> dict:
    context = await get_browser_context()
    page = await context.new_page()

    encoded = urllib.parse.quote(video_query)
    await page.goto(f"https://www.youtube.com/results?search_query={encoded}")

    try:
        first_video = page.locator("ytd-video-renderer a#video-title").first
        await first_video.wait_for(state="visible", timeout=5000)
        await first_video.click()
        status = "Video queued and playing live"
    except Exception:
        status = "YouTube search loaded"

    return {"action": "youtube_queue", "query": video_query, "status": status}

async def automate_amazon_cart_addition(product_query: str) -> dict:
    context = await get_browser_context()
    page = await context.new_page()
    await page.goto("https://www.amazon.com")

    search_box = page.locator("#twotabsearchtextbox")
    await search_box.fill(product_query)
    await search_box.press("Enter")
    await page.wait_for_load_state("domcontentloaded")

    first_product = page.locator("div[data-component-type='s-search-result'] h2 a").first
    await first_product.click()
    await page.wait_for_load_state("domcontentloaded")

    try:
        cart_btn = page.locator("#add-to-cart-button").first
        await cart_btn.wait_for(state="visible", timeout=4000)
        await cart_btn.click()
        status = "Added to Amazon Cart"
    except Exception:
        status = "Navigated to product page"

    return {"action": "amazon_cart", "product": product_query, "status": status}