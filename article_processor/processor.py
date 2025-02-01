import asyncio
import json
from asyncio.subprocess import PIPE
from typing import Any, Dict
from readabilipy import simple_json_from_html_string
from readability import Document

class ArticleProcessor:
    def __init__(self):
        self.node_process = None
        self.node_restart_count = 0
        self.max_restart_attempts = 3
        self.lock = asyncio.Lock()

    async def start_node(self):
        """
        Start the Node.js subprocess that runs 'ProcessArticle.js'.
        """
        if self.node_process is not None:
            await self.stop_node()
        
        self.node_process = await asyncio.create_subprocess_exec(
            "node",
            "ProcessArticle.js",
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    async def stop_node(self):
        """
        Stop the Node.js subprocess safely.
        """
        if self.node_process:
            self.node_process.terminate()
            await self.node_process.wait()
            self.node_process = None

    async def process_backup(self, html: str, url: str) -> Dict[str, Any]:
        """
        Fallback article processing using Python-based readability libraries.
        """
        article = simple_json_from_html_string(html)
        if article:
            article["mode"] = "fallback1"
            return article
        doc = Document(html)
        if doc:
            return {
                "title": doc.title(),
                "content": doc.summary(),
                "mode": "fallback2",
            }
        return {"content": html, "mode": "raw_html"}

    async def process_article(self, html: str, url: str) -> Dict[str, Any]:
        """
        Send HTML content and URL to the Node.js script for parsing via Mozilla Readability.
        If a timeout or error occurs, fall back to Python-based extractor.
        """
        async with self.lock:
            try:
                request = json.dumps({
                    "html": html,
                    "url": url,
                    "debug": False,
                    "maxElemsToParse": None,
                    "nbTopCandidates": None,
                    "charThreshold": None,
                    "classesToPreserve": [],
                    "keepClasses": False,
                    "serializer": None,
                    "disableJSONLD": False,
                    "allowedVideoRegex": None
                }) + "\n"
                
                if self.node_process is None or self.node_process.returncode is not None:
                    if self.node_restart_count >= self.max_restart_attempts:
                        return {}
                    self.node_restart_count += 1
                    await self.start_node()

                self.node_process.stdin.write(request.encode("utf-8"))
                await self.node_process.stdin.drain()

                try:
                    line = await asyncio.wait_for(self.node_process.stdout.readline(), timeout=30)
                    if not line:
                        raise ValueError(f"No response from Node process for {url}")

                    data_json = json.loads(line.decode("utf-8").strip())
                    data_json["mode"] = "nodejs readability/Readability.js"
                    return data_json

                except asyncio.TimeoutError:
                    return await self.process_backup(html, url)
                
            except Exception as e:
                return {"error": str(e), "content": html, "mode": "raw_html"}

    async def cleanup(self):
        """
        Cleanup method to safely terminate subprocess before exiting.
        """
        await self.stop_node()

async def main():
    """
    Main function to demonstrate article processing.
    """
    processor = ArticleProcessor()
    await processor.start_node()

    example_html = """
    <html>
        <head><title>Test Article</title></head>
        <body><h1>Article Title</h1><p>This is a test article content.</p></body>
    </html>
    """
    example_url = "https://example.com/test-article"

    result = await processor.process_article(example_html, example_url)
    print(json.dumps(result, indent=2))

    await processor.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
