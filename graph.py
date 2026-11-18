import subprocess
import time
from langgraph.graph import StateGraph, END
from state import BlogAgentState
from tools import (
    process_markdown_and_assets,
    translate_with_gemini,
    TR_BLOG_DIR,
    EN_BLOG_DIR,
    DOCUSAURUS_ROOT,
)

def parse_and_assets_node(state: BlogAgentState) -> dict:
    print(f"\n[1/4] 📂 Markdown işleniyor ve görseller taşınıyor: {state['slug']}")
    tr_clean, assets = process_markdown_and_assets(state["source_md_path"], state["slug"])
    if assets:
        print(f"      ↳ Taşınan görseller: {', '.join(assets)}")
    return {"tr_content": tr_clean, "copied_assets": assets}

def translate_node(state: BlogAgentState) -> dict:
    if state.get("feedback"):
        print(f"\n[2/4] 🔄 Geri bildirime göre İngilizce çeviri güncelleniyor...")
    else:
        print(f"\n[2/4] 🌐 Gemini ile İngilizce çeviri hazırlanıyor...")
        
    en_text = translate_with_gemini(
        tr_content=state["tr_content"],
        feedback=state.get("feedback"),
        prev_en=state.get("en_content"),
    )
    return {"en_content": en_text, "feedback": None}

def write_files_node(state: BlogAgentState) -> dict:
    print(f"\n[3/4] 💾 Dosyalar Docusaurus dizinlerine yazılıyor...")
    slug = state["slug"]
    
    tr_file = TR_BLOG_DIR / slug / "index.md"
    en_file = EN_BLOG_DIR / slug / "index.md"
    
    tr_file.write_text(state["tr_content"], encoding="utf-8")
    en_file.write_text(state["en_content"], encoding="utf-8")
    
    print(f"      ↳ TR: {tr_file}")
    print(f"      ↳ EN: {en_file}")
    return {}

def local_preview_approval_node(state: BlogAgentState) -> dict:
    print("\n[4/4] 🚀 Lokal Docusaurus sunucusu başlatılıyor...")
    server_process = subprocess.Popen(
        ["npm", "start"],
        cwd=DOCUSAURUS_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)

    print("\n" + "="*60)
    print("👀 İNSAN ONAYI (HUMAN-IN-THE-LOOP)")
    print(f"Tarayıcıdan kontrol et: http://localhost:3000/blog/{state['slug']}")
    print("="*60)
    
    choice = input("\nYazı ve çeviri olmuş mu? Onaylıyor musun? [e/h]: ").strip().lower()
    server_process.terminate()

    if choice in ["e", "evet", "y", "yes"]:
        return {"is_approved": True}
    else:
        fb = input("Neyi düzeltmemi istersin? (Örn: 'İngilizce başlık uzun olmuş kısalt'): ").strip()
        return {"is_approved": False, "feedback": fb}

def should_continue(state: BlogAgentState) -> str:
    if state.get("is_approved"):
        return "end"
    return "revise"

def build_blog_graph():
    workflow = StateGraph(BlogAgentState)
    
    workflow.add_node("parse_and_assets", parse_and_assets_node)
    workflow.add_node("translate", translate_node)
    workflow.add_node("write_files", write_files_node)
    workflow.add_node("human_review", local_preview_approval_node)
    
    workflow.set_entry_point("parse_and_assets")
    
    workflow.add_edge("parse_and_assets", "translate")
    workflow.add_edge("translate", "write_files")
    workflow.add_edge("write_files", "human_review")
    
    workflow.add_conditional_edges(
        "human_review",
        should_continue,
        {
            "end": END,
            "revise": "translate",
        }
    )
    
    return workflow.compile()