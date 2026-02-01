#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT TRANSPILER ENGINE v3.3 - FINAL
=========================================
Motor profissional com items visíveis no inventário

CORREÇÕES v3.3:
✅ Items registrados no Resource Pack (resource_pack/items/)
✅ Sincronização perfeita de IDs (BP ↔ RP)
✅ item_texture.json sem duplicatas
✅ 4 UUIDs únicos garantidos
"""

import json
import zipfile
import re
import uuid as uuid_module
import os
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import traceback

@dataclass
class JavaItem:
    identifier: str
    texture_name: str = ""
    max_stack_size: int = 64
    max_damage: int = 0
    attack_damage: float = 0.0
    is_tool: bool = False
    is_armor: bool = False

@dataclass
class JavaBlock:
    identifier: str
    texture_name: str = ""
    hardness: float = 1.5
    resistance: float = 6.0

class JarAnalyzer:
    def __init__(self, jar_path: str):
        self.jar_path = Path(jar_path)
        self.mod_id = self._extract_mod_id()
        self.items: Dict[str, JavaItem] = {}
        self.blocks: Dict[str, JavaBlock] = {}
        self.item_textures: Dict[str, bytes] = {}
        self.block_textures: Dict[str, bytes] = {}
        self.recipes: List[Dict] = []
    
    def _extract_mod_id(self) -> str:
        name = self.jar_path.stem.lower()
        name = re.sub(r'[-_](forge|fabric|neoforge)', '', name)
        name = re.sub(r'[-_]mc\d+\.\d+', '', name)
        name = re.sub(r'[-_]\d+[._]\d+[._]?\d*', '', name)
        name = re.sub(r'[^a-z0-9]', '', name)
        return name or "converted_mod"
    
    def analyze(self):
        with zipfile.ZipFile(self.jar_path, 'r') as jar:
            for filename in jar.namelist():
                try:
                    if '/textures/item/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        self.item_textures[name] = jar.read(filename)
                    elif '/textures/block/' in filename and filename.endswith('.png'):
                        name = Path(filename).stem
                        self.block_textures[name] = jar.read(filename)
                    elif '/recipes/' in filename and filename.endswith('.json'):
                        try:
                            self.recipes.append({
                                'id': Path(filename).stem,
                                'data': json.loads(jar.read(filename))
                            })
                        except:
                            pass
                except:
                    pass
        
        for name in self.item_textures.keys():
            item = JavaItem(identifier=name, texture_name=name)
            if any(x in name.lower() for x in ['sword', 'axe', 'pickaxe', 'shovel', 'hoe']):
                item.is_tool = True
                item.max_damage = 250
                item.max_stack_size = 1
            elif any(x in name.lower() for x in ['helmet', 'chestplate', 'leggings', 'boots']):
                item.is_armor = True
                item.max_damage = 250
                item.max_stack_size = 1
            self.items[name] = item
        
        for name in self.block_textures.keys():
            self.blocks[name] = JavaBlock(identifier=name, texture_name=name)

class BedrockConverter:
    FORMAT = "1.20.80"
    
    @staticmethod
    def convert_item_behavior(item: JavaItem, mod_id: str) -> Dict:
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
                    "minecraft:icon": {"texture": item.texture_name},
                    "minecraft:max_stack_size": item.max_stack_size,
                    **({"minecraft:durability": {"max_durability": min(item.max_damage, 32767)}} if item.max_damage > 0 else {}),
                    **({"minecraft:damage": item.attack_damage} if item.attack_damage > 0 else {})
                }
            }
        }
    
    @staticmethod
    def convert_item_resource(item: JavaItem, mod_id: str) -> Dict:
        return {
            "format_version": BedrockConverter.FORMAT,
            "minecraft:item": {
                "description": {"identifier": f"{mod_id}:{item.identifier}"},
                "components": {"minecraft:icon": item.texture_name}
            }
        }
    
    @staticmethod
    def convert_block(block: JavaBlock, mod_id: str) -> Dict:
        return {
            "format_version": BedrockConverter.FORMAT,
            "minecraft:block": {
                "description": {"identifier": f"{mod_id}:{block.identifier}"},
                "components": {
                    "minecraft:destructible_by_mining": {"seconds_to_destroy": block.hardness / 1.5},
                    "minecraft:geometry": "geometry.cube",
                    "minecraft:material_instances": {
                        "*": {"texture": block.texture_name, "render_method": "opaque"}
                    }
                }
            }
        }

class AddonGenerator:
    def __init__(self, mod_id: str, output_dir: Path):
        self.mod_id = mod_id
        self.output_dir = output_dir
        self.bp = output_dir / "behavior_pack"
        self.rp = output_dir / "resource_pack"
        self.bp_header_uuid = str(uuid_module.uuid4())
        self.bp_module_uuid = str(uuid_module.uuid4())
        self.rp_header_uuid = str(uuid_module.uuid4())
        self.rp_module_uuid = str(uuid_module.uuid4())
        self.stats = {'bp_items': 0, 'rp_items': 0, 'blocks': 0, 'recipes': 0, 'textures': 0}
    
    def generate(self, analyzer: JarAnalyzer):
        self._create_structure()
        self._generate_manifests()
        if analyzer.item_textures:
            icon = next(iter(analyzer.item_textures.values()))
            (self.bp / "pack_icon.png").write_bytes(icon)
            (self.rp / "pack_icon.png").write_bytes(icon)
        
        for name, item in analyzer.items.items():
            self._save_json(BedrockConverter.convert_item_behavior(item, self.mod_id), 
                          self.bp / "items" / f"{name}.json")
            self._save_json(BedrockConverter.convert_item_resource(item, self.mod_id),
                          self.rp / "items" / f"{name}.json")
            self.stats['bp_items'] += 1
            self.stats['rp_items'] += 1
        
        for name, block in analyzer.blocks.items():
            self._save_json(BedrockConverter.convert_block(block, self.mod_id),
                          self.bp / "blocks" / f"{name}.json")
            self.stats['blocks'] += 1
        
        for name, data in analyzer.item_textures.items():
            (self.rp / "textures" / "items" / f"{name}.png").write_bytes(data)
            self.stats['textures'] += 1
        
        for name, data in analyzer.block_textures.items():
            (self.rp / "textures" / "blocks" / f"{name}.png").write_bytes(data)
            self.stats['textures'] += 1
        
        self._save_json({
            "resource_pack_name": self.mod_id,
            "texture_name": "atlas.items",
            "texture_data": {
                item.texture_name: {"textures": f"textures/items/{item.texture_name}"}
                for item in analyzer.items.values()
            }
        }, self.rp / "textures" / "item_texture.json")
        
        if analyzer.blocks:
            self._save_json({
                "resource_pack_name": self.mod_id,
                "texture_name": "atlas.terrain",
                "texture_data": {
                    block.texture_name: {"textures": f"textures/blocks/{block.texture_name}"}
                    for block in analyzer.blocks.values()
                }
            }, self.rp / "textures" / "terrain_texture.json")
            
            self._save_json({
                f"{self.mod_id}:{name}": {"textures": block.texture_name, "sound": "stone"}
                for name, block in analyzer.blocks.items()
            }, self.rp / "blocks.json")
        
        self._save_json({"languages": ["en_US"]}, self.rp / "texts" / "languages.json")
        
        entries = [f"item.{self.mod_id}:{name}.name={name.replace('_', ' ').title()}" 
                  for name in analyzer.items.keys()]
        entries += [f"tile.{self.mod_id}:{name}.name={name.replace('_', ' ').title()}"
                   for name in analyzer.blocks.keys()]
        (self.rp / "texts" / "en_US.lang").write_text("\n".join(entries), encoding='utf-8')
        
        mcaddon = self.output_dir / f"{self.mod_id}.mcaddon"
        with zipfile.ZipFile(mcaddon, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in self.bp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.output_dir))
            for f in self.rp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.output_dir))
    
    def _create_structure(self):
        for d in [self.bp/"items", self.bp/"blocks", self.bp/"recipes",
                  self.rp/"items", self.rp/"textures"/"items", 
                  self.rp/"textures"/"blocks", self.rp/"texts"]:
            d.mkdir(parents=True, exist_ok=True)
    
    def _generate_manifests(self):
        self._save_json({
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} BP",
                "description": "Converted from Java",
                "uuid": self.bp_header_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{"type": "data", "uuid": self.bp_module_uuid, "version": [1, 0, 0]}],
            "dependencies": [{"uuid": self.rp_header_uuid, "version": [1, 0, 0]}]
        }, self.bp / "manifest.json")
        
        self._save_json({
            "format_version": 2,
            "header": {
                "name": f"{self.mod_id.title()} RP",
                "description": "Textures",
                "uuid": self.rp_header_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 80]
            },
            "modules": [{"type": "resources", "uuid": self.rp_module_uuid, "version": [1, 0, 0]}]
        }, self.rp / "manifest.json")
    
    def _save_json(self, data: Dict, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    try:
        jar_path = Path(jar_path)
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        analyzer = JarAnalyzer(jar_path)
        analyzer.analyze()
        
        generator = AddonGenerator(analyzer.mod_id, output_dir)
        generator.generate(analyzer)
        
        return {
            'success': True,
            'mod_id': analyzer.mod_id,
            'output_file': str(output_dir / f"{analyzer.mod_id}.mcaddon"),
            'stats': {
                'items_processed': generator.stats['bp_items'],
                'blocks_processed': generator.stats['blocks'],
                'recipes_converted': generator.stats['recipes'],
                'assets_extracted': generator.stats['textures']
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()}

class AvaritiaTranspiler:
    def __init__(self, jar_path: str, output_dir: str, mod_name: str = ""):
        self.jar_path = jar_path
        self.output_dir = output_dir
        self.stats = {}
    
    def run(self):
        result = transpile_jar(self.jar_path, self.output_dir)
        if result['success']:
            self.stats = result['stats']
        else:
            raise Exception(result.get('error'))
    
    def parse_jar(self): pass
    def convert_all(self): pass
    def generate_scripts(self): pass
    def build_addon_structure(self): pass
    def package_mcaddon(self): pass
    def print_report(self): pass

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python transpiler_engine.py <mod.jar> [output]")
        sys.exit(1)
    result = transpile_jar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "output")
    if not result['success']:
        print(f"Erro: {result.get('error')}")
        sys.exit(1)
