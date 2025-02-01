/**
 * ProcessArticlePersistent.js
 */

import { Readability } from '@mozilla/readability';
import { JSDOM, VirtualConsole } from 'jsdom';
import createDOMPurify from 'dompurify';
import readline from 'readline';

/**
 * Processes HTML content to extract and sanitize the main article.
 *
 * @param {object} request - The request object containing article extraction parameters.
 * @returns {object}        - The extracted article object, or an error object.
 */
function processArticle(request) {
    try {
        const { html, url, debug, maxElemsToParse, nbTopCandidates, charThreshold, classesToPreserve, keepClasses, serializer, disableJSONLD, allowedVideoRegex } = request;
        
        if (!html || !url) {
            throw new Error('Invalid input: Missing HTML content or URL.');
        }

        // Create a virtual console to suppress JSDOM warnings (e.g., CSS errors).
        const virtualConsole = new VirtualConsole();

        // Initialize JSDOM with options
        const dom = new JSDOM(html, { url, virtualConsole });
        
        // Prepare DOMPurify
        const DOMPurify = createDOMPurify(dom.window);
        
        // Use Mozilla's Readability with optional configurations
        const reader = new Readability(dom.window.document, {
            debug: debug || false,
            maxElemsToParse: maxElemsToParse || 0,
            nbTopCandidates: nbTopCandidates || 5,
            charThreshold: charThreshold || 500,
            classesToPreserve: classesToPreserve || [],
            keepClasses: keepClasses || false,
            serializer: serializer || undefined,
            disableJSONLD: disableJSONLD || false,
            allowedVideoRegex: allowedVideoRegex || null,
        });

        // Attempt to parse the article
        const article = reader.parse();
        if (!article) {
            throw new Error('Readability failed to parse the article.');
        }

        // Sanitize the Readability-parsed HTML content
        article.content = DOMPurify.sanitize(article.content);

        // Return the final article object
        article.mode = "nodejs readability/Readability.js";
        return article;
    } catch (error) {
        console.error(`Error processing article: ${error.message}`);
        return { error: `Processing failed: ${error.message}` };
    }
}

// Create an interface to read JSON requests from stdin, line by line
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
});

// Listen for incoming lines (each line should be a JSON string)
rl.on('line', (line) => {
    try {
        // Parse the incoming request
        const request = JSON.parse(line);

        // Process the article and output the JSON result
        const article = processArticle(request);
        console.log(JSON.stringify(article));
    } catch (e) {
        // Log error to stderr
        console.error(`Failed to process line: ${e.message}`);
        // Respond with a JSON error object
        console.log(JSON.stringify({ error: e.message }));
    }
});

/**
 * Catch any uncaught exceptions to prevent the process from crashing.
 */
process.on('uncaughtException', (err) => {
    console.error(`Uncaught exception: ${err.message}`);
});

/**
 * Catch unhandled promise rejections.
 */
process.on('unhandledRejection', (reason) => {
    console.error(`Unhandled rejection: ${reason}`);
});
