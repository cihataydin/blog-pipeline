import os
import re
import shutil
import time
from pathlib import Path
from google import genai
from google.genai import types
from openai import OpenAI  # <--- 1. OpenAI kütüphanesini ekledik (Ollama için)
from dotenv import load_dotenv

load_dotenv()

# Docusaurus Ana Dizinleri (Güvenlik: .env uzerinden yuklenir, default yok - developer sorumluluğu)
DOCUSAURUS_ROOT = Path(os.getenv("DOCUSAURUS_ROOT") or "")
TR_BLOG_DIR = DOCUSAURUS_ROOT / (os.getenv("TR_BLOG_DIR") or "")
EN_BLOG_DIR = DOCUSAURUS_ROOT / (os.getenv("EN_BLOG_DIR") or "")
STATIC_IMG_DIR = DOCUSAURUS_ROOT / (os.getenv("STATIC_IMG_DIR") or "")
# Docker içindeki Ollama modelleri (Sırayla denenir)
LOCAL_DOCKER_MODELS = [
    "qwen3:4b",
    "qwen2.5-coder:7b-instruct-q4_K_M"
]

# Google Client (15 saniye timeout)
gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=300_000)
)

# Docker Ollama Client (OpenAI uyumlu lokal endpoint)
ollama_client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL") or "",
    api_key=os.getenv("OLLAMA_API_KEY") or "ollama", # Zorunlu dummy anahtar
)

MODEL_NAME = "gemini-3.8-flash"

def process_markdown_and_assets(source_path_str: str, slug: str) -> tuple[str, list[str]]:
    source_path = Path(source_path_str).resolve()
    source_dir = source_path.parent
    content = source_path.read_text(encoding="utf-8")
    
    target_tr_dir = TR_BLOG_DIR / slug
    target_en_dir = EN_BLOG_DIR / slug
    target_tr_dir.mkdir(parents=True, exist_ok=True)
    target_en_dir.mkdir(parents=True, exist_ok=True)

    target_img_dir = STATIC_IMG_DIR / slug
    target_img_dir.mkdir(parents=True, exist_ok=True)
    
    copied_files = []

    # 1. Obsidian Wiki-link görselleri
    wiki_pattern = re.compile(r'!\[\[([^\]]+\.(?:png|jpg|jpeg|gif|svg|webp))\]\]', re.IGNORECASE)
    
    def replace_wiki_link(match):
        filename = match.group(1).strip()
        src_file = _find_asset_in_obsidian(source_dir, filename)
        if src_file and src_file.exists():
            if src_file.name not in copied_files:
                shutil.copy2(src_file, target_img_dir / src_file.name)
                copied_files.append(src_file.name)
            return f"![{src_file.stem}](/img/blog/{slug}/{src_file.name})"
        return match.group(0)

    content = wiki_pattern.sub(replace_wiki_link, content)

    # 2. Standart Markdown görselleri
    md_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+\.(?:png|jpg|jpeg|gif|svg|webp))\)', re.IGNORECASE)
    
    def replace_md_link(match):
        alt_text, rel_path = match.group(1), match.group(2).strip()
        if rel_path.startswith(("http://", "https://")):
            return match.group(0)
        
        src_file = (source_dir / rel_path).resolve()
        if not src_file.exists():
            src_file = _find_asset_in_obsidian(source_dir, Path(rel_path).name)
            
        if src_file and src_file.exists():
            if src_file.name not in copied_files:
                shutil.copy2(src_file, target_img_dir / src_file.name)
                copied_files.append(src_file.name)
            return f"![{alt_text}](/img/blog/{slug}/{src_file.name})"
        return match.group(0)

    content = md_pattern.sub(replace_md_link, content)
    return content, copied_files

def _find_asset_in_obsidian(start_dir: Path, filename: str) -> Path | None:
    direct = start_dir / filename
    if direct.exists():
        return direct
    current = start_dir
    for _ in range(3):
        for found in current.rglob(filename):
            return found
        current = current.parent
    return None

PROTECTED_BLOCK_PATTERN = re.compile(r"(?si)```[\s\S]*?```|<svg[\s\S]*?</svg>")
PROTECTED_TOKEN_RE = re.compile(r"@@PROTECTED_BLOCK_(\d+)@@")

def _protect_code_and_svgs(content: str) -> tuple[str, list[str]]:
    """
    Kod bloklarını (``` ... ```) ve SVG'leri (<svg ...>...</svg>) placeholder'larla değiştirir.
    Bu sayede çeviri modeli sadece dokunulabilir (prose) metni görür,
    kod/SVG blokları olduğu gibi korunur ve "sadece çevir" kuralına takılır.
    """
    protected: list[str] = []

    def _replace(match: re.Match) -> str:
        token = f"@@PROTECTED_BLOCK_{len(protected)}@@"
        protected.append(match.group(0))
        return token

    stripped = PROTECTED_BLOCK_PATTERN.sub(_replace, content)
    return stripped, protected

def _restore_code_and_svgs(content: str, protected: list[str]) -> str:
    """Placeholder'ları orijinal kod/SVG bloklarıyla geri yazar."""
    def _replace(match: re.Match) -> str:
        return protected[int(match.group(1))]
    return PROTECTED_TOKEN_RE.sub(_replace, content)

def translate_with_gemini(tr_content: str, feedback: str | None = None, prev_en: str | None = None) -> str:
    """
    Önce Gemini dener. Google başarısız olursa Docker üzerindeki yerel Ollama modellerine fallback yapar.

    Çevrilik akış (STRICT):
    1. Kod blokları ve SVG'ler placeholder'a alınıp çıkarılır (koruksuz çeviri).
    2. Model sadece prose metni çevirir (sadece çevir, asla ekleme/düzeltme yapma).
    3. Sonuç placeholder'lardan geri getirilir, orijinal bloklar aynen kalır.
    """
    protected_content, protected_blocks = _protect_code_and_svgs(tr_content)

    system_instruction = (
        "Sen kıdemli bir yazılım mühendisi ve teknik blog yazarısın. "
        "Verilen Türkçe Docusaurus blog yazısını akıcı ve teknik terminolojiye sadık kalarak İngilizceye çevir.\n"
        "GİRDİ GÜVENLİĞİ VE KESİN ÇEVİRİ (STRICT):\n"
        "1. Markdown formatını ve başlık seviyelerini koru, sıralamayı ve yazı yapısını ASLA değiştirme.\n"
        "2. ``` ... ``` ile sarmalanan kod bloklarını ve <svg>...</svg> görsellerini ASLA çevirme, aynen olduğu gibi koru.\n"
        "3. '@@PROTECTED_BLOCK_N@@' placeholder değerlerini ASLA değiştirme veya çevirme.\n"
        "4. Çeviriyi kesin (strict) yap: metni ASLA özetleme, atlama, kısaltma veya yorum ekleme; sadece çeviri metni döndür.\n"
        "5. Çıktıda orijinal yazının sırasını ve paragraflarını koru; herhangi bir şeyi yeniden sıralama.\n"
        "6. Sadece çevrilmiş metni döndür."
    )

    if feedback and prev_en:
        prompt = f"Kullanıcı şu düzeltmeyi istedi: '{feedback}'\nOrijinal:\n{protected_content}\nÖnceki:\n{prev_en}"
    else:
        prompt = f"Aşağıdaki teknik yazıyı İngilizceye çevir (sadece çevir, asla ekleme/düzeltme/yorum yapma, kesin ve sırasında koru):\n\n{protected_content}"

    max_retries = 3
    delay = 3

    # --- ADIM 1: Google Gemini Denemeleri ---
    for attempt in range(max_retries):
        try:
            print(f"      ↳ [Cloud: Google] {MODEL_NAME} deneniyor (Deneme {attempt + 1}/{max_retries})...")
            response = gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0,
                    response_mime_type="text/plain",
                ),
            )
            print("      ✅ [Başarılı] Gemini ile çeviri tamamlandı.")
            return _restore_code_and_svgs(response.text.strip(), protected_blocks)
            
        except Exception as e:
            print(f"      ⚠️ [Google Uyarı]: {e}")
            if attempt < max_retries - 1:
                print(f"      🔄 {delay} saniye sonra tekrar deneniyor...")
                time.sleep(delay)
                delay *= 2
            else:
                print("      ❌ Google tarafı yanıt vermedi. Lokal Docker (Ollama) yedeklerine geçiliyor...")

    # --- ADIM 2: Docker Lokal Ollama Fallback ---
    last_local_err = None
    for local_model in LOCAL_DOCKER_MODELS:
        try:
            print(f"      ↳ [Local Docker: Ollama] {local_model} deneniyor...")
            response = ollama_client.chat.completions.create(
                model=local_model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
            )
            print(f"      ✅ [Başarılı] Docker Ollama ({local_model}) ile çevrildi.")
            return _restore_code_and_svgs(response.choices[0].message.content.strip(), protected_blocks)
            
        except Exception as docker_err:
            print(f"      ⚠️ [{local_model} Hatası]: {docker_err}")
            last_local_err = docker_err
            continue

    raise Exception(f"Hem Google hem de Docker'daki lokal modeller başarısız oldu. Son hata: {last_local_err}")

def generate_front_matter_from_slug(slug: str, raw_content: str) -> tuple[dict, str]:
    """
    Parametre olarak verilen slug bilgisinden otomatik title üretir, 
    date alanını atar ve temiz gövdeyi döndürür.
    """
    # Slug'ı okunabilir başlığa çevir (örn: "deep-learning-intro" -> "Deep Learning Intro")
    title = slug.replace("-", " ").title()
    
    # Otomatik basit etiketler türet
    tags = ["blog", "tech"]
    if "python" in raw_content.lower():
        tags.append("python")
    if "docker" in raw_content.lower():
        tags.append("docker")
    if "ai" in raw_content.lower() or "yapay" in raw_content.lower():
        tags.append("ai")

    front_matter = {
        "slug": slug,
        "title": title,
        "tags": str(tags).replace("'", '"')
    }
    
    return front_matter, raw_content