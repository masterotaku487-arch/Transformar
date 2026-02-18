#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT CONVERTER + IA GENYX
===============================
Interface unificada com conversão automática
"""

import os
import gradio as gr
from groq import Groq
import tempfile
from gtts import gTTS
import requests
from pathlib import Path
import sys

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa o transpiler
try:
    from transpiler_engine import transpile_jar
    TRANSPILER_AVAILABLE = True
except ImportError:
    TRANSPILER_AVAILABLE = False
    print("⚠️  Transpiler não disponível")

# Cliente Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ============================================================================
# MODS POPULARES PARA CONVERSÃO RÁPIDA
# ============================================================================

POPULAR_MODS = {
    "🔥 SimpleOres 2": {
        "url": "https://mediafilez.forgecdn.net/files/5839/563/SimpleOres2-1.20.1-6.0.0.3.jar",
        "description": "Adiciona 5 novos minérios (Copper, Tin, Mythril, Adamantium, Onyx) com armaduras e ferramentas"
    },
    "⚔️ Spartan Weaponry": {
        "url": "https://mediafilez.forgecdn.net/files/5208/946/SpartanWeaponry-1.20.1-3.1.2.jar",
        "description": "Mais de 100 armas medievais (lanças, adagas, katanas, machados de guerra)"
    },
    "🏰 Castle Dungeons": {
        "url": "https://mediafilez.forgecdn.net/files/4649/882/castle_dungeons-3.1-forge-1.20.jar",
        "description": "Estruturas de castelos e masmorras com loot épico"
    },
    "🌲 Nature's Compass": {
        "url": "https://mediafilez.forgecdn.net/files/5051/177/NaturesCompass-1.20.1-1.11.2-forge.jar",
        "description": "Bússola para encontrar biomas específicos"
    },
    "🔮 Reliquary": {
        "url": "https://mediafilez.forgecdn.net/files/4532/711/xreliquary-1.20.1-1.4.43.jar",
        "description": "Items mágicos e relíquias poderosas"
    }
}

# ============================================================================
# FUNÇÕES DE CONVERSÃO
# ============================================================================

def convert_jar_file(jar_file):
    """Converte arquivo JAR enviado"""
    if not TRANSPILER_AVAILABLE:
        return None, "❌ Transpiler não disponível", "❌ Erro: Transpiler não carregado"
    
    if jar_file is None:
        return None, "❌ Nenhum arquivo selecionado", "⚠️  Selecione um arquivo .jar"
    
    try:
        output_dir = Path(tempfile.mkdtemp())
        
        status = "🔄 Convertendo...\n"
        yield None, status, "🔄 Processando..."
        
        result = transpile_jar(jar_file.name, str(output_dir))
        
        if result['success']:
            output_file = result['output_file']
            stats = result['stats']
            
            status += f"✅ SUCESSO!\n"
            status += f"📦 Mod: {result['mod_id']}\n"
            status += f"📊 Items: {stats['items_processed']}\n"
            status += f"📊 Blocos: {stats['blocks_processed']}\n"
            status += f"📊 Texturas: {stats['assets_extracted']}\n"
            
            info = f"""
✅ **CONVERSÃO COMPLETA!**

📦 **Mod ID:** `{result['mod_id']}`  
📊 **Items:** {stats['items_processed']}  
📊 **Blocos:** {stats['blocks_processed']}  
📊 **Texturas:** {stats['assets_extracted']}

**📥 Baixe o arquivo .mcaddon acima e importe no Minecraft Bedrock!**
            """
            
            yield output_file, status, info
        else:
            error_msg = result.get('error', 'Erro desconhecido')
            status += f"❌ ERRO: {error_msg}\n"
            yield None, status, f"❌ Erro na conversão:\n{error_msg}"
    
    except Exception as e:
        yield None, f"❌ Erro: {str(e)}", f"❌ Exceção: {str(e)}"

def convert_popular_mod(mod_name):
    """Converte mod popular com 1 clique"""
    if not TRANSPILER_AVAILABLE:
        return None, "❌ Transpiler não disponível", "❌ Erro"
    
    if mod_name not in POPULAR_MODS:
        return None, "❌ Mod não encontrado", "❌ Erro"
    
    try:
        mod_info = POPULAR_MODS[mod_name]
        
        status = f"🔄 Baixando {mod_name}...\n"
        yield None, status, "🔄 Baixando mod..."
        
        response = requests.get(mod_info['url'], allow_redirects=True, timeout=60)
        
        temp_jar = tempfile.NamedTemporaryFile(delete=False, suffix='.jar')
        temp_jar.write(response.content)
        temp_jar.close()
        
        status += f"✅ Download completo ({len(response.content)/1024:.1f}KB)\n"
        status += "🔄 Convertendo...\n"
        yield None, status, "🔄 Convertendo..."
        
        output_dir = Path(tempfile.mkdtemp())
        result = transpile_jar(temp_jar.name, str(output_dir))
        
        if result['success']:
            output_file = result['output_file']
            stats = result['stats']
            
            status += f"✅ CONVERSÃO COMPLETA!\n"
            status += f"📦 Mod: {result['mod_id']}\n"
            status += f"📊 Items: {stats['items_processed']}\n"
            status += f"📊 Blocos: {stats['blocks_processed']}\n"
            
            info = f"""
✅ **{mod_name} CONVERTIDO!**

{mod_info['description']}

📊 **Items:** {stats['items_processed']}  
📊 **Blocos:** {stats['blocks_processed']}  
📊 **Texturas:** {stats['assets_extracted']}

**📥 Baixe o .mcaddon acima e importe no Minecraft!**
            """
            
            yield output_file, status, info
        else:
            error = result.get('error', 'Erro')
            yield None, status + f"❌ {error}", f"❌ Erro: {error}"
    
    except Exception as e:
        yield None, f"❌ Erro: {str(e)}", f"❌ Exceção: {str(e)}"

# ============================================================================
# IA GENYX
# ============================================================================

def orchestrator(message, history):
    """IA conversacional com Groq"""
    log = "🧠 [GENYX ULTRA]: Processando...\n"
    
    messages = [{"role": "system", "content": "Você é GENYX ULTRA, especialista em Minecraft e conversão de mods Java para Bedrock. Use markdown e seja direto."}]
    
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        stream=True
    )
    
    new_history = list(history) if history else []
    new_history.append({"role": "user", "content": message})
    new_history.append({"role": "assistant", "content": ""})

    full_text = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            full_text += chunk.choices[0].delta.content
            new_history[-1]["content"] = full_text
            yield new_history, log, None, None

    # TTS
    audio_path = None
    try:
        tts = gTTS(text=full_text[:300], lang='pt')
        t_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(t_audio.name)
        audio_path = t_audio.name
    except: pass

    # Código
    file_path = None
    if "```" in full_text:
        try:
            code_content = full_text.split("```")[1].split("\n", 1)[-1]
            t_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
            t_file.write(code_content.strip())
            t_file.close()
            file_path = t_file.name
        except: pass

    yield new_history, log + "✅ Completo.", audio_path, file_path

# ============================================================================
# INTERFACE GRADIO
# ============================================================================

with gr.Blocks(theme=gr.themes.Soft(), title="Minecraft Converter + IA") as demo:
    gr.Markdown("""
    # 🎮 MINECRAFT JAVA → BEDROCK CONVERTER + IA
    
    **Converta mods Java para Bedrock Edition com 1 clique + IA integrada!**
    """)
    
    with gr.Tabs():
        # ═══════════════════════════════════════════════════════════════
        # TAB 1: MODS POPULARES (1 CLIQUE)
        # ═══════════════════════════════════════════════════════════════
        with gr.Tab("🔥 Mods Populares"):
            gr.Markdown("""
            ## 🎯 Converta Mods Populares com 1 Clique!
            
            Selecione um mod e clique para baixar e converter automaticamente:
            """)
            
            with gr.Row():
                with gr.Column(scale=2):
                    mod_dropdown = gr.Dropdown(
                        choices=list(POPULAR_MODS.keys()),
                        label="🎮 Escolha um Mod Popular",
                        value=list(POPULAR_MODS.keys())[0]
                    )
                    mod_description = gr.Markdown()
                    convert_popular_btn = gr.Button("⚡ BAIXAR E CONVERTER AGORA", variant="primary", size="lg")
                
                with gr.Column(scale=1):
                    popular_status = gr.Textbox(
                        label="Status da Conversão",
                        lines=12,
                        interactive=False
                    )
            
            with gr.Row():
                with gr.Column():
                    popular_output = gr.File(label="📥 Download do .mcaddon")
                with gr.Column():
                    popular_info = gr.Markdown("Selecione um mod acima")
            
            # Mostra descrição do mod
            def show_mod_info(mod_name):
                if mod_name in POPULAR_MODS:
                    return f"**{mod_name}**\n\n{POPULAR_MODS[mod_name]['description']}"
                return ""
            
            mod_dropdown.change(show_mod_info, inputs=[mod_dropdown], outputs=[mod_description])
            
            # Converte mod popular
            convert_popular_btn.click(
                convert_popular_mod,
                inputs=[mod_dropdown],
                outputs=[popular_output, popular_status, popular_info]
            )
            
            # Inicializa
            demo.load(show_mod_info, inputs=[mod_dropdown], outputs=[mod_description])
        
        # ═══════════════════════════════════════════════════════════════
        # TAB 2: UPLOAD DE MOD
        # ═══════════════════════════════════════════════════════════════
        with gr.Tab("📤 Enviar Mod"):
            gr.Markdown("## 📤 Faça Upload do seu Mod (.jar)")
            
            with gr.Row():
                with gr.Column(scale=2):
                    jar_upload = gr.File(
                        label="Arraste seu arquivo .jar aqui",
                        file_types=[".jar"],
                        type="filepath"
                    )
                    convert_btn = gr.Button("🚀 CONVERTER AGORA", variant="primary", size="lg")
                
                with gr.Column(scale=1):
                    conversion_status = gr.Textbox(
                        label="Status da Conversão",
                        lines=12,
                        interactive=False
                    )
            
            with gr.Row():
                with gr.Column():
                    output_file = gr.File(label="📥 Download do .mcaddon")
                with gr.Column():
                    conversion_info = gr.Markdown("Aguardando arquivo...")
            
            convert_btn.click(
                convert_jar_file,
                inputs=[jar_upload],
                outputs=[output_file, conversion_status, conversion_info]
            )
        
        # ═══════════════════════════════════════════════════════════════
        # TAB 3: IA GENYX
        # ═══════════════════════════════════════════════════════════════
        with gr.Tab("🤖 IA Minecraft"):
            gr.Markdown("## 💬 Converse com a IA sobre Minecraft")
            
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(label="Terminal IA", height=500)
                    msg = gr.Textbox(placeholder="Pergunte sobre Minecraft, mods, comandos, conversões...", show_label=False)
                    
                    with gr.Row():
                        send_btn = gr.Button("📤 ENVIAR", variant="primary")
                        clear_btn = gr.Button("🗑️ LIMPAR")
                    
                    ai_logs = gr.TextArea(label="Logs", interactive=False, lines=2)
                
                with gr.Column(scale=1):
                    img_in = gr.Image(label="Upload de Imagem", type="numpy")
                    audio_out = gr.Audio(label="🔊 Resposta em Áudio", autoplay=True)
                    file_down = gr.File(label="📄 Arquivo Gerado")
            
            send_btn.click(orchestrator, [msg, chatbot], [chatbot, ai_logs, audio_out, file_down])
            msg.submit(orchestrator, [msg, chatbot], [chatbot, ai_logs, audio_out, file_down])
            clear_btn.click(lambda: ([], "", None, None), None, [chatbot, ai_logs, audio_out, file_down])
    
    gr.Markdown("""
    ---
    **🎮 Minecraft Java → Bedrock Converter v4.3 + IA GENYX**  
    Desenvolvido com ❤️ | Conversão automática + IA conversacional
    """)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
