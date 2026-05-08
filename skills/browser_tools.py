from playwright.async_api import async_playwright, Browser, Page


async def get_browser() -> Browser:
    """Launches a Playwright Chromium browser in headless mode."""
    playwright = await async_playwright().start()
    return await playwright.chromium.launch(headless=True)


async def get_page(browser: Browser, url: str) -> Page:
    """Opens a new page and navigates to url."""
    page = await browser.new_page()
    await page.goto(url, wait_until="networkidle")
    return page


async def fill_field(page: Page, selector: str, value: str) -> None:
    """Fills a form field identified by selector."""
    await page.fill(selector, value)


async def click(page: Page, selector: str) -> None:
    """Clicks an element. Only called after human approval."""
    await page.click(selector)


async def screenshot(page: Page, path: str) -> None:
    """Saves a screenshot of the current page for human review."""
    await page.screenshot(path=path, full_page=True)
