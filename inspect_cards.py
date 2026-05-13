import requests
from bs4 import BeautifulSoup

res = requests.get('https://iim-cat-questions-answers.fundamakers.com/questions.php?s=1&t=1&page=1', timeout=15)
soup = BeautifulSoup(res.text, 'html.parser')
cards = soup.find_all('div', class_='card')

for i, c in enumerate(cards[:10]):
    h3 = c.find("h3", class_="text-danger")
    has_qid = c.select_one("[questionid]")
    titles = c.select("h4.card-title")
    
    if h3:
        print(f"\nCard {i}: h3 text='{h3.get_text(strip=True)}', questionid={has_qid.get('questionid') if has_qid else None}, titles={len(titles)}")
        print(f"  Title texts: {[t.get_text(' ', strip=True)[:80] for t in titles]}")
