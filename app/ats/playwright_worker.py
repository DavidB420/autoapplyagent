from pathlib import Path
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

class BrowserWorker:
    def __init__(self):
        self._playwright: Playwright | None = None
        self.context: BrowserContext | None = None

    async def start(self):
        self._playwright = await async_playwright().start()
        profile = Path("./browser-profile")
        profile.mkdir(parents=True, exist_ok=True)
        self.context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=True,
            args=["--disable-dev-shm-usage"],
        )

    async def stop(self):
        if self.context:
            await self.context.close()
        if self._playwright:
            await self._playwright.stop()
        self.context = None
        self._playwright = None

    async def open(self, url: str):
        if not self.context:
            raise RuntimeError("Browser worker is not started")
        page = await self.context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        return page
