#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT JAVA → BEDROCK TRANSPILER ENGINE
==========================================
Versão 2.1 - Com retrocompatibilidade

IMPORTANTE: Este arquivo contém DUAS interfaces:
1. transpile_jar() - Nova interface (recomendada)
2. AvaritiaTranspiler - Classe de compatibilidade para código legado
"""

import json
import zipfile
import re
import uuid
import shutil
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime
import hashlib
import traceback

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class JavaItem:
    """Representação de um Item do Java Edition"""
    identifier: str
    class_name: str = ""
    max_damage: int = 0
    max_stack_size: int = 64
    is_fireproof: bool = False
    armor_value: int = 0
    attack_damage: float = 0.0
    mining_speed: float = 1.0
    rarity: str = "common"
    is_edible: bool = False
    food_value: int = 0
    saturation: float = 0.0
    texture_name: str = ""
    has_custom_behavior: bool = False
    creative_category: str = "items"

@dataclass
class JavaRecipe:
    """Representação de uma Receita do Java Edition"""
    recipe_id: str
    recipe_type: str
    pattern: List[str] = field(default_factory=list)
    key: Dict[str, Any] = field(default_factory=dict)
    ingredients: List[Any] = field(default_factory=list)
    result: Dict[str, Any] = field(default_factory=dict)
    is_extreme: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# ANALISADOR DE JAR
# ============================================================================

class JarAnalyzer:
    """Analisa arquivo JAR e extrai informações"""
    
    ITEM_PATTERNS = {
        'identifier': rb'register\(["\']([^"\']+)["\']',
        'stack_size': rb'stacksTo\((\d+)\)',
        'durability': rb'durability\((\d+)\)',
        'fireproof': rb'fireResistant\(\)',
        'attack_damage': rb'new\s+(?:Sword|Axe)Item\([^,]+,\s*(\d+)',
        'rarity': rb'rarity\(Rarity\.(\w+)\)',
        'food': rb'nutrition\((\d+)\).*?saturationMod\(([\d.]+)\)',
    }
    
    def __init__(self, jar_path: str):
        self.jar_path = Path(jar_path)
        self.mod_id = self._extract_mod_id()
        self.items: Dict[str, JavaItem] = {}
        self.recipes: Dict[str, JavaRecipe] = {}
        self.textures: Dict[str, bytes] = {}
        self.errors: List[str] = []
    
    def _extract_mod_id(self) -> str:
        """Extrai ID do mod do nome do arquivo"""
        name = self.jar_path.stem.lower()
        name = re.sub(r'[-_](forge|fabric|1\.\d+\.?\d*)', '', name)
        name = re.sub(r'[-_]\d+\.?\d*\.?\d*', '', name)
        return re.sub(r'[^a-z0-9_]', '_', name)
    
    def analyze(self):
        """Analisa todo o JAR"""
        print(f"📦 Analisando: {self.jar_path.name}")
        print(f"🆔 Mod ID: {self.mod_id}")
        
        with zipfile.ZipFile(self.jar_path, 'r') as jar:
            file_list = jar.namelist()
            
            for filename in file_list:
                try:
                    if filename.endswith('.class') and '/item/' in filename.lower():
                        self._analyze_item_class(jar, filename)
                    elif 'recipes/' in filename and filename.endswith('.json'):
                        self._analyze_recipe(jar, filename)
                    elif filename.endswith('.png') and '/textures/item' in filename:
                        self._extract_texture(jar, filename)
                except Exception as e:
                    self.errors.append(f"{filename}: {str(e)}")
        
        self._create_default_items()
        
        print(f"✅ Items: {len(self.items)}")
        print(f"✅ Receitas: {len(self.recipes)}")
        print(f"✅ Texturas: {len(self.textures)}")
    
    def _analyze_item_class(self, jar: zipfile.ZipFile, filename: str):
        try:
            bytecode = jar.read(filename)
            item_name = Path(filename).stem
            identifier = re.sub(r'(?<!^)(?=[A-Z])', '_', item_name).lower()
            
            item = JavaItem(identifier=identifier, class_name=filename)
            
            for attr_name, pattern in self.ITEM_PATTERNS.items():
                match = re.search(pattern, bytecode, re.DOTALL | re.IGNORECASE)
                if match:
                    self._process_item_attribute(item, attr_name, match)
            
            item.texture_name = identifier
            self.items[identifier] = item
        except:
            pass
    
    def _process_item_attribute(self, item: JavaItem, attr_name: str, match: re.Match):
        try:
            if attr_name == 'stack_size':
                item.max_stack_size = int(match.group(1))
            elif attr_name == 'durability':
                item.max_damage = int(match.group(1))
            elif attr_name == 'fireproof':
                item.is_fireproof = True
            elif attr_name == 'attack_damage':
                item.attack_damage = float(match.group(1))
                item.creative_category = "equipment"
            elif attr_name == 'rarity':
                item.rarity = match.group(1).decode().lower()
            elif attr_name == 'food':
                item.is_edible = True
                item.food_value = int(match.group(1))
                item.saturation = float(match.group(2))
        except:
            pass
    
    def _analyze_recipe(self, jar: zipfile.ZipFile, filename: str):
        try:
            content = jar.read(filename)
            recipe_data = json.loads(content)
            recipe_id = Path(filename).stem
            recipe_type = recipe_data.get('type', '').split(':')[-1]
            
            recipe = JavaRecipe(
                recipe_id=recipe_id,
                recipe_type=recipe_type,
                raw_data=recipe_data
            )
            
            if 'pattern' in recipe_data:
                recipe.pattern = recipe_data['pattern']
                recipe.key = recipe_data.get('key', {})
            elif 'ingredients' in recipe_data:
                recipe.ingredients = recipe_data['ingredients']
            elif 'primary' in recipe_data or 'secondary' in recipe_data:
                recipe.ingredients = [
                    recipe_data.get('primary', {}),
                    recipe_data.get('secondary', {})
                ]
            
            recipe.result = recipe_data.get('result', {})
            
            if len(recipe.pattern) > 3 or any(len(p) > 3 for p in recipe.pattern):
                recipe.is_extreme = True
            
            self.recipes[recipe_id] = recipe
        except:
            pass
    
    def _extract_texture(self, jar: zipfile.ZipFile, filename: str):
        try:
            texture_name = Path(filename).stem
            texture_data = jar.read(filename)
            self.textures[texture_name] = texture_data
        except:
            pass
    
    def _create_default_items(self):
        for texture_name in self.textures.keys():
            if texture_name not in self.items:
                self.items[texture_name] = JavaItem(
                    identifier=texture_name,
                    texture_name=texture_name,
                    max_stack_size=64
                )

# ============================================================================
# CONVERSOR BEDROCK
# ============================================================================

class BedrockConverter:
    """Converte para formato Bedrock"""
    
    FORMAT_VERSION = "1.20.80"
    
    @staticmethod
    def convert_item(item: JavaItem, mod_id: str) -> Dict[str, Any]:
        bedrock_item = {
            "format_version": BedrockConverter.FORMAT_VERSION,
            "minecraft:item": {
                "description": {
                    "identifier": f"{mod_id}:{item.identifier}",
                    "menu_category": {
                        "category": item.creative_category,
                        "group": f"itemGroup.name.{mod_id}"
                    }
                },
                "components": {
                    "minecraft:max_stack_size": item.max_stack_size
                }
            }
        }
        
        components = bedrock_item["minecraft:item"]["components"]
        
        if item.max_damage > 0:
            components["minecraft:durability"] = {
                "max_durability": min(item.max_damage, 32767)
            }
        
        if item.is_fireproof:
            components["minecraft:ignores_damage"] = True
        
        if item.attack_damage > 0:
            components["minecraft:damage"] = item.attack_damage
        
        if item.armor_value > 0:
            components["minecraft:armor"] = {"protection": item.armor_value}
        
        if item.is_edible:
            components["minecraft:food"] = {
                "nutrition": item.food_value,
                "saturation_modifier": item.saturation
            }
        
        if item.mining_speed > 1.0:
            components["minecraft:digger"] = {
                "use_efficiency": True,
                "destroy_speeds": [{
                    "block": "minecraft:stone",
                    "speed": int(item.mining_speed)
                }]
            }
        
        return bedrock_item
    
    @staticmethod
    def convert_recipe(recipe: JavaRecipe, mod_id: str) -> Optional[Dict[str, Any]]:
        if recipe.is_extreme:
            return None
        
        if recipe.pattern:
            return BedrockConverter._convert_shaped_recipe(recipe, mod_id)
        elif recipe.ingredients:
            return BedrockConverter._convert_shapeless_recipe(recipe, mod_id)
        elif 'primary' in recipe.raw_data:
            return BedrockConverter._convert_custom_recipe(recipe, mod_id)
        
        return None
    
    @staticmethod
    def _convert_shaped_recipe(recipe: JavaRecipe, mod_id: str) -> Dict[str, Any]:
        bedrock_recipe = {
            "format_version": BedrockConverter.FORMAT_VERSION,
            "minecraft:recipe_shaped": {
                "description": {"identifier": f"{mod_id}:{recipe.recipe_id}"},
                "tags": ["crafting_table"],
                "pattern": recipe.pattern,
                "key": {},
                "result": BedrockConverter._convert_result(recipe.result, mod_id)
            }
        }
        
        for symbol, ingredient in recipe.key.items():
            bedrock_recipe["minecraft:recipe_shaped"]["key"][symbol] = \
                BedrockConverter._convert_ingredient(ingredient, mod_id)
        
        return bedrock_recipe
    
    @staticmethod
    def _convert_shapeless_recipe(recipe: JavaRecipe, mod_id: str) -> Dict[str, Any]:
        ingredients = []
        for ingredient in recipe.ingredients:
            converted = BedrockConverter._convert_ingredient(ingredient, mod_id)
            if converted:
                ingredients.append(converted)
        
        return {
            "format_version": BedrockConverter.FORMAT_VERSION,
            "minecraft:recipe_shapeless": {
                "description": {"identifier": f"{mod_id}:{recipe.recipe_id}"},
                "tags": ["crafting_table"],
                "ingredients": ingredients,
                "result": BedrockConverter._convert_result(recipe.result, mod_id)
            }
        }
    
    @staticmethod
    def _convert_custom_recipe(recipe: JavaRecipe, mod_id: str) -> Dict[str, Any]:
        ingredients = []
        
        if 'primary' in recipe.raw_data:
            ingredients.append(BedrockConverter._convert_ingredient(
                recipe.raw_data['primary'], mod_id
            ))
        if 'secondary' in recipe.raw_data:
            ingredients.append(BedrockConverter._convert_ingredient(
                recipe.raw_data['secondary'], mod_id
            ))
        
        return {
            "format_version": BedrockConverter.FORMAT_VERSION,
            "minecraft:recipe_shapeless": {
                "description": {"identifier": f"{mod_id}:{recipe.recipe_id}"},
                "tags": ["crafting_table"],
                "ingredients": ingredients,
                "result": BedrockConverter._convert_result(recipe.result, mod_id)
            }
        }
    
    @staticmethod
    def _convert_ingredient(ingredient: Any, mod_id: str) -> Dict[str, Any]:
        if not ingredient:
            return {"item": "minecraft:air"}
        
        if isinstance(ingredient, str):
            return {"item": BedrockConverter._normalize_item_id(ingredient, mod_id)}
        
        if isinstance(ingredient, dict):
            if 'item' in ingredient:
                return {
                    "item": BedrockConverter._normalize_item_id(ingredient['item'], mod_id),
                    "count": ingredient.get('count', 1)
                }
            elif 'tag' in ingredient:
                tag = ingredient['tag']
                return {"item": f"minecraft:{tag.split('/')[-1]}"}
        
        return {"item": "minecraft:air"}
    
    @staticmethod
    def _convert_result(result: Any, mod_id: str) -> Dict[str, Any]:
        if isinstance(result, str):
            return {
                "item": BedrockConverter._normalize_item_id(result, mod_id),
                "count": 1
            }
        
        if isinstance(result, dict):
            item_id = result.get('item', result.get('id', 'minecraft:air'))
            return {
                "item": BedrockConverter._normalize_item_id(item_id, mod_id),
                "count": result.get('count', 1)
            }
        
        return {"item": "minecraft:air", "count": 1}
    
    @staticmethod
    def _normalize_item_id(item_id: str, mod_id: str) -> str:
        if item_id.startswith(f'{mod_id}:') or item_id.startswith('minecraft:'):
            return item_id
        
        if ':' not in item_id:
            return f"{mod_id}:{item_id}"
        
        parts = item_id.split(':')
        if len(parts) == 2:
            return f"{mod_id}:{parts[1]}"
        
        return item_id

# ============================================================================
# GERADOR DE ADDON
# ============================================================================

class AddonGenerator:
    """Gera estrutura do addon"""
    
    def __init__(self, mod_id: str, output_dir: Path):
        self.mod_id = mod_id
        self.output_dir = output_dir
        self.bp_dir = output_dir / "behavior_pack"
        self.rp_dir = output_dir / "resource_pack"
        self.stats = {
            'items_created': 0,
            'recipes_created': 0,
            'textures_copied': 0,
            'errors': []
        }
    
    def generate(self, analyzer: JarAnalyzer):
        print("\n🔨 Gerando Addon...")
        
        self._create_folders()
        self._generate_manifests()
        self._generate_items(analyzer.items)
        self._generate_recipes(analyzer.recipes)
        self._copy_textures(analyzer.textures)
        self._generate_texture_mapping(analyzer.items, analyzer.textures)
        self._generate_language_files(analyzer.items)
        self._create_mcaddon()
        
        print(f"✅ Addon gerado!")
        print(f"   Items: {self.stats['items_created']}")
        print(f"   Receitas: {self.stats['recipes_created']}")
        print(f"   Texturas: {self.stats['textures_copied']}")
    
    def _create_folders(self):
        folders = [
            self.bp_dir / "items",
            self.bp_dir / "recipes",
            self.rp_dir / "textures" / "items",
            self.rp_dir / "texts"
        ]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
    
    def _generate_manifests(self):
        bp_uuid = str(uuid.uuid4())
        rp_uuid = str(uuid.uuid4())
        
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} BP",
                "description": f"Converted from Java\n{datetime.now().strftime('%Y-%m-%d')}",
                "uuid": bp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}],
            "dependencies": [{"uuid": rp_uuid, "version": [1, 0, 0]}]
        }
        
        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} RP",
                "description": "Textures",
                "uuid": rp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{"type": "resources", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}]
        }
        
        self._save_json(bp_manifest, self.bp_dir / "manifest.json")
        self._save_json(rp_manifest, self.rp_dir / "manifest.json")
    
    def _generate_items(self, items: Dict[str, JavaItem]):
        for identifier, item in items.items():
            try:
                bedrock_item = BedrockConverter.convert_item(item, self.mod_id)
                self._save_json(bedrock_item, self.bp_dir / "items" / f"{identifier}.json")
                self.stats['items_created'] += 1
            except Exception as e:
                self.stats['errors'].append(f"Item {identifier}: {str(e)}")
    
    def _generate_recipes(self, recipes: Dict[str, JavaRecipe]):
        for recipe_id, recipe in recipes.items():
            try:
                bedrock_recipe = BedrockConverter.convert_recipe(recipe, self.mod_id)
                if bedrock_recipe:
                    self._save_json(bedrock_recipe, self.bp_dir / "recipes" / f"{recipe_id}.json")
                    self.stats['recipes_created'] += 1
            except Exception as e:
                self.stats['errors'].append(f"Recipe {recipe_id}: {str(e)}")
    
    def _copy_textures(self, textures: Dict[str, bytes]):
        for name, data in textures.items():
            try:
                (self.rp_dir / "textures" / "items" / f"{name}.png").write_bytes(data)
                self.stats['textures_copied'] += 1
            except:
                pass
    
    def _generate_texture_mapping(self, items: Dict[str, JavaItem], textures: Dict[str, bytes]):
        texture_data = {}
        for identifier, item in items.items():
            texture_name = item.texture_name or identifier
            if texture_name in textures:
                texture_data[f"{self.mod_id}:{identifier}"] = {
                    "textures": f"textures/items/{texture_name}"
                }
        
        self._save_json(
            {
                "resource_pack_name": self.mod_id,
                "texture_name": "atlas.items",
                "texture_data": texture_data
            },
            self.rp_dir / "textures" / "item_texture.json"
        )
    
    def _generate_language_files(self, items: Dict[str, JavaItem]):
        self._save_json(
            {"languages": ["en_US"]},
            self.rp_dir / "texts" / "languages.json"
        )
        
        lang_entries = [
            f"item.{self.mod_id}:{id}.name={id.replace('_', ' ').title()}"
            for id in items.keys()
        ]
        (self.rp_dir / "texts" / "en_US.lang").write_text("\n".join(lang_entries), encoding='utf-8')
    
    def _create_mcaddon(self):
        mcaddon_path = self.output_dir / f"{self.mod_id}.mcaddon"
        
        with zipfile.ZipFile(mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for file in self.bp_dir.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(self.output_dir))
            for file in self.rp_dir.rglob("*"):
                if file.is_file():
                    z.write(file, file.relative_to(self.output_dir))
    
    def _save_json(self, data: Dict, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    """
    FUNÇÃO PRINCIPAL DE TRANSPILAÇÃO
    
    Args:
        jar_path: Caminho do .jar
        output_folder: Pasta de saída
    
    Returns:
        Dict com resultado e estatísticas
    """
    print("=" * 70)
    print("🚀 MINECRAFT TRANSPILER v2.1")
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
                'items_processed': generator.stats['items_created'],
                'recipes_converted': generator.stats['recipes_created'],
                'assets_extracted': generator.stats['textures_copied'],
                'errors': len(generator.stats['errors'])
            },
            'elapsed_time': f"{elapsed:.2f}s"
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

# ============================================================================
# CLASSE DE COMPATIBILIDADE (PARA APP.PY ANTIGO)
# ============================================================================

class AvaritiaTranspiler:
    """
    Classe wrapper para retrocompatibilidade com app.py antigo
    """
    
    def __init__(self, jar_path: str, output_dir: str, mod_name: str = ""):
        self.jar_path = jar_path
        self.output_dir = output_dir
        self.mod_name = mod_name
        self.stats = {
            'items_processed': 0,
            'recipes_converted': 0,
            'scripts_generated': 0,
            'assets_extracted': 0,
            'errors': []
        }
    
    def run(self):
        """Executa transpilação (compatibilidade)"""
        result = transpile_jar(self.jar_path, self.output_dir)
        
        if result['success']:
            self.stats = result['stats']
        else:
            raise Exception(result.get('error', 'Erro desconhecido'))
    
    def parse_jar(self):
        pass
    
    def convert_all(self):
        pass
    
    def generate_scripts(self):
        pass
    
    def build_addon_structure(self):
        pass
    
    def package_mcaddon(self):
        pass
    
    def print_report(self):
        print(f"Items: {self.stats.get('items_processed', 0)}")
        print(f"Receitas: {self.stats.get('recipes_converted', 0)}")

# ============================================================================
# TESTE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python transpiler_engine.py <mod.jar> [output]")
        sys.exit(1)
    
    result = transpile_jar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "output")
    
    if not result['success']:
        print(f"ERRO: {result['error']}")
        sys.exit(1)
