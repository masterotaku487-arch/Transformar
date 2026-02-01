#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT JAVA → BEDROCK TRANSPILER ENGINE
==========================================
Motor completo de conversão de mods Java Edition para Bedrock Edition

Autor: Sistema de Transpilação Profissional
Versão: 2.0.0
Data: 2025-01-31

Características:
- Processamento de receitas customizadas
- Criação automática de items (Behavior Pack)
- Mapeamento completo de texturas
- Compatibilidade com 1.20.80
- Extração inteligente de assets
- Geração de manifests UUID únicos
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
    """Analisa arquivo JAR e extrai informações de items e receitas"""
    
    # Padrões de detecção melhorados
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
        # Remove versão e plataforma
        name = re.sub(r'[-_](forge|fabric|1\.\d+\.?\d*)', '', name)
        name = re.sub(r'[-_]\d+\.?\d*\.?\d*', '', name)
        return re.sub(r'[^a-z0-9_]', '_', name)
    
    def analyze(self):
        """Analisa todo o JAR"""
        print(f"📦 Analisando JAR: {self.jar_path.name}")
        print(f"🆔 Mod ID detectado: {self.mod_id}")
        
        with zipfile.ZipFile(self.jar_path, 'r') as jar:
            # Fase 1: Escanear estrutura
            file_list = jar.namelist()
            
            # Fase 2: Processar arquivos
            for filename in file_list:
                try:
                    # Items de classes Java
                    if filename.endswith('.class') and '/item/' in filename.lower():
                        self._analyze_item_class(jar, filename)
                    
                    # Receitas JSON
                    elif 'recipes/' in filename and filename.endswith('.json'):
                        self._analyze_recipe(jar, filename)
                    
                    # Texturas PNG
                    elif filename.endswith('.png') and '/textures/item' in filename:
                        self._extract_texture(jar, filename)
                    
                except Exception as e:
                    self.errors.append(f"Erro em {filename}: {str(e)}")
        
        # Fase 3: Criar items padrão se não encontrados
        self._create_default_items()
        
        print(f"✅ Items encontrados: {len(self.items)}")
        print(f"✅ Receitas encontradas: {len(self.recipes)}")
        print(f"✅ Texturas extraídas: {len(self.textures)}")
        if self.errors:
            print(f"⚠️  Avisos: {len(self.errors)}")
    
    def _analyze_item_class(self, jar: zipfile.ZipFile, filename: str):
        """Analisa classe Java de item"""
        try:
            bytecode = jar.read(filename)
            
            # Extrai nome do item do caminho
            item_name = Path(filename).stem
            identifier = re.sub(r'(?<!^)(?=[A-Z])', '_', item_name).lower()
            
            # Cria item
            item = JavaItem(
                identifier=identifier,
                class_name=filename
            )
            
            # Analisa atributos
            for attr_name, pattern in self.ITEM_PATTERNS.items():
                match = re.search(pattern, bytecode, re.DOTALL | re.IGNORECASE)
                if match:
                    self._process_item_attribute(item, attr_name, match)
            
            # Detecta textura
            item.texture_name = identifier
            
            self.items[identifier] = item
            
        except Exception as e:
            self.errors.append(f"Item class {filename}: {str(e)}")
    
    def _process_item_attribute(self, item: JavaItem, attr_name: str, match: re.Match):
        """Processa atributo encontrado"""
        try:
            if attr_name == 'identifier':
                # Usa identifier do registro se encontrado
                custom_id = match.group(1).decode('utf-8', errors='ignore')
                if custom_id:
                    item.identifier = custom_id.split(':')[-1]
            
            elif attr_name == 'stack_size':
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
        
        except Exception as e:
            pass  # Silenciosamente ignora erros de parsing
    
    def _analyze_recipe(self, jar: zipfile.ZipFile, filename: str):
        """Analisa arquivo de receita JSON"""
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
            
            # Processa diferentes formatos de receita
            if 'pattern' in recipe_data:
                recipe.pattern = recipe_data['pattern']
                recipe.key = recipe_data.get('key', {})
            
            elif 'ingredients' in recipe_data:
                recipe.ingredients = recipe_data['ingredients']
            
            # Formatos customizados (primary/secondary)
            elif 'primary' in recipe_data or 'secondary' in recipe_data:
                recipe.ingredients = [
                    recipe_data.get('primary', {}),
                    recipe_data.get('secondary', {})
                ]
            
            # Resultado
            recipe.result = recipe_data.get('result', {})
            
            # Detecta extreme crafting
            if len(recipe.pattern) > 3 or any(len(p) > 3 for p in recipe.pattern):
                recipe.is_extreme = True
            
            self.recipes[recipe_id] = recipe
            
        except Exception as e:
            self.errors.append(f"Recipe {filename}: {str(e)}")
    
    def _extract_texture(self, jar: zipfile.ZipFile, filename: str):
        """Extrai textura PNG"""
        try:
            texture_name = Path(filename).stem
            texture_data = jar.read(filename)
            self.textures[texture_name] = texture_data
        except Exception as e:
            self.errors.append(f"Texture {filename}: {str(e)}")
    
    def _create_default_items(self):
        """Cria items padrão baseado em texturas se não foram detectados"""
        for texture_name in self.textures.keys():
            if texture_name not in self.items:
                self.items[texture_name] = JavaItem(
                    identifier=texture_name,
                    texture_name=texture_name,
                    max_stack_size=64
                )
                print(f"   ℹ️  Item criado automaticamente: {texture_name}")

# ============================================================================
# CONVERSOR BEDROCK
# ============================================================================

class BedrockConverter:
    """Converte estruturas Java para formato Bedrock"""
    
    FORMAT_VERSION = "1.20.80"
    
    @staticmethod
    def convert_item(item: JavaItem, mod_id: str) -> Dict[str, Any]:
        """
        Converte JavaItem para formato Bedrock
        GARANTE que SEMPRE retorna um JSON válido
        """
        
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
                "components": {}
            }
        }
        
        components = bedrock_item["minecraft:item"]["components"]
        
        # Stack Size (SEMPRE presente)
        components["minecraft:max_stack_size"] = item.max_stack_size
        
        # Durabilidade
        if item.max_damage > 0:
            components["minecraft:durability"] = {
                "max_durability": min(item.max_damage, 32767)
            }
        
        # Fireproof
        if item.is_fireproof:
            components["minecraft:ignores_damage"] = True
        
        # Dano
        if item.attack_damage > 0:
            components["minecraft:damage"] = item.attack_damage
        
        # Armadura
        if item.armor_value > 0:
            components["minecraft:armor"] = {
                "protection": item.armor_value
            }
        
        # Comida
        if item.is_edible:
            components["minecraft:food"] = {
                "nutrition": item.food_value,
                "saturation_modifier": item.saturation,
                "can_always_eat": False
            }
        
        # Mineração
        if item.mining_speed > 1.0:
            components["minecraft:digger"] = {
                "use_efficiency": True,
                "destroy_speeds": [
                    {
                        "block": "minecraft:stone",
                        "speed": int(item.mining_speed)
                    }
                ]
            }
        
        # Tags
        tags = []
        if item.has_custom_behavior:
            tags.append(f"{mod_id}:custom")
        
        if tags:
            components["minecraft:tags"] = {"tags": tags}
        
        return bedrock_item
    
    @staticmethod
    def convert_recipe(recipe: JavaRecipe, mod_id: str) -> Optional[Dict[str, Any]]:
        """
        Converte JavaRecipe para formato Bedrock
        NUNCA retorna JSON vazio {}
        """
        
        # Extreme crafting não é suportado diretamente
        if recipe.is_extreme:
            print(f"   ⚠️  Receita {recipe.recipe_id} requer crafting 9x9 (não suportado)")
            return None
        
        # Shaped Recipe
        if recipe.pattern:
            return BedrockConverter._convert_shaped_recipe(recipe, mod_id)
        
        # Shapeless Recipe
        elif recipe.ingredients:
            return BedrockConverter._convert_shapeless_recipe(recipe, mod_id)
        
        # Formato customizado (primary/secondary)
        elif 'primary' in recipe.raw_data or 'secondary' in recipe.raw_data:
            return BedrockConverter._convert_custom_recipe(recipe, mod_id)
        
        # Se não conseguiu converter, retorna None (não JSON vazio)
        return None
    
    @staticmethod
    def _convert_shaped_recipe(recipe: JavaRecipe, mod_id: str) -> Dict[str, Any]:
        """Converte receita shaped"""
        
        bedrock_recipe = {
            "format_version": BedrockConverter.FORMAT_VERSION,
            "minecraft:recipe_shaped": {
                "description": {
                    "identifier": f"{mod_id}:{recipe.recipe_id}"
                },
                "tags": ["crafting_table"],
                "pattern": recipe.pattern,
                "key": {},
                "result": BedrockConverter._convert_result(recipe.result, mod_id)
            }
        }
        
        # Converte key
        for symbol, ingredient in recipe.key.items():
            bedrock_recipe["minecraft:recipe_shaped"]["key"][symbol] = \
                BedrockConverter._convert_ingredient(ingredient, mod_id)
        
        return bedrock_recipe
    
    @staticmethod
    def _convert_shapeless_recipe(recipe: JavaRecipe, mod_id: str) -> Dict[str, Any]:
        """Converte receita shapeless"""
        
        bedrock_recipe = {
            "format_version": BedrockConverter.FORMAT_VERSION,
            "minecraft:recipe_shapeless": {
                "description": {
                    "identifier": f"{mod_id}:{recipe.recipe_id}"
                },
                "tags": ["crafting_table"],
                "ingredients": [],
                "result": BedrockConverter._convert_result(recipe.result, mod_id)
            }
        }
        
        # Converte ingredients
        for ingredient in recipe.ingredients:
            converted = BedrockConverter._convert_ingredient(ingredient, mod_id)
            if converted:
                bedrock_recipe["minecraft:recipe_shapeless"]["ingredients"].append(converted)
        
        return bedrock_recipe
    
    @staticmethod
    def _convert_custom_recipe(recipe: JavaRecipe, mod_id: str) -> Dict[str, Any]:
        """Converte receita com formato customizado"""
        
        ingredients = []
        
        if 'primary' in recipe.raw_data:
            ingredients.append(BedrockConverter._convert_ingredient(
                recipe.raw_data['primary'], mod_id
            ))
        
        if 'secondary' in recipe.raw_data:
            ingredients.append(BedrockConverter._convert_ingredient(
                recipe.raw_data['secondary'], mod_id
            ))
        
        # Adiciona outros ingredientes possíveis
        for key in recipe.raw_data:
            if key not in ['type', 'primary', 'secondary', 'result']:
                ing = recipe.raw_data[key]
                if isinstance(ing, dict) and ('item' in ing or 'tag' in ing):
                    ingredients.append(BedrockConverter._convert_ingredient(ing, mod_id))
        
        bedrock_recipe = {
            "format_version": BedrockConverter.FORMAT_VERSION,
            "minecraft:recipe_shapeless": {
                "description": {
                    "identifier": f"{mod_id}:{recipe.recipe_id}"
                },
                "tags": ["crafting_table"],
                "ingredients": ingredients,
                "result": BedrockConverter._convert_result(recipe.result, mod_id)
            }
        }
        
        return bedrock_recipe
    
    @staticmethod
    def _convert_ingredient(ingredient: Any, mod_id: str) -> Dict[str, Any]:
        """Converte ingrediente individual"""
        
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
                # Bedrock não suporta tags diretamente em receitas
                # Tenta converter para item específico
                tag = ingredient['tag']
                return {"item": f"minecraft:{tag.split('/')[-1]}"}
        
        return {"item": "minecraft:air"}
    
    @staticmethod
    def _convert_result(result: Any, mod_id: str) -> Dict[str, Any]:
        """Converte resultado da receita"""
        
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
        """Normaliza ID do item"""
        
        # Remove namespace se for do próprio mod
        if item_id.startswith(f'{mod_id}:'):
            return item_id
        
        # Mantém minecraft:
        if item_id.startswith('minecraft:'):
            return item_id
        
        # Se não tem namespace, adiciona o do mod
        if ':' not in item_id:
            return f"{mod_id}:{item_id}"
        
        # Outros namespaces (forge, etc) → converte para o mod
        parts = item_id.split(':')
        if len(parts) == 2:
            return f"{mod_id}:{parts[1]}"
        
        return item_id

# ============================================================================
# GERADOR DE ADDON
# ============================================================================

class AddonGenerator:
    """Gera estrutura completa do addon Bedrock"""
    
    def __init__(self, mod_id: str, output_dir: Path):
        self.mod_id = mod_id
        self.output_dir = output_dir
        self.bp_dir = output_dir / "behavior_pack"
        self.rp_dir = output_dir / "resource_pack"
        
        # Estatísticas
        self.stats = {
            'items_created': 0,
            'recipes_created': 0,
            'textures_copied': 0,
            'errors': []
        }
    
    def generate(self, analyzer: JarAnalyzer):
        """Gera addon completo"""
        
        print("\n🔨 Gerando Addon Bedrock...")
        
        # Cria estrutura de pastas
        self._create_folders()
        
        # Behavior Pack
        self._generate_manifests()
        self._generate_items(analyzer.items)
        self._generate_recipes(analyzer.recipes)
        
        # Resource Pack
        self._copy_textures(analyzer.textures)
        self._generate_texture_mapping(analyzer.items, analyzer.textures)
        self._generate_language_files(analyzer.items)
        
        # Empacota
        self._create_mcaddon()
        
        print(f"\n✅ Addon gerado com sucesso!")
        print(f"   Items: {self.stats['items_created']}")
        print(f"   Receitas: {self.stats['recipes_created']}")
        print(f"   Texturas: {self.stats['textures_copied']}")
    
    def _create_folders(self):
        """Cria estrutura de pastas"""
        
        folders = [
            self.bp_dir / "items",
            self.bp_dir / "recipes",
            self.rp_dir / "textures" / "items",
            self.rp_dir / "texts"
        ]
        
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
    
    def _generate_manifests(self):
        """Gera manifest.json para BP e RP"""
        
        bp_uuid = str(uuid.uuid4())
        rp_uuid = str(uuid.uuid4())
        bp_module_uuid = str(uuid.uuid4())
        rp_module_uuid = str(uuid.uuid4())
        
        # Behavior Pack Manifest
        bp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} Behavior Pack",
                "description": f"Converted from Java Edition\n{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "uuid": bp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [
                {
                    "type": "data",
                    "uuid": bp_module_uuid,
                    "version": [1, 0, 0]
                }
            ],
            "dependencies": [
                {
                    "uuid": rp_uuid,
                    "version": [1, 0, 0]
                }
            ]
        }
        
        # Resource Pack Manifest
        rp_manifest = {
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} Resource Pack",
                "description": f"Textures and UI\n{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "uuid": rp_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [
                {
                    "type": "resources",
                    "uuid": rp_module_uuid,
                    "version": [1, 0, 0]
                }
            ]
        }
        
        # Salva
        self._save_json(bp_manifest, self.bp_dir / "manifest.json")
        self._save_json(rp_manifest, self.rp_dir / "manifest.json")
        
        print("   ✓ Manifests gerados")
    
    def _generate_items(self, items: Dict[str, JavaItem]):
        """Gera arquivos de items no Behavior Pack"""
        
        for identifier, item in items.items():
            try:
                bedrock_item = BedrockConverter.convert_item(item, self.mod_id)
                
                # GARANTE que o arquivo é criado
                item_path = self.bp_dir / "items" / f"{identifier}.json"
                self._save_json(bedrock_item, item_path)
                
                self.stats['items_created'] += 1
                
            except Exception as e:
                self.stats['errors'].append(f"Item {identifier}: {str(e)}")
        
        print(f"   ✓ {self.stats['items_created']} items gerados")
    
    def _generate_recipes(self, recipes: Dict[str, JavaRecipe]):
        """Gera arquivos de receitas"""
        
        for recipe_id, recipe in recipes.items():
            try:
                bedrock_recipe = BedrockConverter.convert_recipe(recipe, self.mod_id)
                
                # NUNCA salva JSON vazio
                if bedrock_recipe and bedrock_recipe != {}:
                    recipe_path = self.bp_dir / "recipes" / f"{recipe_id}.json"
                    self._save_json(bedrock_recipe, recipe_path)
                    self.stats['recipes_created'] += 1
                
            except Exception as e:
                self.stats['errors'].append(f"Recipe {recipe_id}: {str(e)}")
        
        print(f"   ✓ {self.stats['recipes_created']} receitas geradas")
    
    def _copy_textures(self, textures: Dict[str, bytes]):
        """Copia texturas para Resource Pack"""
        
        for texture_name, texture_data in textures.items():
            try:
                texture_path = self.rp_dir / "textures" / "items" / f"{texture_name}.png"
                texture_path.write_bytes(texture_data)
                self.stats['textures_copied'] += 1
                
            except Exception as e:
                self.stats['errors'].append(f"Texture {texture_name}: {str(e)}")
        
        print(f"   ✓ {self.stats['textures_copied']} texturas copiadas")
    
    def _generate_texture_mapping(self, items: Dict[str, JavaItem], 
                                  textures: Dict[str, bytes]):
        """Gera item_texture.json com mapeamento correto"""
        
        texture_data = {}
        
        for identifier, item in items.items():
            texture_name = item.texture_name or identifier
            
            # Verifica se a textura existe
            if texture_name in textures:
                texture_data[f"{self.mod_id}:{identifier}"] = {
                    "textures": f"textures/items/{texture_name}"
                }
        
        item_texture_json = {
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.items",
            "texture_data": texture_data
        }
        
        self._save_json(
            item_texture_json,
            self.rp_dir / "textures" / "item_texture.json"
        )
        
        print("   ✓ Mapeamento de texturas gerado")
    
    def _generate_language_files(self, items: Dict[str, JavaItem]):
        """Gera arquivos de tradução"""
        
        # languages.json
        languages_json = {
            "languages": ["en_US", "pt_BR"]
        }
        
        self._save_json(
            languages_json,
            self.rp_dir / "texts" / "languages.json"
        )
        
        # en_US.lang
        lang_entries = []
        for identifier, item in items.items():
            display_name = identifier.replace('_', ' ').title()
            lang_entries.append(
                f"item.{self.mod_id}:{identifier}.name={display_name}"
            )
        
        (self.rp_dir / "texts" / "en_US.lang").write_text(
            "\n".join(lang_entries),
            encoding='utf-8'
        )
        
        print("   ✓ Arquivos de idioma gerados")
    
    def _create_mcaddon(self):
        """Cria arquivo .mcaddon"""
        
        mcaddon_path = self.output_dir / f"{self.mod_id}.mcaddon"
        
        with zipfile.ZipFile(mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as mcaddon:
            # Adiciona Behavior Pack
            for file in self.bp_dir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(self.output_dir)
                    mcaddon.write(file, arcname)
            
            # Adiciona Resource Pack
            for file in self.rp_dir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(self.output_dir)
                    mcaddon.write(file, arcname)
        
        print(f"   ✓ {self.mod_id}.mcaddon criado ({mcaddon_path.stat().st_size / 1024:.1f} KB)")
    
    def _save_json(self, data: Dict[str, Any], path: Path):
        """Salva JSON formatado"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    """
    Função principal de transpilação
    
    Args:
        jar_path: Caminho do arquivo .jar
        output_folder: Pasta de saída
    
    Returns:
        Dicionário com estatísticas e caminhos dos arquivos gerados
    """
    
    print("=" * 70)
    print("🚀 MINECRAFT JAVA → BEDROCK TRANSPILER")
    print("=" * 70)
    
    start_time = datetime.now()
    
    try:
        # Valida entrada
        jar_path = Path(jar_path)
        if not jar_path.exists():
            raise FileNotFoundError(f"JAR não encontrado: {jar_path}")
        
        if not jar_path.suffix == '.jar':
            raise ValueError("Arquivo deve ter extensão .jar")
        
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Fase 1: Análise
        analyzer = JarAnalyzer(jar_path)
        analyzer.analyze()
        
        # Fase 2: Geração
        generator = AddonGenerator(analyzer.mod_id, output_dir)
        generator.generate(analyzer)
        
        # Resultado
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = {
            'success': True,
            'mod_id': analyzer.mod_id,
            'output_file': str(output_dir / f"{analyzer.mod_id}.mcaddon"),
            'stats': {
                'items_created': generator.stats['items_created'],
                'recipes_created': generator.stats['recipes_created'],
                'textures_copied': generator.stats['textures_copied'],
                'errors': len(generator.stats['errors']) + len(analyzer.errors)
            },
            'elapsed_time': f"{elapsed:.2f}s",
            'errors': generator.stats['errors'] + analyzer.errors
        }
        
        print("\n" + "=" * 70)
        print("✨ TRANSPILAÇÃO CONCLUÍDA")
        print("=" * 70)
        print(f"⏱️  Tempo: {elapsed:.2f}s")
        print(f"📦 Arquivo: {result['output_file']}")
        print("=" * 70)
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {str(e)}")
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

# ============================================================================
# TESTE STANDALONE
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python transpiler_engine.py <caminho_do_mod.jar> [pasta_saida]")
        print("\nExemplo:")
        print("  python transpiler_engine.py mods/waystones-1.20.1.jar output/")
        sys.exit(1)
    
    jar_file = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    result = transpile_jar(jar_file, output)
    
    if not result['success']:
        sys.exit(1)
