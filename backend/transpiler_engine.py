#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT TRANSPILER ENGINE v3.3 FINAL
=======================================
Motor profissional com items 100% visíveis

GARANTIAS v3.3:
✅ resource_pack/items/ SEMPRE criado
✅ Cada item tem JSON no BP E no RP
✅ item_texture.json com chaves simples
✅ Dependencies UUID corretas
✅ Logs detalhados para debug
"""

import json
import zipfile
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import traceback

@dataclass
class Item:
    """Representa um item"""
    identifier: str
    texture_name: str
    max_stack_size: int = 64
    max_damage: int = 0
    is_tool: bool = False

@dataclass
class Block:
    """Representa um bloco"""
    identifier: str
    texture_name: str
    hardness: float = 1.5

class JarAnalyzer:
    """Analisa arquivo JAR"""
    
    def __init__(self, jar_path: str):
        self.jar_path = Path(jar_path)
        self.mod_id = self._extract_mod_id()
        self.items: Dict[str, Item] = {}
        self.blocks: Dict[str, Block] = {}
        self.item_textures: Dict[str, bytes] = {}
        self.block_textures: Dict[str, bytes] = {}
        self.recipes: List[Dict] = []
    
    def _extract_mod_id(self) -> str:
        """Extrai ID limpo do mod"""
        name = self.jar_path.stem.lower()
        name = re.sub(r'[-_](forge|fabric|neoforge)', '', name)
        name = re.sub(r'[-_]mc?\d+\.\d+', '', name)
        name = re.sub(r'[-_]\d+\.\d+\.?\d*', '', name)
        name = re.sub(r'[^a-z0-9]', '', name)
        return name or "converted_mod"
    
    def analyze(self):
        """Analisa JAR completo"""
        print(f"📦 Mod ID: {self.mod_id}")
        print("🔍 Analisando JAR...")
        
        with zipfile.ZipFile(self.jar_path, 'r') as jar:
            for filename in jar.namelist():
                try:
                    # Texturas de items
                    if '/textures/item/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        data = jar.read(filename)
                        self.item_textures[name] = data
                        
                        # Cria item
                        item = Item(identifier=name, texture_name=name)
                        
                        # Detecta ferramentas
                        if any(x in name.lower() for x in ['sword', 'axe', 'pickaxe', 'shovel', 'hoe']):
                            item.is_tool = True
                            item.max_damage = 250
                            item.max_stack_size = 1
                        
                        # Detecta armadura
                        elif any(x in name.lower() for x in ['helmet', 'chestplate', 'leggings', 'boots']):
                            item.max_damage = 250
                            item.max_stack_size = 1
                        
                        self.items[name] = item
                    
                    # Texturas de blocos
                    elif '/textures/block/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        self.block_textures[name] = jar.read(filename)
                        self.blocks[name] = Block(identifier=name, texture_name=name)
                    
                    # Receitas
                    elif '/recipes/' in filename and filename.endswith('.json'):
                        try:
                            recipe_data = json.loads(jar.read(filename))
                            self.recipes.append({
                                'id': Path(filename).stem,
                                'data': recipe_data
                            })
                        except:
                            pass
                
                except Exception as e:
                    pass
        
        print(f"✅ {len(self.items)} items encontrados")
        print(f"✅ {len(self.blocks)} blocos encontrados")
        print(f"✅ {len(self.recipes)} receitas encontradas")

class AddonGenerator:
    """Gera estrutura do addon"""
    
    def __init__(self, mod_id: str, output_dir: Path):
        self.mod_id = mod_id
        self.output_dir = output_dir
        self.bp = output_dir / "behavior_pack"
        self.rp = output_dir / "resource_pack"
        
        # 4 UUIDs únicos
        self.bp_header_uuid = str(uuid.uuid4())
        self.bp_module_uuid = str(uuid.uuid4())
        self.rp_header_uuid = str(uuid.uuid4())
        self.rp_module_uuid = str(uuid.uuid4())
        
        self.stats = {
            'items_bp': 0,
            'items_rp': 0,
            'blocks': 0,
            'textures': 0
        }
    
    def generate(self, analyzer: JarAnalyzer):
        """Gera addon completo"""
        
        print("\n" + "=" * 70)
        print("🔨 GERANDO ADDON BEDROCK")
        print("=" * 70)
        
        # 1. Estrutura
        self._create_structure()
        
        # 2. Manifests
        self._generate_manifests()
        
        # 3. Ícones
        self._generate_pack_icons(analyzer.item_textures)
        
        # 4. Items
        print("\n📝 Gerando items:")
        self._generate_items_behavior(analyzer.items)
        self._generate_items_resource(analyzer.items)  # ✅ CRÍTICO!
        
        # 5. Blocos
        if analyzer.blocks:
            print("\n🧱 Gerando blocos:")
            self._generate_blocks(analyzer.blocks)
        
        # 6. Texturas
        print("\n🎨 Copiando texturas:")
        self._copy_textures(analyzer.item_textures, analyzer.block_textures)
        
        # 7. Mapeamentos
        print("\n📋 Gerando mapeamentos:")
        self._generate_item_texture_json(analyzer.items)
        
        if analyzer.blocks:
            self._generate_terrain_texture_json(analyzer.blocks)
            self._generate_blocks_json(analyzer.blocks)
        
        # 8. Traduções
        self._generate_languages(analyzer.items, analyzer.blocks)
        
        # 9. Empacota
        print("\n📦 Empacotando:")
        self._create_mcaddon()
        
        # 10. Resumo
        self._print_summary()
    
    def _create_structure(self):
        """Cria todas as pastas necessárias"""
        
        folders = [
            # Behavior Pack
            self.bp / "items",
            self.bp / "blocks",
            self.bp / "recipes",
            
            # Resource Pack
            self.rp / "items",              # ✅ CRÍTICO - Items no RP
            self.rp / "textures" / "items",
            self.rp / "textures" / "blocks",
            self.rp / "texts"
        ]
        
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
        
        print("   ✓ Estrutura de pastas criada")
    
    def _generate_manifests(self):
        """Gera manifests com UUIDs corretos"""
        
        # Behavior Pack Manifest
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} BP",
                "description": f"Converted from Java Edition\n{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "uuid": self.bp_header_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{
                "type": "data",
                "uuid": self.bp_module_uuid,
                "version": [1, 0, 0]
            }],
            # ✅ CRÍTICO - Dependencies
            "dependencies": [{
                "uuid": self.rp_header_uuid,
                "version": [1, 0, 0]
            }]
        }
        
        # Resource Pack Manifest
        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} RP",
                "description": "Textures and Models",
                "uuid": self.rp_header_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{
                "type": "resources",
                "uuid": self.rp_module_uuid,
                "version": [1, 0, 0]
            }]
        }
        
        self._save_json(bp_manifest, self.bp / "manifest.json")
        self._save_json(rp_manifest, self.rp / "manifest.json")
        
        print(f"   ✓ Manifests gerados")
        print(f"   ✓ BP UUID: {self.bp_header_uuid[:8]}...")
        print(f"   ✓ RP UUID: {self.rp_header_uuid[:8]}...")
        print(f"   ✓ Dependencies: BP → RP")
    
    def _generate_pack_icons(self, textures: Dict[str, bytes]):
        """Gera pack_icon.png"""
        if textures:
            first_texture = next(iter(textures.values()))
            (self.bp / "pack_icon.png").write_bytes(first_texture)
            (self.rp / "pack_icon.png").write_bytes(first_texture)
            print("   ✓ pack_icon.png criado")
    
    def _generate_items_behavior(self, items: Dict[str, Item]):
        """Gera items no Behavior Pack"""
        
        for name, item in items.items():
            item_json = {
                "format_version": "1.20.80",
                "minecraft:item": {
                    "description": {
                        "identifier": f"{self.mod_id}:{item.identifier}",
                        "menu_category": {
                            "category": "equipment" if item.is_tool else "items"
                        }
                    },
                    "components": {
                        "minecraft:icon": {
                            "texture": item.texture_name
                        },
                        "minecraft:max_stack_size": item.max_stack_size
                    }
                }
            }
            
            # Adiciona durabilidade se necessário
            if item.max_damage > 0:
                item_json["minecraft:item"]["components"]["minecraft:durability"] = {
                    "max_durability": min(item.max_damage, 32767)
                }
            
            self._save_json(item_json, self.bp / "items" / f"{name}.json")
            self.stats['items_bp'] += 1
        
        print(f"   ✓ {self.stats['items_bp']} items no Behavior Pack")
    
    def _generate_items_resource(self, items: Dict[str, Item]):
        """
        ✅ CRÍTICO: Gera items no Resource Pack
        SEM ISSO, ITEMS FICAM INVISÍVEIS!
        """
        
        print("   📝 Gerando items no Resource Pack...")
        
        for name, item in items.items():
            # Estrutura EXATA necessária para o Bedrock
            item_json = {
                "format_version": "1.20.80",
                "minecraft:item": {
                    "description": {
                        "identifier": f"{self.mod_id}:{item.identifier}"
                    },
                    "components": {
                        "minecraft:icon": item.texture_name  # ✅ Nome simples da textura
                    }
                }
            }
            
            # Salva em resource_pack/items/
            path = self.rp / "items" / f"{name}.json"
            self._save_json(item_json, path)
            self.stats['items_rp'] += 1
        
        print(f"   ✓ {self.stats['items_rp']} items no Resource Pack")
    
    def _generate_blocks(self, blocks: Dict[str, Block]):
        """Gera blocos"""
        
        for name, block in blocks.items():
            block_json = {
                "format_version": "1.20.80",
                "minecraft:block": {
                    "description": {
                        "identifier": f"{self.mod_id}:{block.identifier}"
                    },
                    "components": {
                        "minecraft:destructible_by_mining": {
                            "seconds_to_destroy": block.hardness / 1.5
                        },
                        "minecraft:geometry": "geometry.cube",
                        "minecraft:material_instances": {
                            "*": {
                                "texture": block.texture_name,
                                "render_method": "opaque"
                            }
                        }
                    }
                }
            }
            
            self._save_json(block_json, self.bp / "blocks" / f"{name}.json")
            self.stats['blocks'] += 1
        
        print(f"   ✓ {self.stats['blocks']} blocos gerados")
    
    def _copy_textures(self, item_tex: Dict[str, bytes], block_tex: Dict[str, bytes]):
        """Copia texturas"""
        
        # Items
        for name, data in item_tex.items():
            path = self.rp / "textures" / "items" / f"{name}.png"
            path.write_bytes(data)
            self.stats['textures'] += 1
        
        # Blocos
        for name, data in block_tex.items():
            path = self.rp / "textures" / "blocks" / f"{name}.png"
            path.write_bytes(data)
            self.stats['textures'] += 1
        
        print(f"   ✓ {self.stats['textures']} texturas copiadas")
    
    def _generate_item_texture_json(self, items: Dict[str, Item]):
        """
        ✅ Gera item_texture.json com estrutura CORRETA
        
        Chaves: nomes simples (ex: "copper_ingot")
        Valores: caminhos completos (ex: "textures/items/copper_ingot")
        """
        
        texture_data = {}
        
        for name, item in items.items():
            # ✅ Chave simples SEM namespace
            texture_key = item.texture_name
            
            # ✅ Caminho completo da textura
            texture_data[texture_key] = {
                "textures": f"textures/items/{item.texture_name}"
            }
        
        item_texture_json = {
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.items",
            "texture_data": texture_data
        }
        
        self._save_json(item_texture_json, self.rp / "textures" / "item_texture.json")
        print(f"   ✓ item_texture.json ({len(texture_data)} texturas)")
    
    def _generate_terrain_texture_json(self, blocks: Dict[str, Block]):
        """Gera terrain_texture.json"""
        
        texture_data = {}
        
        for name, block in blocks.items():
            texture_data[block.texture_name] = {
                "textures": f"textures/blocks/{block.texture_name}"
            }
        
        terrain_json = {
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.terrain",
            "texture_data": texture_data
        }
        
        self._save_json(terrain_json, self.rp / "textures" / "terrain_texture.json")
        print(f"   ✓ terrain_texture.json ({len(texture_data)} blocos)")
    
    def _generate_blocks_json(self, blocks: Dict[str, Block]):
        """Gera blocks.json"""
        
        blocks_data = {}
        
        for name, block in blocks.items():
            blocks_data[f"{self.mod_id}:{name}"] = {
                "textures": block.texture_name,
                "sound": "stone"
            }
        
        self._save_json(blocks_data, self.rp / "blocks.json")
        print(f"   ✓ blocks.json ({len(blocks_data)} blocos)")
    
    def _generate_languages(self, items: Dict[str, Item], blocks: Dict[str, Block]):
        """Gera traduções"""
        
        self._save_json(
            {"languages": ["en_US", "pt_BR"]},
            self.rp / "texts" / "languages.json"
        )
        
        entries = []
        
        for name in items.keys():
            display = name.replace('_', ' ').title()
            entries.append(f"item.{self.mod_id}:{name}.name={display}")
        
        for name in blocks.keys():
            display = name.replace('_', ' ').title()
            entries.append(f"tile.{self.mod_id}:{name}.name={display}")
        
        lang_content = "\n".join(entries)
        (self.rp / "texts" / "en_US.lang").write_text(lang_content, encoding='utf-8')
        (self.rp / "texts" / "pt_BR.lang").write_text(lang_content, encoding='utf-8')
        
        print(f"   ✓ Traduções ({len(entries)} entradas)")
    
    def _create_mcaddon(self):
        """Empacota em .mcaddon"""
        
        mcaddon_path = self.output_dir / f"{self.mod_id}.mcaddon"
        
        with zipfile.ZipFile(mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as z:
            # Behavior Pack
            for file in self.bp.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(self.output_dir))
            
            # Resource Pack
            for file in self.rp.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(self.output_dir))
        
        size_kb = mcaddon_path.stat().st_size / 1024
        print(f"   ✓ {mcaddon_path.name} ({size_kb:.1f} KB)")
    
    def _print_summary(self):
        """Imprime resumo final"""
        
        print("\n" + "=" * 70)
        print("✅ ADDON GERADO COM SUCESSO!")
        print("=" * 70)
        print(f"Items (Behavior Pack):  {self.stats['items_bp']}")
        print(f"Items (Resource Pack):  {self.stats['items_rp']}")  # ✅ NOVO
        print(f"Blocos:                 {self.stats['blocks']}")
        print(f"Texturas:               {self.stats['textures']}")
        print("=" * 70)
    
    def _save_json(self, data: Dict, path: Path):
        """Salva JSON"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    """Função principal de transpilação"""
    
    print("\n" + "=" * 70)
    print("🚀 MINECRAFT TRANSPILER ENGINE v3.3 FINAL")
    print("=" * 70)
    
    try:
        jar_path = Path(jar_path)
        if not jar_path.exists():
            raise FileNotFoundError(f"JAR não encontrado: {jar_path}")
        
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Análise
        analyzer = JarAnalyzer(jar_path)
        analyzer.analyze()
        
        # Geração
        generator = AddonGenerator(analyzer.mod_id, output_dir)
        generator.generate(analyzer)
        
        return {
            'success': True,
            'mod_id': analyzer.mod_id,
            'output_file': str(output_dir / f"{analyzer.mod_id}.mcaddon"),
            'stats': {
                'items_processed': generator.stats['items_bp'],
                'blocks_processed': generator.stats['blocks'],
                'recipes_converted': 0,
                'assets_extracted': generator.stats['textures']
            }
        }
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

class AvaritiaTranspiler:
    """Classe de compatibilidade com app.py antigo"""
    
    def __init__(self, jar_path: str, output_dir: str, mod_name: str = ""):
        self.jar_path = jar_path
        self.output_dir = output_dir
        self.stats = {}
    
    def run(self):
        result = transpile_jar(self.jar_path, self.output_dir)
        if result['success']:
            self.stats = result['stats']
        else:
            raise Exception(result.get('error', 'Erro desconhecido'))
    
    def parse_jar(self): pass
    def convert_all(self): pass
    def generate_scripts(self): pass
    def build_addon_structure(self): pass
    def package_mcaddon(self): pass
    def print_report(self): pass

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("\nUso: python transpiler_engine.py <mod.jar> [output_folder]")
        print("\nExemplo:")
        print("  python transpiler_engine.py SimpleOres2.jar output/")
        sys.exit(1)
    
    result = transpile_jar(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else "output"
    )
    
    if not result['success']:
        print(f"\n❌ Conversão falhou!")
        sys.exit(1)
    else:
        print(f"\n✅ Conversão concluída com sucesso!")
        print(f"Arquivo: {result['output_file']}")
        sys.exit(0)
