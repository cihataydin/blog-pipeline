# Blog Pipeline

Obsidian notlarını otomatik olarak Docusaurus blog'una (Türkçe + İngilizce) taşıyan otonom yayınlama agent'ı.

## Kullanım

```bash
python main.py "<obsidian path>/<file name>.md" --slug YYYY-MM-DD-slug-name
```

- **Argüman:** Notun `.md` dosya yolu (Obsidian klasöründen geçerli yol)
- **`--slug`:** Opsiyonel. Belirtilmezse `YYYY-MM-DD-<dosya-adi>` formatında otomatik üretilir.

Çalıştırdıktan sonra pipeline:

1. 📂 Markdown'i okur, görselleri (`static/img/blog/<slug>/`) taşır.
2. 🌐 Gemini ile notu **strict** modda İngilizceye çevirir (kod blokları ve SVG'ler olduğu gibi korunur, sadece yazı çevrilir, sıralama/skor korunur).
3. 💾 Türkçe ve İngilizce içerikleri Docusaurus blog dizinlerine yazar.
4. 🚀 Lokal Docusaurus sunucusunu başlatıp insan onayı (human-in-the-loop) bekler.

## Ortam Değişkenleri (.env)

- `GEMINI_API_KEY` — LLM API key (Gemini)
- `DOCUSAURUS_ROOT` — Docusaurus ana dizini (developer sorumluluğu, boş bırakılırsa değer alınmaz)
- `TR_BLOG_DIR` — Türkçe blog klasörü (developer sorumluluğu)
- `EN_BLOG_DIR` — İngilizce blog klasörü (developer sorumluluğu)
- `STATIC_IMG_DIR` — Statik görseller klasörü (developer sorumluluğu)

## Kurulum

```bash
pip install -r requirements.txt
```

