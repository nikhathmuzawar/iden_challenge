import json
import time
import asyncio
import signal
import sys
from playwright.async_api import async_playwright
import threading

class OptimizedScraper:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.data = []
        self.data_lock = threading.Lock()
        self.setup_signal_handler()
        
    def setup_signal_handler(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        print("\nKeyboard interrupt detected! Saving extracted data...")
        self.save_data_on_interrupt()
        print("Data saved. Exiting gracefully.")
        sys.exit(0)
        
    def save_data_on_interrupt(self):
        if self.data:
            filename = f"products_interrupted_{int(time.time())}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(self.data)} rows to {filename}")
        else:
            print("No data to save.")
        
    async def login_and_save_session(self, page):
        await page.goto("https://hiring.idenhq.com/")
        await page.wait_for_selector("input#email")
        await page.fill("input#email", self.email)
        await page.fill("input#password", self.password)
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")

    async def navigate_to_products(self, page):
        await page.goto("https://hiring.idenhq.com/instructions")
        await page.wait_for_selector("text=Launch Challenge")
        await page.click("text=Launch Challenge")
        await page.wait_for_url("**/challenge")
        await page.click("text=Open Dashboard Menu")
        await page.click("text=Data Tools")
        await page.click("text=Data Tools")
        await page.click("text=Inventory Options")
        await page.click("text=Open Products Drawer")
        await page.get_by_role("button", name="Open Products Drawer").click()
        await page.wait_for_selector("div.space-y-2 div.flex.flex-col")

    async def smart_scroll_and_extract(self, page):
        await page.wait_for_selector("div.space-y-2")
        
        scroll_position = 0
        scroll_increment = 1000
        processed_rows = set()
        batch_size = 100
        
        viewport_height = await page.evaluate("window.innerHeight")
        
        try:
            while True:
                await page.evaluate(f"window.scrollTo(0, {scroll_position})")
                scroll_position += scroll_increment
                
                try:
                    await page.wait_for_load_state("networkidle", timeout=1000)
                except:
                    await asyncio.sleep(0.5)
                
                rows = await page.query_selector_all("div.space-y-2 > div.flex.flex-col")
                current_count = len(rows)
                
                new_rows = rows[len(processed_rows):]
                if new_rows:
                    batch_data = await self.extract_batch_data(new_rows[:batch_size])
                    with self.data_lock:
                        self.data.extend(batch_data)
                        processed_rows.update(range(len(processed_rows), len(processed_rows) + len(batch_data)))
                
                print(f"Processed: {len(self.data)} rows, Current DOM: {current_count}")
                
                if len(new_rows) == 0:
                    for _ in range(3):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(0.3)
                        new_rows_check = await page.query_selector_all("div.space-y-2 > div.flex.flex-col")
                        if len(new_rows_check) > current_count:
                            break
                    else:
                        break
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)
        
        return self.data

    async def extract_batch_data(self, rows):
        batch_data = []
        
        for row in rows:
            try:
                row_text = await row.evaluate("""
                    (element) => {
                        const cells = element.querySelectorAll('div');
                        return Array.from(cells)
                            .map(cell => cell.innerText?.trim())
                            .filter(text => text && text.length > 0);
                    }
                """)
                
                if row_text:
                    batch_data.append(row_text)
            except Exception as e:
                print(f"Error extracting row: {e}")
                continue
                
        return batch_data

    async def parallel_extraction(self, page):
        await page.wait_for_selector("div.space-y-2")
        
        load_more_selector = "button:has-text('Load More'), button:has-text('Show More'), .load-more"
        
        while True:
            try:
                load_more = await page.query_selector(load_more_selector)
                if load_more:
                    await load_more.click()
                    await page.wait_for_load_state("networkidle", timeout=2000)
                    continue
            except:
                break
        
        await page.evaluate("""
            () => {
                window.scrollData = { shouldContinue: true, lastRowCount: 0 };
                
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            window.scrollTo(0, document.body.scrollHeight);
                        }
                    });
                });
                
                const rows = document.querySelectorAll('div.space-y-2 > div.flex.flex-col');
                if (rows.length > 5) {
                    for (let i = rows.length - 5; i < rows.length; i++) {
                        observer.observe(rows[i]);
                    }
                }
            }
        """)
        
        last_count = 0
        stable_count = 0
        
        while stable_count < 3:
            for _ in range(5):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(0.1)
            
            current_count = await page.evaluate("document.querySelectorAll('div.space-y-2 > div.flex.flex-col').length")
            
            if current_count == last_count:
                stable_count += 1
            else:
                stable_count = 0
                
            last_count = current_count
            print(f"Rapid loading: {current_count} rows")
            
            await asyncio.sleep(0.5)
        
        all_data = await page.evaluate("""
            () => {
                const rows = document.querySelectorAll('div.space-y-2 > div.flex.flex-col');
                return Array.from(rows).map(row => {
                    const cells = row.querySelectorAll('div');
                    return Array.from(cells)
                        .map(cell => cell.innerText?.trim())
                        .filter(text => text && text.length > 0);
                }).filter(row => row.length > 0);
            }
        """)
        
        return all_data

    async def run_optimized_scrape(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding"
                ]
            )
            
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            page = await context.new_page()
            
            try:
                await self.login_and_save_session(page)
                await self.navigate_to_products(page)
                
                print("Starting optimized extraction...")
                start_time = time.time()
                
                products = await self.parallel_extraction(page)
                
                extraction_time = time.time() - start_time
                print(f"Extraction completed in {extraction_time:.2f} seconds")
                print(f"Total products extracted: {len(products)}")
                
                filename = f"products_optimized_{int(time.time())}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(products, f, indent=4, ensure_ascii=False)
                
                print(f"Saved to {filename}")
                return products
                
            except Exception as e:
                print(f"Error during scraping: {e}")
                raise
            finally:
                await browser.close()

class SuperOptimizedScraper(OptimizedScraper):
    def __init__(self, email, password):
        super().__init__(email, password)
    async def infinite_scroll_with_mutation_observer(self, page):
        await page.evaluate("""
            () => {
                window.scrapingData = { 
                    newRowsDetected: false, 
                    totalRows: 0,
                    extractedData: []
                };
                
                const targetNode = document.querySelector('div.space-y-2');
                if (!targetNode) return;
                
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                            window.scrapingData.newRowsDetected = true;
                            
                            mutation.addedNodes.forEach(node => {
                                if (node.nodeType === 1 && node.classList.contains('flex')) {
                                    const cells = node.querySelectorAll('div');
                                    const rowData = Array.from(cells)
                                        .map(cell => cell.innerText?.trim())
                                        .filter(text => text && text.length > 0);
                                    if (rowData.length > 0) {
                                        window.scrapingData.extractedData.push(rowData);
                                    }
                                }
                            });
                        }
                    });
                });
                
                observer.observe(targetNode, { 
                    childList: true, 
                    subtree: true 
                });
            }
        """)
        
        consecutive_no_change = 0
        last_data_length = 0
        
        try:
            while consecutive_no_change < 3:
                for _ in range(10):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(0.05)
                
                scraping_data = await page.evaluate("window.scrapingData")
                current_data = scraping_data.get('extractedData', [])
                current_length = len(current_data)
                
                with self.data_lock:
                    self.data = current_data.copy()
                
                if current_length == last_data_length:
                    consecutive_no_change += 1
                else:
                    consecutive_no_change = 0
                    
                last_data_length = current_length
                print(f"Real-time extracted: {current_length} rows")
                
                await asyncio.sleep(0.3)
        except KeyboardInterrupt:
            scraping_data = await page.evaluate("window.scrapingData")
            with self.data_lock:
                self.data = scraping_data.get('extractedData', [])
            self.signal_handler(signal.SIGINT, None)
        
        final_data = await page.evaluate("window.scrapingData.extractedData")
        return final_data

    async def multi_tab_approach(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            
            pages = []
            try:
                for i in range(3):
                    page = await context.new_page()
                    await self.login_and_save_session(page)
                    pages.append(page)
                
                tasks = [self.navigate_to_products(page) for page in pages]
                await asyncio.gather(*tasks)
                
                main_page = pages[0]
                products = await self.infinite_scroll_with_mutation_observer(main_page)
                
                with self.data_lock:
                    self.data = products
                
                return products
            except KeyboardInterrupt:
                self.signal_handler(signal.SIGINT, None)
            finally:
                await browser.close()

async def run_super_optimized():
    email = "nikhath.fatimam@gmail.com"
    password = "VBFzAiNg"
    
    scraper = SuperOptimizedScraper(email, password)
    
    print("Starting SUPER optimized scraping...")
    start_time = time.time()
    
    try:
        products = await scraper.multi_tab_approach()
        
        if not products:
            print("Falling back to single-tab optimized method...")
            scraper = OptimizedScraper(email, password)
            products = await scraper.run_optimized_scrape()
        
        total_time = time.time() - start_time
        print(f"TOTAL TIME: {total_time:.2f} seconds")
        print(f"SPEED: {len(products)/total_time:.1f} rows/second")
        
        return products
        
    except Exception as e:
        print(f"Error: {e}")
        raise

def main_optimized():
    return asyncio.run(run_super_optimized())

if __name__ == "__main__":
    products = main_optimized()