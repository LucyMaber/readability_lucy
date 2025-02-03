/**
 * ProcessArticlePersistent.js
 */

import { Readability } from '@mozilla/readability';
import { JSDOM, VirtualConsole } from 'jsdom';
import createDOMPurify from 'dompurify';
import readline from 'readline';

// Create a VirtualConsole and suppress extra warnings if desired.
const globalVirtualConsole = new VirtualConsole();
// Uncomment the next line to quiet JSDOM errors if you prefer:
// globalVirtualConsole.sendTo(console, { omitJSDOMErrors: true });

// Default Readability options.
const defaultReadabilityOptions = {
  debug: false,
  maxElemsToParse: 0,
  nbTopCandidates: 5,
  charThreshold: 500,
  classesToPreserve: [],
  keepClasses: false,
  serializer: undefined,
  disableJSONLD: false,
  allowedVideoRegex: null,
};

/**
 * Process an article by building a DOM from HTML, then running Readability and DOMPurify.
 */
function processArticle(request) {
  try {
    const { html, url } = request;
    if (!html || !url) {
      throw new Error('Invalid input: Missing HTML content or URL.');
    }

    // Merge any request options with defaults.
    const options = { ...defaultReadabilityOptions, ...request };

    // Create a JSDOM instance with external resource fetching disabled.
    const dom = new JSDOM(html, {
      url,
      virtualConsole: globalVirtualConsole,
      runScripts: "outside-only",
      resources: "none", // No external resources; speeds up processing.
    });

    // Create a DOMPurify instance.
    const DOMPurify = createDOMPurify(dom.window);

    // Run Readability on the document.
    const reader = new Readability(dom.window.document, options);
    const article = reader.parse();

    if (!article) {
      throw new Error('Readability failed to parse the article.');
    }

    // Sanitize and annotate the output.
    article.content = DOMPurify.sanitize(article.content);
    article.mode = "nodejs readability/Readability.js";
    return article;
  } catch (error) {
    console.error(`Error processing article: ${error.message}`);
    return { error: `Processing failed: ${error.message}` };
  }
}

// Read JSON requests (one per line) from stdin.
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

rl.on('line', (line) => {
  (async () => {
    try {
      const request = JSON.parse(line);
      const article = processArticle(request);
      console.log(JSON.stringify(article));
    } catch (e) {
      console.error(`Failed to process line: ${e.message}`);
      console.log(JSON.stringify({ error: e.message }));
    }
  })();
});

// (No special handling on close; process lifetime is managed externally.)
rl.on('close', () => {});

// Catch uncaught exceptions and unhandled rejections.
process.on('uncaughtException', (err) => {
  console.error(`Uncaught exception: ${err.message}`);
});
process.on('unhandledRejection', (reason) => {
  console.error(`Unhandled rejection: ${reason}`);
});
