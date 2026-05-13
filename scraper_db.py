import requests
from bs4 import BeautifulSoup
import json
import html
import re
import hashlib
from pathlib import Path
from urllib.parse import urljoin
import os
import boto3
from pymongo import MongoClient
from bson import ObjectId
import certifi
from dotenv import load_dotenv
import io

load_dotenv()

BASE_URL = "https://iim-cat-questions-answers.fundamakers.com/questions.php"

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET_NAME:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

# MongoDB Configuration
CONNECTION_STRING = os.getenv("CONNECTION_STRING")
db_client = None
db = None
questions_collection = None
comprehensions_collection = None

if CONNECTION_STRING:
    db_client = MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    # Using the db name from connection string if present, otherwise default to StudyNaksha
    db = db_client.get_database("StudyNaksha")
    questions_collection = db.get_collection("questions")
    comprehensions_collection = db.get_collection("comprehensions")

# Catalog Mapping based on provided HTML
CATALOG = {
    # s=1: Quantitative Ability
    "1": {
        "name": "Quantitative Ability",
        "topics": {
            "1": "Number System",
            "2": "Set Theory",
            "3": "Functions",
            "4": "Averages, Ratio & Proportion",
            "5": "Percentage, Profit & Loss",
            "6": "Algebra",
            "7": "Geometry",
            "8": "Mensuration",
            "9": "TIme, Speed, Distance and Work",
            "10": "Permutation, Combination and Probability",
        }
    },
    # s=4: DILR
    "4": {
        "name": "DILR",
        "topics": {
            "18": "Line Chart & Bar Chart",
            "19": "Pie Charts",
            "20": "Data Tabulation",
            "21": "Data Sufficiency",
            "22": "Logical Reasoning",
            "23": "Analytical Reasoning",
        }
    },
    # s=3: RC
    "3": {
        "name": "RC",
        "topics": {
            "14": "RC- Social Science",
            "15": "RC Based on Natural Science",
            "16": "RC Based on Humanities",
        }
    },
    # s=2: Verbal Ability
    "2": {
        "name": "Verbal Ability",
        "topics": {
            "31": "Grammar",
            "11": "Critical Reasoning",
            "12": "Para Jumbles",
            "13": "Paragraph Completion",
            "17": "Para Summary",
            "24": "Odd One Out",
            "30": "Analogy",
            "25": "Fill in the Blanks",
            "26": "Antonyms",
            "28": "Synonyms",
            "29": "Word Usage",
            "32": "Fact, Inference & Judgement",
            "33": "Deductions",
        }
    }
}

def upload_to_s3(image_url):
    """Downloads an image from URL and uploads it to S3, returning the S3 URL."""
    if not s3_client or not image_url:
        return image_url
    
    try:
        # Avoid re-uploading if already an S3 URL
        if "s3.amazonaws.com" in image_url or AWS_S3_BUCKET_NAME in image_url:
            return image_url

        # Generate a unique key based on the original URL path
        # E.g., https://.../question_images/123.jpg -> question_images/123.jpg
        from urllib.parse import urlparse
        parsed = urlparse(image_url)
        s3_key = parsed.path.lstrip("/")
        if not s3_key:
            return image_url # fallback

        # Download image
        res = requests.get(image_url, stream=True, timeout=10)
        res.raise_for_status()

        # Upload to S3
        s3_client.upload_fileobj(
            res.raw,
            AWS_S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={'ContentType': res.headers.get('content-type', 'image/jpeg')}
        )

        # Construct S3 URL
        s3_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        return s3_url

    except Exception as e:
        print(f"Failed to upload image {image_url} to S3: {e}")
        return image_url

def clean(text):
    if not text: return ""
    text = html.unescape(text)
    text = " ".join(text.split()).strip()
    return text

def extract_text_with_math(element):
    if not element: return ""
    html_str = str(element)
    html_str = re.sub(r'<sup>([^<]+)</sup>', r'^\1', html_str)
    html_str = re.sub(r'<sub>([^<]+)</sub>', r'_\1', html_str)
    html_str = re.sub(r'<span[^>]*>√</span>', r'√', html_str)
    html_str = re.sub(r'<span[^>]*>π</span>', r'π', html_str)
    
    temp_soup = BeautifulSoup(html_str, "html.parser")
    text_parts = []
    for child in temp_soup.descendants:
        if isinstance(child, str):
            text = str(child).strip()
            if text:
                text_parts.append(text)
    
    return clean(" ".join(text_parts))

def extract_images_and_text(element):
    images = []
    text_parts = []
    if not element: return "", images
    
    for img in element.find_all("img", recursive=True):
        src = img.get("src", "").strip()
        if src and ('question_images' in src or 'files/' in src):
            images.append({"src": src})
            
    for child in element.descendants:
        if hasattr(child, 'name') and child.name == 'img': continue
        if isinstance(child, str):
            text = str(child).strip()
            if text: text_parts.append(text)
            
    return clean(" ".join(text_parts)), images

def fix_and_upload_images(images, base_url="https://iim-cat-questions-answers.fundamakers.com"):
    """Fixes relative URLs and uploads to S3, returning a list of image URLs."""
    if not images: return []
    image_urls = []
    for img in images:
        src = img.get("src", "")
        
        # Fix legacy domain that no longer resolves
        src = src.replace("http://cat.fundamakers.com", "https://iim-cat-questions-answers.fundamakers.com")
        src = src.replace("https://cat.fundamakers.com", "https://iim-cat-questions-answers.fundamakers.com")
        
        if src.startswith("./"):
            src = base_url + src.replace("./", "/")
        elif not src.startswith("http"):
            src = urljoin(base_url, src)
            
        s3_url = upload_to_s3(src)
        image_urls.append(s3_url)
    return image_urls

def parse_meta(meta_text):
    year, shift = None, None
    try:
        meta_text = clean(meta_text)
        if "CAT/" in meta_text:
            part = meta_text.split("CAT/")[1]
            year = int(part.split(".")[0])
            if len(part.split(".")) > 1:
                shift = int(part.split(".")[1][0])
    except: pass
    return year, shift

def get_explanation_link(card, page_url):
    """Find explanation link inside a question card."""
    for a in card.find_all("a", href=True):
        link_text = a.get_text(strip=True).lower()
        if "explanation" in link_text:
            return urljoin(page_url, a["href"])
    return None

def scrape_explanation_page(url):
    """Fetch and parse explanation content from an explanation page."""
    explanation = {
        "text": None,
        "imageUrls": []
    }
    if not url: return explanation
    
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception:
        return explanation

    # The explanation lives inside div.col-12 that also contains the h1 "Explanatory Answer"
    h1 = soup.find("h1", string=lambda t: t and "explanatory answer" in t.lower())
    if h1:
        col_div = h1.find_parent("div", class_=lambda c: c and "col-12" in c)
        if col_div:
            images = []
            for img in col_div.find_all("img"):
                src = img.get("src", "").strip()
                if src and "question_images" in src:
                    images.append({"src": src})

            content_parts = []
            for child in col_div.children:
                if hasattr(child, "name") and child.name in ("h1", "h2", "h3", "h4"):
                    continue
                if hasattr(child, "get_text"):
                    txt = child.get_text(" ", strip=True)
                    if txt:
                        content_parts.append(txt)
                elif isinstance(child, str):
                    txt = child.strip()
                    if txt:
                        content_parts.append(txt)

            text = clean(" ".join(content_parts))
            explanation["text"] = text if text else None
            explanation["imageUrls"] = fix_and_upload_images(images)

    return explanation

def parse_card(card, subject_name, topic_name, idx, page_url=BASE_URL):
    """Parse a question card. Returns (doc, comprehension_data_or_None).
    comprehension_data is a dict with 'text' and 'imageUrls' if the card has a comprehension passage."""
    
    titles = card.select("h4.card-title")
    
    # Detect comprehension: look for <h3 class="text-danger">Comprehension</h3>
    has_comprehension = False
    comp_header = card.find("h3", class_="text-danger")
    if comp_header and "comprehension" in comp_header.get_text(strip=True).lower():
        has_comprehension = True
    
    comprehension_data = None
    question_text = None
    question_images_raw = []
    
    if has_comprehension and len(titles) >= 2:
        # Title 0 = passage, Title 1 = actual question
        passage_title = titles[0]
        question_title = titles[1]
        
        # Extract passage
        passage_text = extract_text_with_math(passage_title)
        _, passage_images = extract_images_and_text(passage_title)
        
        # Only treat as real comprehension if passage has meaningful content
        # (Fundamaker puts "Comprehension" header on ALL cards, even plain QA 
        # questions where the first title is just "N/A" or empty)
        has_real_passage = (passage_text and passage_text.strip() != "N/A" 
                           and len(passage_text.strip()) > 10) or len(passage_images) > 0
        
        if has_real_passage:
            passage_image_urls = fix_and_upload_images(passage_images)
            comprehension_data = {
                "text": passage_text if passage_text else None,
                "imageUrls": passage_image_urls
            }
        
        # Extract question
        q_text, q_images = extract_images_and_text(question_title)
        if q_images: question_images_raw.extend(q_images)
        math_text = extract_text_with_math(question_title)
        if math_text and math_text != "N/A":
            question_text = math_text
    else:
        # Non-comprehension card: all titles are question text
        for title in titles:
            text, images = extract_images_and_text(title)
            if images: question_images_raw.extend(images)
            if text and text != "N/A" and text != "":
                math_text = extract_text_with_math(title)
                if math_text and math_text != "N/A":
                    question_text = math_text if not question_text else question_text + " " + math_text
                
    question_image_urls = fix_and_upload_images(question_images_raw)

    options = []
    correct_option_index = None
    q_type = "tita"
    correct_answer = None
    
    option_items = card.select(".list-group-item")
    if option_items:
        q_type = "mcq"
        for opt_idx, opt_element in enumerate(option_items):
            opt_text, opt_images = extract_images_and_text(opt_element)
            is_correct = "Correct" in opt_element.get("class", [])
            
            if ":" in opt_text:
                opt_text = opt_text.split(":", 1)[1].strip()
            opt_text = clean(opt_text)
            
            opt_image_urls = fix_and_upload_images(opt_images)
            
            if opt_text or opt_image_urls:
                options.append({
                    "index": opt_idx,
                    "text": opt_text if opt_text else None,
                    "imageUrls": opt_image_urls
                })
                if is_correct:
                    correct_option_index = opt_idx

    tita_answers = card.select("[class*='tita-answer']")
    if tita_answers:
        q_type = "tita"
        for tita in tita_answers:
            tita_text = extract_text_with_math(tita)
            if tita_text:
                correct_answer = clean(tita_text)
                break

    qid_tag = card.select_one("[questionid]")
    if qid_tag:
        external_id = qid_tag.get("questionid", "")
    
    if not qid_tag or not external_id:
        # Generate a stable ID from question text so upserts work across runs
        id_source = (question_text or "") + subject_name + topic_name
        external_id = "auto_" + hashlib.md5(id_source.encode("utf-8")).hexdigest()[:12]
    
    meta = card.select_one(".muted-text")
    meta_text = extract_text_with_math(meta) if meta else ""
    year, shift = parse_meta(meta_text)

    explanation_url = get_explanation_link(card, page_url)
    explanation = scrape_explanation_page(explanation_url)

    doc = {
        "type": q_type,
        "text": question_text,
        "imageUrls": question_image_urls,
        "subject": subject_name,
        "topic": topic_name,
        "externalId": external_id,
        "year": year,
        "shift": shift,
        "explanation": explanation
    }
    
    if q_type == "mcq":
        doc["options"] = options
        doc["correctOptionIndex"] = correct_option_index
    else:
        doc["correctAnswer"] = correct_answer

    return doc, comprehension_data

def get_comprehension_hash(comp_data):
    """Generate a hash from comprehension text to deduplicate passages."""
    text = comp_data.get("text") or ""
    # Use first 500 chars for hashing — enough to uniquely identify a passage
    return hashlib.md5(text[:500].encode("utf-8")).hexdigest()

def get_or_create_comprehension(comp_data, subject_name, topic_name, comp_hash_cache):
    """Find or create a comprehension document. Returns the ObjectId."""
    comp_hash = get_comprehension_hash(comp_data)
    
    # Check in-memory cache first
    if comp_hash in comp_hash_cache:
        return comp_hash_cache[comp_hash]
    
    if comprehensions_collection is not None:
        # Check if it already exists in DB
        existing = comprehensions_collection.find_one({"hash": comp_hash})
        if existing:
            comp_hash_cache[comp_hash] = existing["_id"]
            return existing["_id"]
        
        # Insert new comprehension
        comp_doc = {
            "text": comp_data.get("text"),
            "imageUrls": comp_data.get("imageUrls", []),
            "subject": subject_name,
            "topic": topic_name,
            "hash": comp_hash
        }
        result = comprehensions_collection.insert_one(comp_doc)
        comp_hash_cache[comp_hash] = result.inserted_id
        print(f"  [NEW COMPREHENSION] Created comprehension {result.inserted_id}")
        return result.inserted_id
    
    return None

def scrape_topic(s_id, t_id, subject_name, topic_name):
    page = 1
    total_scraped = 0
    seen_ids = set()
    comp_hash_cache = {}  # hash -> ObjectId, for deduplicating comprehensions within a topic
    
    while True:
        url = f"{BASE_URL}?s={s_id}&t={t_id}&page={page}"
        print(f"Fetching {subject_name} - {topic_name} - Page {page} ({url})")
        
        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
        except Exception as e:
            print(f"Error fetching URL: {e}")
            break
            
        cards = soup.find_all("div", class_="card")
        valid_cards = [c for c in cards if c.select("h4.card-title")]
        
        if not valid_cards:
            print(f"No valid cards found on page {page}. Topic complete.")
            break
            
        new_cards_on_page = 0
        for idx, card in enumerate(valid_cards):
            try:
                doc, comp_data = parse_card(card, subject_name, topic_name, idx, url)
                
                # Check for infinite loop pagination
                if doc["externalId"] in seen_ids:
                    continue
                seen_ids.add(doc["externalId"])
                new_cards_on_page += 1
                
                # Handle comprehension linking
                if comp_data is not None:
                    comp_id = get_or_create_comprehension(comp_data, subject_name, topic_name, comp_hash_cache)
                    if comp_id:
                        doc["comprehensionId"] = comp_id
                
                # Insert into DB
                if questions_collection is not None:
                    # Update or insert
                    questions_collection.update_one(
                        {"externalId": doc["externalId"]},
                        {"$set": doc},
                        upsert=True
                    )
                total_scraped += 1
            except Exception as e:
                print(f"[ERROR] Error parsing question: {str(e)}")
                
        if new_cards_on_page == 0:
            print(f"No new questions found on page {page}. Site ignores pagination. Topic complete.")
            break
            
        page += 1
        
    return total_scraped

def scrape_from_html_file(html_file_path, subject_name, topic_name):
    print(f"Reading HTML file: {html_file_path}")
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.find_all("div", class_="card")
    valid_cards = [c for c in cards if c.select("h4.card-title")]
    
    print(f"Valid question cards: {len(valid_cards)}")
    total_scraped = 0
    
    for idx, card in enumerate(valid_cards):
        try:
            doc = parse_card(card, subject_name, topic_name, idx)
            if questions_collection is not None:
                questions_collection.update_one(
                    {"externalId": doc["externalId"]},
                    {"$set": doc},
                    upsert=True
                )
            total_scraped += 1
            print(f"[OK] Parsed and saved question {idx + 1}: {doc['externalId']}")
        except Exception as e:
            print(f"[ERROR] Error parsing question {idx + 1}: {str(e)}")
            
    return total_scraped

def run_scraper():
    if not questions_collection:
        print("Warning: MongoDB CONNECTION_STRING not set. Will skip saving.")
    if not s3_client:
        print("Warning: AWS Credentials not set. Images will not be uploaded to S3.")

    # Cleanup: remove old gen_ entries from previous runs.
    # These had passage+question text mixed together. The re-scrape will
    # recreate them with proper separated text and stable auto_ IDs.
    if questions_collection is not None:
        result = questions_collection.delete_many({"externalId": {"$regex": "^gen_"}})
        if result.deleted_count > 0:
            print(f"[CLEANUP] Removed {result.deleted_count} old 'gen_' entries. They will be re-scraped with proper comprehension separation.")

    total_all = 0
    for s_id, subject_data in CATALOG.items():
        subject_name = subject_data["name"]
        for t_id, topic_name in subject_data["topics"].items():
            scraped = scrape_topic(s_id, t_id, subject_name, topic_name)
            total_all += scraped
            
    print(f"Scraping complete. Total questions processed: {total_all}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Fundamaker questions")
    parser.add_argument("--local", type=str, help="Path to local HTML file to scrape")
    parser.add_argument("--subject", type=str, help="Subject name for local scrape", default="Quantitative Ability")
    parser.add_argument("--topic", type=str, help="Topic name for local scrape", default="Number System")
    args = parser.parse_args()

    if args.local:
        if Path(args.local).exists():
            print(f"Scraping from local file {args.local} for {args.subject} - {args.topic}")
            scrape_from_html_file(args.local, args.subject, args.topic)
        else:
            print(f"Local file {args.local} not found.")
    else:
        run_scraper()
