# iden_challenge

# SuperOptimized Web Scraper

A robust, interruption-resilient Playwright-based scraper for rapid extraction of product data from [https://hiring.idenhq.com](https://hiring.idenhq.com). Features multi-tab concurrency, smart scrolling, real-time data extraction with mutation observers, and automatic progress saving on interruption.

## Features

- **Multi-tab and Parallelized Scraping:** Extract data using multiple browser tabs concurrently for increased speed.
- **Optimized Infinite Scrolling:** Dynamically loads new data using a mutation observer.
- **Graceful Interruption Handling:** Automatically saves data to disk if interrupted (Ctrl+C).
- **Automatic Login:** Script logs in using provided credentials.
- **Fallback and Robustness:** Falls back to a single-tab approach if multi-tab fails.

## Setup

1. **Clone the repository**
2. **Install dependencies**
3. `pip install playwright`  
4. `playwright install`
5. 3. **Update credentials**
- Set your `email` and `password` variables in the script.

## Usage

Run the scraper with:

`python3 scrape.py`  
- Data is saved as `products_optimized_<timestamp>.json` upon completion, or `products_interrupted_<timestamp>.json` if interrupted.
- The script prints real-time progress and extraction speed.

## Methods

- `SuperOptimizedScraper`: Multi-tab, mutation observer, and interruption handling.
- `OptimizedScraper`: Single-session fallback with scroll and batch extraction.
