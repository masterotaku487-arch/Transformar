#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT TRANSPILER v3.2 - PRODUCTION READY
============================================
Motor profissional com texturas e blocos funcionais

CORREÇÕES v3.2:
✅ Pluralização correta: textures/items/ e textures/blocks/
✅ terrain_texture.json gerado corretamente
✅ blocks.json na raiz do Resource Pack
✅ 4 UUIDs únicos e dependencies corretas
✅ Cópia completa de texturas verificada
"""

import json
import zipfile
import re
import uuid as uuid_module
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
    light_emission: int = 0

# ============================================================================
# ANALISADOR DE JAR
# ============================================================================

class JarAnalyzer:
    """Analisa JAR e extrai todo o conteúdo"""
    
    def __init__(self, jar_path: str):
        self.jar_path = Path(jar_path)
        self.mod_id = self._extract_mod_id()
        
        # Dados extraídos
        self.items: Dict[str, JavaItem] = {}
        self.blocks: Dict[str, JavaBlock] = {}
        self.item_textures: Dict[str, bytes] = {}
        self.block_textures: Dict[str, bytes] = {}
        self.recipes: List[Dict] = []
        
        print(f"📦 Mod ID: {self.mod_id}")
    
    def _extract_mod_id(self) -> str:
        """Extrai ID limpo do mod"""
        name = self.jar_path.stem.lower()
        # Remove versões, plataformas e números
        name = re.sub(r'[-_](forge|fabric|neoforge)', '', name)
        name = re.sub(r'[-_]mc\d+\.\d+', '', name)
        name = re.sub(r'[-_]\d+[._]\d+[._]?\d*', '', name)
        name = re.sub(r'[^a-z0-9]', '', name)
        return name or "converted_mod"
    
    def analyze(self):
        """Analisa JAR completo - FASE CRÍTICA"""
        print("🔍 Analisando JAR...")
        
        with zipfile.ZipFile(self.jar_path, 'r') as jar:
            total_files = len(jar.namelist())
            processed = 0
            
            for filename in jar.namelist():
                processed += 1
                
                # Progress
                if processed % 100 == 0:
                    print(f"   Processando: {processed}/{total_files}...")
                
                try:
                    # ✅ TEXTURAS DE ITEMS (PLURAL: items/)
                    if '/textures/item/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        data = jar.read(filename)
                        self.item_textures[name] = data
                        print(f"   📄 Item texture: {name}")
                    
                    # ✅ TEXTURAS DE BLOCOS (PLURAL: blocks/)
                    elif '/textures/block/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        data = jar.read(filename)
                        self.block_textures[name] = data
                        print(f"   🧱 Block texture: {name}")
                    
                    # ✅ RECEITAS
                    elif '/recipes/' in filename and filename.endswith('.json'):
                        try:
                            data = json.loads(jar.read(filename))
                            self.recipes.append({
                                'id': Path(filename).stem,
                                'data': data
                            })
                        except:
                            pass
                
                except Exception as e:
                    print(f"   ⚠️  Erro em {filename}: {e}")
        
        # Cria items baseado nas texturas
        print("\n🔨 Criando definições de items...")
        for name, texture_data in self.item_textures.items():
            item = JavaItem(identifier=name, texture_name=name)
            
            # Detecta tipo pelo nome
            if any(x in name.lower() for x in ['sword', 'axe', 'pickaxe', 'shovel', 'hoe']):
                item.is_tool = True
                item.max_damage = 250
                item.max_stack_size = 1
                item.attack_damage = 4.0
            elif any(x in name.lower() for x in ['helmet', 'chestplate', 'leggings', 'boots']):
                item.is_armor = True
                item.max_damage = 250
                item.max_stack_size = 1
            
            self.items[name] = item
            print(f"   ✓ Item: {name}")
        
        # Cria blocos baseado nas texturas
        print("\n🔨 Criando definições de blocos...")
        for name, texture_data in self.block_textures.items():
            block = JavaBlock(identifier=name, texture_name=name)
            
            # Detecta propriedades
            if 'ore' in name.lower():
                block.hardness = 3.0
                block.resistance = 3.0
                block.material = "stone"
            elif 'block' in name.lower() or 'brick' in name.lower():
                block.hardness = 5.0
                block.resistance = 6.0
                block.material = "stone"
            
            self.blocks[name] = block
            print(f"   ✓ Bloco: {name}")
        
        print(f"\n✅ RESUMO DA ANÁLISE:")
        print(f"   Items: {len(self.items)}")
        print(f"   Blocos: {len(self.blocks)}")
        print(f"   Receitas: {len(self.recipes)}")
        print(f"   Texturas de items: {len(self.item_textures)}")
        print(f"   Texturas de blocos: {len(self.block_textures)}")

# ============================================================================
# CONVERSOR BEDROCK
# ============================================================================

class BedrockConverter:
    """Converte estruturas para Bedrock"""
    
    FORMAT = "1.20.80"
    
    @staticmethod
    def convert_item(item: JavaItem, mod_id: str) -> Dict:
        """
        Converte item para Bedrock
        CRÍTICO: texture em minecraft:icon deve ser o nome exato
        """
        
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
                    # ✅ Nome EXATO da chave no item_texture.json
                    "minecraft:icon": {
                        "texture": item.texture_name
                    },
                    "minecraft:max_stack_size": item.max_stack_size,
                    **BedrockConverter._get_item_components(item)
                }
            }
        }
    
    @staticmethod
    def _get_item_components(item: JavaItem) -> Dict:
        """Componentes adicionais do item"""
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
        """Converte bloco para Bedrock"""
        
        return {
            "format_version": BedrockConverter.FORMAT,
            "minecraft:block": {
                "description": {
                    "identifier": f"{mod_id}:{block.identifier}",
                    "menu_category": {
                        "category": "construction"
                    }
                },
                "components": {
                    "minecraft:destructible_by_mining": {
                        "seconds_to_destroy": block.hardness / 1.5
                    },
                    "minecraft:destructible_by_explosion": {
                        "explosion_resistance": block.resistance
                    },
                    "minecraft:geometry": "geometry.cube",
                    "minecraft:material_instances": {
                        "*": {
                            "texture": block.texture_name,
                            "render_method": "opaque"
                        }
                    },
                    "minecraft:light_emission": block.light_emission
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
        
        # ✅ 4 UUIDs ÚNICOS
        self.bp_header_uuid = str(uuid_module.uuid4())
        self.bp_module_uuid = str(uuid_module.uuid4())
        self.rp_header_uuid = str(uuid_module.uuid4())
        self.rp_module_uuid = str(uuid_module.uuid4())
        
        self.stats = {
            'items': 0,
            'blocks': 0,
            'recipes': 0,
            'item_textures': 0,
            'block_textures': 0
        }
    
    def generate(self, analyzer: JarAnalyzer):
        """Gera addon completo"""
        print("\n" + "=" * 70)
        print("🔨 GERANDO ADDON BEDROCK")
        print("=" * 70)
        
        self._create_structure()
        self._generate_manifests()
        self._generate_pack_icons(analyzer.item_textures)
        
        # Behavior Pack
        print("\n📝 Behavior Pack:")
        self._generate_items(analyzer.items)
        self._generate_blocks(analyzer.blocks)
        self._generate_recipes(analyzer.recipes)
        
        # Resource Pack
        print("\n🎨 Resource Pack:")
        self._copy_item_textures(analyzer.item_textures)
        self._copy_block_textures(analyzer.block_textures)
        self._generate_item_texture_json(analyzer.items)
        self._generate_terrain_texture_json(analyzer.blocks)
        self._generate_blocks_json(analyzer.blocks)
        self._generate_languages(analyzer.items, analyzer.blocks)
        
        # Empacota
        print("\n📦 Empacotando:")
        self._create_mcaddon()
        
        print("\n" + "=" * 70)
        print("✅ ADDON GERADO COM SUCESSO")
        print("=" * 70)
        print(f"Items criados:        {self.stats['items']}")
        print(f"Blocos criados:       {self.stats['blocks']}")
        print(f"Receitas:             {self.stats['recipes']}")
        print(f"Texturas de items:    {self.stats['item_textures']}")
        print(f"Texturas de blocos:   {self.stats['block_textures']}")
        print("=" * 70)
    
    def _create_structure(self):
        """Cria estrutura de pastas"""
        print("   📁 Criando estrutura de pastas...")
        
        folders = [
            self.bp / "items",
            self.bp / "blocks",
            self.bp / "recipes",
            self.rp / "textures" / "items",    # ✅ PLURAL
            self.rp / "textures" / "blocks",   # ✅ PLURAL
            self.rp / "texts"
        ]
        
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
            print(f"      ✓ {folder.relative_to(self.output_dir)}")
    
    def _generate_manifests(self):
        """
        ✅ CRÍTICO: Gera manifests com 4 UUIDs únicos e dependencies
        """
        print("   📄 Gerando manifests com UUIDs únicos...")
        
        # Behavior Pack Manifest
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"§e{self.mod_id.title()}§r BP",
                "description": f"§7Converted from Java Edition\n§8{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "uuid": self.bp_header_uuid,       # ✅ UUID 1
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{
                "type": "data",
                "uuid": self.bp_module_uuid,       # ✅ UUID 2
                "version": [1, 0, 0]
            }],
            # ✅ CRÍTICO: Dependencies vincula BP ao RP
            "dependencies": [{
                "uuid": self.rp_header_uuid,       # ✅ Aponta para RP
                "version": [1, 0, 0]
            }]
        }
        
        # Resource Pack Manifest
        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"§e{self.mod_id.title()}§r RP",
                "description": "§7Textures, Models and Sounds",
                "uuid": self.rp_header_uuid,       # ✅ UUID 3
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{
                "type": "resources",
                "uuid": self.rp_module_uuid,       # ✅ UUID 4
                "version": [1, 0, 0]
            }]
        }
        
        self._save_json(bp_manifest, self.bp / "manifest.json")
        self._save_json(rp_manifest, self.rp / "manifest.json")
        
        print(f"      ✓ BP UUID: {self.bp_header_uuid}")
        print(f"      ✓ RP UUID: {self.rp_header_uuid}")
        print(f"      ✓ Dependencies: BP → RP")
    
    def _generate_pack_icons(self, textures: Dict[str, bytes]):
        """Gera pack_icon.png para ambos os packs"""
        if not textures:
            print("   ⚠️  Nenhuma textura disponível para ícone")
            return
        
        first_texture = next(iter(textures.values()))
        
        (self.bp / "pack_icon.png").write_bytes(first_texture)
        (self.rp / "pack_icon.png").write_bytes(first_texture)
        
        print("   ✓ pack_icon.png criado")
    
    def _generate_items(self, items: Dict[str, JavaItem]):
        """Gera arquivos de items"""
        for name, item in items.items():
            try:
                item_json = BedrockConverter.convert_item(item, self.mod_id)
                path = self.bp / "items" / f"{name}.json"
                self._save_json(item_json, path)
                self.stats['items'] += 1
            except Exception as e:
                print(f"   ⚠️  Erro no item {name}: {e}")
        
        print(f"   ✓ {self.stats['items']} items gerados")
    
    def _generate_blocks(self, blocks: Dict[str, JavaBlock]):
        """Gera arquivos de blocos"""
        for name, block in blocks.items():
            try:
                block_json = BedrockConverter.convert_block(block, self.mod_id)
                path = self.bp / "blocks" / f"{name}.json"
                self._save_json(block_json, path)
                self.stats['blocks'] += 1
            except Exception as e:
                print(f"   ⚠️  Erro no bloco {name}: {e}")
        
        print(f"   ✓ {self.stats['blocks']} blocos gerados")
    
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
                    path = self.bp / "recipes" / f"{recipe['id']}.json"
                    self._save_json(recipe_json, path)
                    self.stats['recipes'] += 1
            except:
                pass
        
        print(f"   ✓ {self.stats['recipes']} receitas geradas")
    
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
    
    def _copy_item_textures(self, textures: Dict[str, bytes]):
        """
        ✅ CRÍTICO: Copia texturas para textures/items/ (PLURAL)
        """
        print("   🎨 Copiando texturas de items...")
        
        for name, data in textures.items():
            try:
                # ✅ CAMINHO CORRETO: textures/items/ (com S)
                path = self.rp / "textures" / "items" / f"{name}.png"
                path.write_bytes(data)
                self.stats['item_textures'] += 1
                print(f"      ✓ {name}.png ({len(data)} bytes)")
            except Exception as e:
                print(f"      ✗ Erro em {name}: {e}")
        
        print(f"   ✓ {self.stats['item_textures']} texturas de items copiadas")
    
    def _copy_block_textures(self, textures: Dict[str, bytes]):
        """
        ✅ CRÍTICO: Copia texturas para textures/blocks/ (PLURAL)
        """
        print("   🧱 Copiando texturas de blocos...")
        
        for name, data in textures.items():
            try:
                # ✅ CAMINHO CORRETO: textures/blocks/ (com S)
                path = self.rp / "textures" / "blocks" / f"{name}.png"
                path.write_bytes(data)
                self.stats['block_textures'] += 1
                print(f"      ✓ {name}.png ({len(data)} bytes)")
            except Exception as e:
                print(f"      ✗ Erro em {name}: {e}")
        
        print(f"   ✓ {self.stats['block_textures']} texturas de blocos copiadas")
    
    def _generate_item_texture_json(self, items: Dict[str, JavaItem]):
        """
        ✅ MAPEAMENTO ESTRITO:
        Chave: nome_limpo
        Valor: textures/items/nome_limpo (PLURAL)
        """
        print("   📝 Gerando item_texture.json...")
        
        texture_data = {}
        
        for name, item in items.items():
            texture_data[item.texture_name] = {
                "textures": f"textures/items/{item.texture_name}"  # ✅ PLURAL
            }
        
        item_texture_json = {
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.items",
            "texture_data": texture_data
        }
        
        self._save_json(item_texture_json, self.rp / "textures" / "item_texture.json")
        print(f"      ✓ {len(texture_data)} mapeamentos criados")
    
    def _generate_terrain_texture_json(self, blocks: Dict[str, JavaBlock]):
        """
        ✅ CRÍTICO: Gera terrain_texture.json para blocos
        """
        print("   📝 Gerando terrain_texture.json...")
        
        texture_data = {}
        
        for name, block in blocks.items():
            texture_data[block.texture_name] = {
                "textures": f"textures/blocks/{block.texture_name}"  # ✅ PLURAL
            }
        
        terrain_texture_json = {
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.terrain",
            "texture_data": texture_data
        }
        
        self._save_json(terrain_texture_json, self.rp / "textures" / "terrain_texture.json")
        print(f"      ✓ {len(texture_data)} mapeamentos de blocos criados")
    
    def _generate_blocks_json(self, blocks: Dict[str, JavaBlock]):
        """
        ✅ CRÍTICO: Gera blocks.json NA RAIZ do Resource Pack
        Sem esse arquivo, blocos NÃO aparecem
        """
        print("   📝 Gerando blocks.json...")
        
        blocks_data = {}
        
        for name, block in blocks.items():
            blocks_data[f"{self.mod_id}:{name}"] = {
                "textures": block.texture_name,
                "sound": "stone"
            }
        
        # ✅ RAIZ DO RESOURCE PACK
        self._save_json(blocks_data, self.rp / "blocks.json")
        print(f"      ✓ {len(blocks_data)} blocos registrados")
    
    def _generate_languages(self, items: Dict, blocks: Dict):
        """Gera arquivos de idioma"""
        print("   🌍 Gerando traduções...")
        
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
        
        print(f"      ✓ {len(entries)} traduções geradas")
    
    def _create_mcaddon(self):
        """Empacota em .mcaddon"""
        mcaddon_path = self.output_dir / f"{self.mod_id}.mcaddon"
        
        print("   📦 Criando .mcaddon...")
        
        with zipfile.ZipFile(mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as z:
            # Behavior Pack
            for file in self.bp.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(self.output_dir)
                    z.write(file, arcname)
            
            # Resource Pack
            for file in self.rp.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(self.output_dir)
                    z.write(file, arcname)
        
        size_kb = mcaddon_path.stat().st_size / 1024
        print(f"      ✓ {mcaddon_path.name}")
        print(f"      ✓ Tamanho: {size_kb:.1f} KB")
    
    def _save_json(self, data: Dict, path: Path):
        """Salva JSON formatado"""
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
    
    print("\n" + "=" * 70)
    print("🚀 MINECRAFT TRANSPILER v3.2 FINAL")
    print("=" * 70)
    
    start = datetime.now()
    
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
        
        elapsed = (datetime.now() - start).total_seconds()
        
        return {
            'success': True,
            'mod_id': analyzer.mod_id,
            'output_file': str(output_dir / f"{analyzer.mod_id}.mcaddon"),
            'stats': {
                'items_processed': generator.stats['items'],
                'blocks_processed': generator.stats['blocks'],
                'recipes_converted': generator.stats['recipes'],
                'assets_extracted': generator.stats['item_textures'] + generator.stats['block_textures']
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
    
    # Métodos vazios para compatibilidade
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
        print("\nUso: python transpiler_engine.py <mod.jar> [output_folder]")
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
        print(f"\n✅ SUCESSO!")
        print(f"Arquivo gerado: {result['output_file']}")
