import asyncio
import json
from asyncio.subprocess import PIPE
from typing import Any, Dict, List
from readabilipy import simple_json_from_html_string
from readability import Document

# -----------------------------------------------------------------------------
# NodeProcess: A thin wrapper around a Node.js subprocess.
# -----------------------------------------------------------------------------
class NodeProcess:
    def __init__(self, cmd: List[str] = None):
        if cmd is None:
            cmd = ["node", "ProcessArticle.js"]
        self.cmd = cmd
        self.process = None

    async def start(self):
        if self.process is not None:
            await self.stop()
        self.process = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    async def stop(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None

    async def send_request(self, request: str, timeout: int = 30) -> str:
        """
        Send a JSON request to the Node process and wait for a single response line.
        """
        self.process.stdin.write(request.encode("utf-8"))
        await self.process.stdin.drain()
        line = await asyncio.wait_for(self.process.stdout.readline(), timeout=timeout)
        if not line:
            raise ValueError("No response from Node process")
        return line.decode("utf-8").strip()

# -----------------------------------------------------------------------------
# ArticleProcessor: Uses a pool of Node processes for concurrent processing.
# -----------------------------------------------------------------------------
class ArticleProcessor:
    def __init__(self, num_workers: int = 4, max_restart_attempts: int = 3):
        self.num_workers = num_workers
        self.max_restart_attempts = max_restart_attempts
        self.node_pool: List[NodeProcess] = []
        self.pool_lock = asyncio.Lock()  # protects modifications to node_pool
        self.restart_counts = [0] * num_workers  # track per-worker restart counts

    async def start_pool(self):
        """
        Start a pool of Node.js subprocesses.
        """
        async with self.pool_lock:
            for _ in range(self.num_workers):
                node = NodeProcess()
                await node.start()
                self.node_pool.append(node)

    async def stop_pool(self):
        """
        Stop all Node.js subprocesses in the pool.
        """
        async with self.pool_lock:
            tasks = [node.stop() for node in self.node_pool]
            await asyncio.gather(*tasks)
            self.node_pool.clear()

    async def get_node(self) -> NodeProcess:
        """
        Get a Node process from the pool using a round-robin strategy.
        """
        async with self.pool_lock:
            if not self.node_pool:
                raise RuntimeError("No available Node processes in the pool.")
            # Rotate: pop the first process and append it back
            node = self.node_pool.pop(0)
            self.node_pool.append(node)
            return node

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
        Send HTML content and URL to a Node.js process for parsing via Mozilla Readability.
        Falls back to Python-based extraction on timeout or error.
        """
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

        try:
            node = await self.get_node()
            response_line = await node.send_request(request, timeout=30)
            data_json = json.loads(response_line)
            data_json["mode"] = "nodejs readability/Readability.js"
            return data_json

        except Exception as e:
            # On error or timeout, fallback to the Python-based extraction
            return await self.process_backup(html, url)

    async def cleanup(self):
        """
        Cleanup method to stop all Node.js subprocesses.
        """
        await self.stop_pool()

# -----------------------------------------------------------------------------
# Example usage: Processing an article.
# -----------------------------------------------------------------------------
async def main():
    processor = ArticleProcessor(num_workers=4)
    await processor.start_pool()

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

    # Process the article concurrently; in a real scenario, you might process many articles.
    result = await processor.process_article(example_html, example_url)
    print(json.dumps(result, indent=2))

    await processor.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # Fallback for environments where asyncio.run might raise a RuntimeError.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
