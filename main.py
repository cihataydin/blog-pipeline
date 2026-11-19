import typer
from datetime import date
from pathlib import Path
from typing import List, Optional
from graph import build_blog_graph

app = typer.Typer(help="Obsidian notlarını Docusaurus'a taşıyan otonom yayınlama agent'ı.")

@app.command()
def publish(
    markdown_path: str = typer.Argument(..., help="Obsidian'daki .md dosyasının yolu"),
    slug: str = typer.Option(None, "--slug", "-s", help="Örn: 2026-11-18-my-first-blog-writing"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Blog etiketleri (virgülle ayırılacak, örn: system-design,ai). Boş bırakılırsa sizden sorulur."),
):
    """
    Obsidian yazısını işler, görselleri taşır, Gemini ile İngilizceye çevirir ve lokalde önizlemeye açar.
    """
    md_file = Path(markdown_path).expanduser().resolve()
    if not md_file.exists():
        typer.secho(f"Hata: Dosya bulunamadı -> {md_file}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not slug:
        clean_name = md_file.stem.lower().replace(" ", "-")
        today_str = date.today().isoformat()
        slug = f"{today_str}-{clean_name}"

    if tags:
        blog_tags: Optional[List[str]] = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        tags_input = typer.prompt("Blog etiketleri (virgülle ayır, örn: system-design,ai)", default="")
        blog_tags = [t.strip() for t in tags_input.split(",") if t.strip()] if tags_input.strip() else None

    typer.secho(f"🤖 blog-pipeline başlatılıyor | Hedef Slug: {slug}", fg=typer.colors.CYAN, bold=True)
    if blog_tags:
        typer.secho(f"🏷️  Kullanılacak etiketler: {', '.join(blog_tags)}", fg=typer.colors.YELLOW)

    graph = build_blog_graph()
    
    initial_state = {
        "source_md_path": str(md_file),
        "slug": slug,
        "tr_content": "",
        "en_content": None,
        "copied_assets": [],
        "feedback": None,
        "is_approved": False,
        "tags": blog_tags,
    }

    final_state = graph.invoke(initial_state)

    if final_state.get("is_approved"):
        typer.secho(f"\n✅ Harika! '{slug}' hem TR hem EN olarak Docusaurus dizinine hazırlandı.", fg=typer.colors.GREEN, bold=True)
        typer.echo("Artık git commit & push ile canlıya alabilirsin.")

if __name__ == "__main__":
    app()