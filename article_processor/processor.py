import asyncio
import json
import os
from asyncio.subprocess import PIPE
from typing import Any, Dict

from readabilipy import simple_json_from_html_string
from readability import Document


class NodeProcessWrapper:
    def __init__(self, node_script="ProcessArticlePersistent.js"):
        self.node_script = node_script
        self.process = None
        self.restart_count = 0
        self.max_restart_attempts = 3
        self.lock = asyncio.Lock()

    async def start(self):
        """Start a Node.js subprocess."""
        self.process = await asyncio.create_subprocess_exec(
            "node",
            self.node_script,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    async def stop(self):
        """Terminate the Node.js subprocess."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None

    async def process_article(self, html: str, url: str) -> Dict[str, Any]:
        """Send the article for processing and return the parsed output."""
        async with self.lock:
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

            if self.process is None or self.process.returncode is not None:
                if self.restart_count >= self.max_restart_attempts:
                    raise Exception("Max restart attempts reached")
                self.restart_count += 1
                await self.start()

            self.process.stdin.write(request.encode("utf-8"))
            await self.process.stdin.drain()

            try:
                # Use a 30-second timeout (adjust as needed).
                line = await asyncio.wait_for(self.process.stdout.readline(), timeout=30)
                if not line:
                    raise ValueError(f"No response from Node process for {url}")
                data_json = json.loads(line.decode("utf-8").strip())
                data_json["mode"] = "nodejs readability/Readability.js"
                return data_json
            except asyncio.TimeoutError:
                raise Exception("Timeout waiting for Node process response")


class NodeProcessPool:
    def __init__(self, pool_size: int = None, node_script="ProcessArticlePersistent.js"):
        # Use CPU count if pool size is not specified.
        self.pool_size = pool_size or (os.cpu_count() or 4)
        self.node_script = node_script
        self.pool = asyncio.Queue()

    async def initialize(self):
        """Start the pool of Node processes."""
        for _ in range(self.pool_size):
            wrapper = NodeProcessWrapper(self.node_script)
            await wrapper.start()
            await self.pool.put(wrapper)

    async def process_article(self, html: str, url: str) -> Dict[str, Any]:
        """Get an available Node process to handle the article."""
        wrapper = await self.pool.get()
        try:
            result = await wrapper.process_article(html, url)
            return result
        except Exception as e:
            # If an error occurs, restart the process.
            try:
                await wrapper.stop()
            except Exception:
                pass
            wrapper = NodeProcessWrapper(self.node_script)
            await wrapper.start()
            result = await wrapper.process_article(html, url)
            return result
        finally:
            await self.pool.put(wrapper)

    async def cleanup(self):
        """Terminate all Node processes."""
        while not self.pool.empty():
            wrapper = await self.pool.get()
            await wrapper.stop()


class ArticleProcessor:
    def __init__(self, pool_size: int = None, node_script="ProcessArticlePersistent.js"):
        self.pool = NodeProcessPool(pool_size, node_script)

    async def initialize(self):
        """Initialize the pool of Node.js subprocesses."""
        await self.pool.initialize()

    async def process_backup(self, html: str, url: str) -> Dict[str, Any]:
        """
        Fallback article processing using Python-based libraries.
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
        Try processing with Node.js; if that fails (or times out), fall back.
        """
        try:
            result = await self.pool.process_article(html, url)
            return result
        except Exception as e:
            return await self.process_backup(html, url)

    async def cleanup(self):
        """Cleanup all Node.js subprocesses."""
        await self.pool.cleanup()


async def main():
    """
    Main demonstration function.
    """
    processor = ArticleProcessor(pool_size=4)
    await processor.initialize()

    example_html = """
    <html>
      <head><title>Test Article</title></head>
      <body>
        <h1>Article Title</h1>
        <p>This is a test article content.</p>
      </body>
    </html>
    """
    example_url = "https://example.com/test-article"

    # You can process multiple articles concurrently.
    tasks = [processor.process_article(example_html, example_url) for _ in range(8)]
    results = await asyncio.gather(*tasks)
    for result in results:
        print(json.dumps(result, indent=2))

    await processor.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # Fallback for environments that already have an event loop.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
