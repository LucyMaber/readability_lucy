# Article Processor

## Overview
The Article Processor is a Python package designed to extract and sanitize main article content from web pages. It integrates Mozilla Readability with Python-based alternatives for robustness.

## Features
- Uses Mozilla Readability via Node.js for high-quality article extraction.
- Falls back to Python libraries (`readabilipy`, `readability-lxml`) when necessary.
- Supports async processing for efficient execution.
- Ensures extracted content is sanitized using DOMPurify.

## Installation
### Prerequisites
- Python 3.7+
- Node.js with npm

### Steps
```sh
# Clone the repository
git clone https://github.com/yourusername/article_processor.git
cd article_processor

# Install Python dependencies
pip install .

# Ensure Node.js dependencies are installed
npm install @mozilla/readability jsdom dompurify
```

## Usage
You can use the package from the command line or within Python.

### Command Line
```sh
article_processor input.html output.json
```

### Python
```python
from article_processor import ArticleProcessor

processor = ArticleProcessor()
html = "<html>...</html>"
url = "https://example.com"
result = processor.process_article(html, url)
print(result)
```

## License
This project is licensed under the MIT License.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Contact
For inquiries, please email your.email@example.com or visit https://github.com/yourusername/article_processor.

