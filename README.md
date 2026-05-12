# CAT PYQ Scraper - Improved Version

A Python scraper for extracting CAT (Common Admission Test) questions from FundaMakers website.

## Features

- ✅ Extracts all questions (MCQ and TITA) with metadata (year, shift)
- ✅ Captures images in questions and options
- ✅ Properly decodes HTML entities
- ✅ Distinguishes between MCQ and TITA question types
- ✅ Extracts explanations from linked pages
- ✅ Works with local HTML files or live URLs

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### From Local HTML File
```python
from scraper_improved import scrape_from_html_file, save_results

results = scrape_from_html_file("FundaMakers - CAT Questions Number System.html")
save_results(results, "output.json")
```

### From URL
```python
from scraper_improved import scrape_from_url, save_results

url = "https://iim-cat-questions-answers.fundamakers.com/questions.php?s=1&t=1&page=1"
results = scrape_from_url(url)
save_results(results, "output.json")
```

### Run Directly
```bash
python scraper_improved.py
```

## Output Format

Each question in the JSON output contains:

```json
{
  "external_id": "4637",
  "section": "QA",
  "topic": "Number System",
  "year": 2024,
  "shift": 3,
  "question_text": "Question text or null if image-only",
  "question_images": [{"src": "./path/to/image.png", "alt": "image"}],
  "options": [
    {
      "text": "Option A or [Image]",
      "is_correct": true,
      "images": [{"src": "./path/to/option_image.png", "alt": "image"}]
    }
  ],
  "answer": "Correct answer",
  "type": "MCQ|TITA",
  "meta": "CAT/2024.3"
}
```

## Results Summary

| Metric | Count |
|--------|-------|
| Total Questions | 176 |
| MCQ Questions | 144 |
| TITA Questions | 32 |
| Questions with Images | 15 |
| Questions with Image Options | 14 |
| Data Completeness | 100% |

## Key Improvements Over Original

1. **Image Extraction**: Now extracts all images from questions and options (previously ignored)
2. **HTML Entity Decoding**: Properly decodes `&amp;`, `&lt;`, `&gt;` using `html.unescape()`
3. **Card Detection**: Flexible detection finds all 176 questions (was missing some)
4. **Math Notation**: Preserves superscript/subscript as `^6` and `_n`
5. **Explanation Scraping**: Fetches detailed explanations from linked pages

## File Structure

```
├── scraper_improved.py    # Main scraper (use this)
├── questions_viewer.html  # HTML viewer for output
├── output.json            # Generated questions
├── requirements.txt       # Python dependencies
└── FundaMakers - CAT Questions Number System.html  # Input HTML
```

## Requirements

- Python 3.7+
- requests
- beautifulsoup4