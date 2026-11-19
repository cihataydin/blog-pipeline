from typing import TypedDict, List, Optional

class BlogAgentState(TypedDict):
    source_md_path: str          # Obsidian'daki orijinal .md dosyasının yolu
    slug: str                    # Örn: 2026-11-18-my-first-blog-writing
    tr_content: str              # Görsel yolları düzeltilmiş Türkçe içerik
    en_content: Optional[str]    # Gemini ile çevrilmiş İngilizce içerik
    copied_assets: List[str]     # Taşınan SVG/PNG dosyalarının isimleri
    feedback: Optional[str]      # Kullanıcı lokalde beğenmezse gireceği düzeltme notu
    is_approved: bool            # Lokal önizleme onayı (True/False)
    tags: Optional[List[str]]   # Kullanıcıdan alınan blog etiketleri