#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT TRANSPILER v3.1 - FINAL EDITION
==========================================
Motor completo com texturas funcionais e ícone do pack

CORREÇÕES v3.1:
✅ pack_icon.png gerado automaticamente
✅ UUIDs vinculados corretamente (BP → RP)
✅ Mapeamento estrito de texturas
✅ minecraft:icon com nome exato da chave
"""

import json
import zipfile
import re
import uuid
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import traceback

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class JavaItem:
    """Item do Java Edition"""
    identifier: str
    texture_name: str = ""
    max_stack_size: int = 64
    max_damage: int = 0
    attack_damage: float = 0.0
    is_tool: bool = False
    is_armor: bool = False

@dataclass
class JavaBlock:
    """Bloco do Java Edition"""
    identifier: str
    texture_name: str = ""
    hardness: float = 1.5
    resistance: float = 6.0
    material: str = "stone"

# ============================================================================
# ANALISADOR DE JAR
# ============================================================================

class JarAnalyzer:
    """Analisa JAR e extrai conteúdo"""
    
    def __init__(self, jar_path: str):
        self.jar_path = Path(jar_path)
        self.mod_id = self._extract_mod_id()
        
        self.items: Dict[str, JavaItem] = {}
        self.blocks: Dict[str, JavaBlock] = {}
        self.item_textures: Dict[str, bytes] = {}
        self.block_textures: Dict[str, bytes] = {}
        self.recipes: List[Dict] = []
        
        print(f"📦 Mod ID: {self.mod_id}")
    
    def _extract_mod_id(self) -> str:
        """Extrai ID limpo do mod"""
        name = self.jar_path.stem.lower()
        # Remove versões e plataformas
        name = re.sub(r'[-_](forge|fabric|neoforge)', '', name)
        name = re.sub(r'[-_]mc\d+\.\d+', '', name)
        name = re.sub(r'[-_]\d+\.\d+\.?\d*', '', name)
        name = re.sub(r'[^a-z0-9]', '', name)  # Remove tudo exceto letras/números
        return name or "converted_mod"
    
    def analyze(self):
        """Analisa JAR completo"""
        print("🔍 Analisando JAR...")
        
        with zipfile.ZipFile(self.jar_path, 'r') as jar:
            for filename in jar.namelist():
                try:
                    # Texturas de items
                    if '/textures/item/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        self.item_textures[name] = jar.read(filename)
                    
                    # Texturas de blocos
                    elif '/textures/block/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        self.block_textures[name] = jar.read(filename)
                    
                    # Receitas
                    elif '/recipes/' in filename and filename.endswith('.json'):
                        try:
                            data = json.loads(jar.read(filename))
                            self.recipes.append({'id': Path(filename).stem, 'data': data})
                        except:
                            pass
                
                except:
                    pass
        
        # Cria items/blocos baseado nas texturas
        for name, data in self.item_textures.items():
            item = JavaItem(identifier=name, texture_name=name)
            
            # Detecta tipo
            if any(x in name for x in ['sword', 'axe', 'pickaxe', 'shovel', 'hoe']):
                item.is_tool = True
                item.max_damage = 250
                item.max_stack_size = 1
            elif any(x in name for x in ['helmet', 'chestplate', 'leggings', 'boots']):
                item.is_armor = True
                item.max_damage = 250
                item.max_stack_size = 1
            
            self.items[name] = item
        
        for name, data in self.block_textures.items():
            self.blocks[name] = JavaBlock(identifier=name, texture_name=name)
        
        print(f"✅ Items: {len(self.items)}")
        print(f"✅ Blocos: {len(self.blocks)}")
        print(f"✅ Receitas: {len(self.recipes)}")

# ============================================================================
# CONVERSOR BEDROCK
# ============================================================================

class BedrockConverter:
    """Converte para Bedrock"""
    
    FORMAT = "1.20.80"
    
    @staticmethod
    def convert_item(item: JavaItem, mod_id: str) -> Dict:
        """
        Converte item para Bedrock
        
        CRÍTICO: O valor em minecraft:icon DEVE ser EXATAMENTE
        a chave usada em item_texture.json
        """
        
        # Nome limpo da textura (SEM namespace)
        texture_key = item.texture_name
        
        return {
            "format_version": BedrockConverter.FORMAT,
            "minecraft:item": {
                "description": {
                    "identifier": f"{mod_id}:{item.identifier}",
                    "menu_category": {
                        "category": "equipment" if item.is_tool or item.is_armor else "items"
                    }
                },
                "components": {
                    # ✅ CRÍTICO: Nome EXATO da chave do texture mapping
                    "minecraft:icon": {
                        "texture": texture_key
                    },
                    "minecraft:max_stack_size": item.max_stack_size,
                    **BedrockConverter._get_components(item)
                }
            }
        }
    
    @staticmethod
    def _get_components(item: JavaItem) -> Dict:
        """Componentes adicionais"""
        comp = {}
        
        if item.max_damage > 0:
            comp["minecraft:durability"] = {
                "max_durability": min(item.max_damage, 32767)
            }
        
        if item.attack_damage > 0:
            comp["minecraft:damage"] = item.attack_damage
        
        if item.is_tool:
            comp["minecraft:digger"] = {
                "use_efficiency": True,
                "destroy_speeds": [{
                    "block": "minecraft:stone",
                    "speed": 8
                }]
            }
        
        return comp
    
    @staticmethod
    def convert_block(block: JavaBlock, mod_id: str) -> Dict:
        """Converte bloco"""
        return {
            "format_version": BedrockConverter.FORMAT,
            "minecraft:block": {
                "description": {
                    "identifier": f"{mod_id}:{block.identifier}"
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

# ============================================================================
# GERADOR DE ADDON
# ============================================================================

class AddonGenerator:
    """Gera estrutura completa do addon"""
    
    def __init__(self, mod_id: str, output_dir: Path):
        self.mod_id = mod_id
        self.output_dir = output_dir
        self.bp = output_dir / "behavior_pack"
        self.rp = output_dir / "resource_pack"
        
        # UUIDs únicos e vinculados
        self.bp_uuid = str(uuid.uuid4())
        self.rp_uuid = str(uuid.uuid4())
        
        self.stats = {'items': 0, 'blocks': 0, 'recipes': 0, 'textures': 0}
    
    def generate(self, analyzer: JarAnalyzer):
        """Gera addon completo"""
        print("\n🔨 Gerando Addon...")
        
        self._create_structure()
        self._generate_manifests()
        
        # ✅ NOVO: Gera pack_icon.png
        self._generate_pack_icons(analyzer.item_textures)
        
        # Behavior Pack
        self._generate_items(analyzer.items)
        self._generate_blocks(analyzer.blocks)
        self._generate_recipes(analyzer.recipes)
        
        # Resource Pack
        self._copy_textures(analyzer.item_textures, analyzer.block_textures)
        self._generate_item_texture_json(analyzer.items)
        self._generate_terrain_texture_json(analyzer.blocks)
        self._generate_blocks_json(analyzer.blocks)
        self._generate_languages(analyzer.items, analyzer.blocks)
        
        # Empacota
        self._create_mcaddon()
        
        print(f"\n✅ Concluído!")
        print(f"   Items: {self.stats['items']}")
        print(f"   Blocos: {self.stats['blocks']}")
        print(f"   Texturas: {self.stats['textures']}")
    
    def _create_structure(self):
        """Cria pastas"""
        for d in [
            self.bp / "items",
            self.bp / "blocks",
            self.bp / "recipes",
            self.rp / "textures" / "items",
            self.rp / "textures" / "blocks",
            self.rp / "texts"
        ]:
            d.mkdir(parents=True, exist_ok=True)
    
    def _generate_manifests(self):
        """
        ✅ CORREÇÃO CRÍTICA: Vincula BP → RP via dependencies
        """
        
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"§e{self.mod_id.title()}§r BP",
                "description": f"§7Converted from Java Edition\n{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "uuid": self.bp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{
                "type": "data",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }],
            # ✅ CRÍTICO: Vincula ao Resource Pack
            "dependencies": [{
                "uuid": self.rp_uuid,
                "version": [1, 0, 0]
            }]
        }
        
        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"§e{self.mod_id.title()}§r RP",
                "description": "§7Textures and Models",
                "uuid": self.rp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{
                "type": "resources",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            }]
        }
        
        self._save_json(bp_manifest, self.bp / "manifest.json")
        self._save_json(rp_manifest, self.rp / "manifest.json")
        
        print("   ✓ Manifests com UUIDs vinculados")
    
    def _generate_pack_icons(self, textures: Dict[str, bytes]):
        """
        ✅ NOVO: Cria pack_icon.png usando primeira textura
        """
        if not textures:
            print("   ⚠️  Nenhuma textura para ícone")
            return
        
        # Pega primeira textura disponível
        first_texture = next(iter(textures.values()))
        
        # Salva em ambos os packs
        (self.bp / "pack_icon.png").write_bytes(first_texture)
        (self.rp / "pack_icon.png").write_bytes(first_texture)
        
        print("   ✓ pack_icon.png criado")
    
    def _generate_items(self, items: Dict[str, JavaItem]):
        """Gera items no BP"""
        for name, item in items.items():
            try:
                item_json = BedrockConverter.convert_item(item, self.mod_id)
                self._save_json(item_json, self.bp / "items" / f"{name}.json")
                self.stats['items'] += 1
            except Exception as e:
                print(f"⚠️  Item {name}: {e}")
    
    def _generate_blocks(self, blocks: Dict[str, JavaBlock]):
        """Gera blocos no BP"""
        for name, block in blocks.items():
            try:
                block_json = BedrockConverter.convert_block(block, self.mod_id)
                self._save_json(block_json, self.bp / "blocks" / f"{name}.json")
                self.stats['blocks'] += 1
            except Exception as e:
                print(f"⚠️  Bloco {name}: {e}")
    
    def _generate_recipes(self, recipes: List[Dict]):
        """Gera receitas"""
        for recipe in recipes:
            try:
                recipe_type = recipe['data'].get('type', '').split(':')[-1]
                
                if 'shaped' in recipe_type:
                    recipe_json = self._convert_shaped(recipe)
                elif 'shapeless' in recipe_type:
                    recipe_json = self._convert_shapeless(recipe)
                else:
                    continue
                
                if recipe_json:
                    self._save_json(recipe_json, self.bp / "recipes" / f"{recipe['id']}.json")
                    self.stats['recipes'] += 1
            except:
                pass
    
    def _convert_shaped(self, recipe: Dict) -> Dict:
        """Converte receita shaped"""
        data = recipe['data']
        
        return {
            "format_version": "1.20.80",
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{self.mod_id}:{recipe['id']}"},
                "tags": ["crafting_table"],
                "pattern": data.get('pattern', []),
                "key": {
                    k: {"item": self._fix_id(v.get('item', 'minecraft:air'))}
                    for k, v in data.get('key', {}).items()
                },
                "result": {
                    "item": self._fix_id(data.get('result', {}).get('item', 'minecraft:air')),
                    "count": data.get('result', {}).get('count', 1)
                }
            }
        }
    
    def _convert_shapeless(self, recipe: Dict) -> Dict:
        """Converte receita shapeless"""
        data = recipe['data']
        
        ingredients = []
        for ing in data.get('ingredients', []):
            if isinstance(ing, dict) and 'item' in ing:
                ingredients.append({"item": self._fix_id(ing['item'])})
        
        return {
            "format_version": "1.20.80",
            "minecraft:recipe_shapeless": {
                "description": {"identifier": f"{self.mod_id}:{recipe['id']}"},
                "tags": ["crafting_table"],
                "ingredients": ingredients,
                "result": {
                    "item": self._fix_id(data.get('result', {}).get('item', 'minecraft:air')),
                    "count": data.get('result', {}).get('count', 1)
                }
            }
        }
    
    def _fix_id(self, item_id: str) -> str:
        """Normaliza ID"""
        if ':' not in item_id:
            return f"{self.mod_id}:{item_id}"
        parts = item_id.split(':')
        return item_id if parts[0] == 'minecraft' else f"{self.mod_id}:{parts[1]}"
    
    def _copy_textures(self, items: Dict[str, bytes], blocks: Dict[str, bytes]):
        """
        ✅ ORGANIZAÇÃO CORRETA:
        - Items → resource_pack/textures/items/
        - Blocos → resource_pack/textures/blocks/
        """
        
        # Items
        for name, data in items.items():
            try:
                (self.rp / "textures" / "items" / f"{name}.png").write_bytes(data)
                self.stats['textures'] += 1
            except:
                pass
        
        # Blocos
        for name, data in blocks.items():
            try:
                (self.rp / "textures" / "blocks" / f"{name}.png").write_bytes(data)
                self.stats['textures'] += 1
            except:
                pass
        
        print(f"   ✓ {self.stats['textures']} texturas copiadas")
    
    def _generate_item_texture_json(self, items: Dict[str, JavaItem]):
        """
        ✅ MAPEAMENTO ESTRITO:
        - Chave: nome_limpo (ex: "copper_ingot")
        - Valor: caminho completo da textura
        """
        
        texture_data = {}
        
        for name, item in items.items():
            # CHAVE: Nome limpo SEM namespace
            texture_key = item.texture_name
            
            # VALOR: Caminho da textura
            texture_data[texture_key] = {
                "textures": f"textures/items/{item.texture_name}"
            }
        
        item_texture_json = {
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.items",
            "texture_data": texture_data
        }
        
        self._save_json(item_texture_json, self.rp / "textures" / "item_texture.json")
        print("   ✓ item_texture.json (mapeamento estrito)")
    
    def _generate_terrain_texture_json(self, blocks: Dict[str, JavaBlock]):
        """Gera terrain_texture.json para blocos"""
        
        texture_data = {}
        
        for name, block in blocks.items():
            texture_data[block.texture_name] = {
                "textures": f"textures/blocks/{block.texture_name}"
            }
        
        self._save_json({
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.terrain",
            "texture_data": texture_data
        }, self.rp / "textures" / "terrain_texture.json")
        
        print("   ✓ terrain_texture.json")
    
    def _generate_blocks_json(self, blocks: Dict[str, JavaBlock]):
        """Gera blocks.json obrigatório"""
        
        blocks_data = {}
        
        for name, block in blocks.items():
            blocks_data[f"{self.mod_id}:{name}"] = {
                "textures": block.texture_name,
                "sound": "stone"
            }
        
        self._save_json(blocks_data, self.rp / "blocks.json")
        print("   ✓ blocks.json")
    
    def _generate_languages(self, items: Dict, blocks: Dict):
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
    
    def _create_mcaddon(self):
        """Empacota em .mcaddon"""
        
        mcaddon_path = self.output_dir / f"{self.mod_id}.mcaddon"
        
        with zipfile.ZipFile(mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for file in self.bp.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(self.output_dir))
            
            for file in self.rp.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(self.output_dir))
        
        size_kb = mcaddon_path.stat().st_size / 1024
        print(f"   ✓ {mcaddon_path.name} ({size_kb:.1f} KB)")
    
    def _save_json(self, data: Dict, path: Path):
        """Salva JSON"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    """
    Converte JAR para .mcaddon
    
    Returns:
        Dict com success, stats, output_file
    """
    
    print("=" * 70)
    print("🚀 MINECRAFT TRANSPILER v3.1 FINAL")
    print("=" * 70)
    
    start = datetime.now()
    
    try:
        jar_path = Path(jar_path)
        if not jar_path.exists():
            raise FileNotFoundError(f"JAR não encontrado: {jar_path}")
        
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        analyzer = JarAnalyzer(jar_path)
        analyzer.analyze()
        
        generator = AddonGenerator(analyzer.mod_id, output_dir)
        generator.generate(analyzer)
        
        elapsed = (datetime.now() - start).total_seconds()
        
        return {
            'success': True,
            'mod_id': analyzer.mod_id,
            'output_file': str(output_dir / f"{analyzer.mod_id}.mcaddon"),
            'stats': {
                'items_processed': generator.stats['items'],
                'blocks_processed': generator.stats['blocks'],
                'recipes_converted': generator.stats['recipes'],
                'assets_extracted': generator.stats['textures']
            },
            'elapsed_time': f"{elapsed:.2f}s"
        }
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

# ============================================================================
# CLASSE DE COMPATIBILIDADE
# ============================================================================

class AvaritiaTranspiler:
    """Wrapper para compatibilidade com app.py antigo"""
    
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

# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python transpiler_engine.py <mod.jar> [output]")
        print("\nExemplo:")
        print("  python transpiler_engine.py SimpleOres2.jar output/")
        sys.exit(1)
    
    result = transpile_jar(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else "output"
    )
    
    if not result['success']:
        print(f"\n❌ Falhou: {result.get('error')}")
        sys.exit(1)
    else:
        print(f"\n✅ Sucesso! Arquivo: {result['output_file']}")
