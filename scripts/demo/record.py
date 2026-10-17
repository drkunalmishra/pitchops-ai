"""Drive the live site in Chrome (Playwright, your installed Chrome, persistent profile) and capture crisp frames over
the DevTools screencast. Each 'rec' scene lasts exactly its narration length + padding (from audio/durations.json).

  python record.py --login   # opens Chrome; YOU sign in once, then close the window
  python record.py           # records; writes rec/frames/*.jpg + rec/timeline.json
"""
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from scenes import DATA, SCENES, SITE  # noqa: E402

PROFILE = DATA / ".chrome-profile"
OUT = DATA / "rec"
VIEW = {"width": 1600, "height": 900}
DSF = 1.2  # 1600x900 CSS → 1920x1080 frames, larger readable text
PAD = 1.8  # seconds of hold after each narration

CURSOR = """
(() => { const add = () => { if (document.getElementById('__cur')) return;
  const c = document.createElement('div'); c.id='__cur';
  c.style.cssText='position:fixed;left:-50px;top:-50px;width:22px;height:22px;border-radius:50%;'+
   'background:rgba(255,255,255,.85);border:3px solid #14b8a6;box-shadow:0 0 0 4px rgba(20,184,166,.25);'+
   'z-index:2147483647;pointer-events:none;transform:translate(-50%,-50%);transition:width .1s,height .1s';
  document.documentElement.appendChild(c);
  addEventListener('mousemove', e => { c.style.left=e.clientX+'px'; c.style.top=e.clientY+'px'; }, true);
  addEventListener('mousedown', () => { c.style.width=c.style.height='30px'; }, true);
  addEventListener('mouseup', () => { c.style.width=c.style.height='22px'; }, true); };
  if (document.readyState !== 'loading') add(); else addEventListener('DOMContentLoaded', add); })();
"""


class Tour:
    def __init__(self, page):
        self.p = page
        self.mx, self.my = 800, 450

    async def go(self, path, settle=2.5):
        await self.p.goto(SITE + path, wait_until="networkidle")
        await asyncio.sleep(settle)

    async def move(self, x, y, steps=25):
        await self.p.mouse.move(x, y, steps=steps)
        self.mx, self.my = x, y

    async def hover_el(self, loc, steps=25):
        box = await loc.bounding_box()
        if box:
            await self.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps)
        return box

    async def click(self, loc, pause=0.6):
        try:
            await loc.scroll_into_view_if_needed(timeout=3000)
            if await self.hover_el(loc):
                await asyncio.sleep(0.25)
                await loc.click(timeout=5000)
                await asyncio.sleep(pause)
                return True
        except Exception as e:  # keep recording even if a selector misses
            print("  click miss:", str(e).splitlines()[0][:120])
        return False

    async def scroll(self, px, secs=2.0):
        n = max(int(secs * 20), 1)
        for _ in range(n):
            await self.p.mouse.wheel(0, px / n)
            await asyncio.sleep(secs / n)

    # ---- scene actions -------------------------------------------------------------------------------------------
    async def overview_top(self):
        await self.go("/dashboard/")
        await self.move(300, 300)
        await asyncio.sleep(2)
        await self.move(1250, 230, 40)

    async def overview_funnel(self):
        rows = self.p.get_by_text("DLD registered brokers")
        await self.hover_el(rows)
        for label in ["YouTube channels matched", "Videos harvested", "Relevant videos, last 24 months",
                      "Deep-analysed", "Comments collected"]:
            await asyncio.sleep(2.2)
            await self.hover_el(self.p.get_by_text(label).first, 20)

    async def personas(self):
        await self.go("/personas/")
        await self.move(700, 400)
        await asyncio.sleep(1.5)
        await self.click(self.p.get_by_role("radio", name="Median trending"), 1.5)
        await self.click(self.p.get_by_role("radio", name="Video count"), 1.0)
        cell = self.p.get_by_role("button", name="Luxury Status by Hnw Uhnw Investor")
        if not await cell.count():
            cell = self.p.locator("td button").filter(has_text="7k")
        await self.click(cell.first, 1.5)
        await self.scroll(650, 2.5)

    async def overview_long(self):
        await self.overview_top()
        await self.overview_funnel()
        for label in ["Top seller persona", "Top buyer persona", "Most-discussed project", "Avg sales pressure"]:
            await asyncio.sleep(1.8)
            await self.hover_el(self.p.get_by_text(label, exact=False).first, 20)

    async def personas_long(self):
        await self.personas()
        await asyncio.sleep(2)
        await self.scroll(500, 3)
        await asyncio.sleep(1.5)
        await self.p.mouse.wheel(0, -3000)
        await asyncio.sleep(1)
        cell = self.p.locator("td button").filter(has_text="4.6k").first
        await self.click(cell, 1.5)
        await self.scroll(700, 3)

    async def company_long(self):
        await self.go("/companies/", 1.5)
        for i in range(4):
            await self.hover_el(self.p.locator("a[href*='/company/']").nth(i), 15)
            await asyncio.sleep(0.6)
        await self.click(self.p.get_by_role("link", name="PALLADIUM REALTY REAL ESTATE L.L.C").first, 2.5)
        await self.hover_el(self.p.get_by_text("Persona statement", exact=False).first, 25)
        await asyncio.sleep(2)
        await self.hover_el(self.p.get_by_text("Download Markdown").first, 25)
        await asyncio.sleep(1.5)
        await self.scroll(600, 4)

    async def _persona_tab(self, label, scroll_px):
        if "/personas" not in self.p.url:
            await self.go("/personas/", 2)
        tab = self.p.get_by_role("tab", name=label)
        await self.click(tab, 1.5)
        cards = self.p.locator("[role=tabpanel] > *")
        for i in range(3):
            await self.hover_el(cards.nth(i), 20)
            await asyncio.sleep(1.4)
        await self.scroll(scroll_px, 4)
        for i in range(6, 9):
            if await cards.nth(i).count():
                await self.hover_el(cards.nth(i), 20)
                await asyncio.sleep(1.2)

    async def persona_tab_seller(self):
        await self.go("/personas/", 2)
        await self._persona_tab("Seller personas", 500)

    async def persona_tab_buyer(self):
        await self.p.mouse.wheel(0, -900)
        await asyncio.sleep(0.8)
        await self._persona_tab("Buyer personas", 600)

    async def company(self):
        await self.go("/companies/", 1.5)
        await self.click(self.p.get_by_role("link", name="PALLADIUM REALTY REAL ESTATE L.L.C").first, 2.5)
        await self.hover_el(self.p.get_by_text("Download Markdown").first, 30)
        await asyncio.sleep(1.5)
        await self.scroll(500, 3)

    async def properties(self):
        await self.go("/properties/", 2)
        await self.scroll(250, 1.5)
        await self.click(self.p.locator("a[href*='/property/']").first, 2.5)
        await self.scroll(450, 2)

    async def studio(self):
        await self.go("/studio/", 2)
        await self.move(600, 420, 30)
        await asyncio.sleep(1)
        await self.hover_el(self.p.get_by_text("PASS").nth(2), 30)

    async def compliance(self):
        await self.click(self.p.get_by_text("Guaranteed returns? (compliance demo)").first, 2.5)
        await self.click(self.p.get_by_role("button", name="Run compliance"), 4)
        await self.hover_el(self.p.get_by_text("UAE-CLAIM-002").first, 30)
        await asyncio.sleep(2)
        await self.scroll(300, 1.5)
        await self.p.mouse.wheel(0, -2000)
        await asyncio.sleep(0.8)
        if await self.click(self.p.get_by_role("button", name="Edit"), 1.5):
            await self.click(self.p.get_by_role("button", name="Regenerate line").first, 0.5)
            for _ in range(30):  # wait for Gemini's rewrite to land
                await asyncio.sleep(0.5)
                if not await self.p.get_by_text("Regenerating").count():
                    break
            await asyncio.sleep(2.5)
            await self.click(self.p.get_by_role("button", name="Cancel"), 1)  # discard: nothing is saved
        await self.hover_el(self.p.get_by_role("button", name="Approve"), 30)

    async def media(self):
        await self.go("/media/", 1.5)
        await self.hover_el(self.p.get_by_text("Media budget", exact=False).first, 20)
        await asyncio.sleep(1.0)
        await self.scroll(350, 1.5)
        await self.go("/avatars/", 1.2)
        await self.scroll(500, 2)

    async def plan(self):
        await self.go("/plan/?id=plan_bugatti_residences_16x9_status_luxury", 1.0)
        await self.hover_el(self.p.locator("video").first, 30)

    async def finops(self):
        await self.go("/finops/", 2.5)
        await self.move(400, 260, 30)
        await asyncio.sleep(1.5)
        await self.scroll(450, 2.5)
        await self.move(1100, 500, 30)


async def login():
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(PROFILE, channel="chrome", headless=False, viewport=VIEW)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(SITE)
        print("Sign in in the Chrome window. Waiting for the dashboard…")
        for _ in range(900):
            if "/dashboard" in page.url:
                print("signed in — profile saved")
                await asyncio.sleep(2)
                break
            await asyncio.sleep(1)
        await ctx.close()


async def record():
    durs = json.loads((DATA / "audio" / "durations.json").read_text())
    frames_dir = OUT / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for f in frames_dir.glob("*.jpg"):
        f.unlink()
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(PROFILE, channel="chrome", headless=False, viewport=VIEW,
                                                          device_scale_factor=DSF)
        await ctx.add_init_script(CURSOR)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        tour = Tour(page)
        await page.goto(SITE + "/dashboard/", wait_until="networkidle")
        await asyncio.sleep(3)
        if "/dashboard" not in page.url:
            raise SystemExit("not signed in — run: python record.py --login")
        cdp = await ctx.new_cdp_session(page)
        frames: list[tuple[float, str]] = []

        async def on_frame(ev):
            n = len(frames)
            name = f"{n:06d}.jpg"
            (frames_dir / name).write_bytes(base64.b64decode(ev["data"]))
            frames.append((time.monotonic(), name))
            await cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

        cdp.on("Page.screencastFrame", lambda ev: asyncio.ensure_future(on_frame(ev)))
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920,
                                                "maxHeight": 1080, "everyNthFrame": 1})
        t0 = time.monotonic()
        marks = []
        for s in SCENES:
            if s["kind"] != "rec":
                continue
            target = durs[s["id"]] + PAD
            start = time.monotonic()
            print(f"{s['id']}: {target:.1f}s")
            await getattr(tour, s["action"])()
            left = target - (time.monotonic() - start)
            if left > 0:
                # gentle idle motion so the hold doesn't look frozen
                await tour.move(tour.mx + 30, tour.my + 15, max(int(left * 10), 1))
                await asyncio.sleep(max(target - (time.monotonic() - start), 0))
            else:
                print(f"  ⚠ actions overran narration by {-left:.1f}s")
            marks.append({"id": s["id"], "start": start - t0, "end": time.monotonic() - t0})
        await cdp.send("Page.stopScreencast")
        await asyncio.sleep(0.5)
        await ctx.close()
    (OUT / "timeline.json").write_text(json.dumps({"frames": [(t - t0, n) for t, n in frames], "scenes": marks},
                                                  indent=0))
    print(f"{len(frames)} frames, {marks[-1]['end']:.1f}s recorded")


if __name__ == "__main__":
    asyncio.run(login() if "--login" in sys.argv else record())
