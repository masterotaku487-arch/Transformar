#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT TRANSPILER ENGINE v4.3 FINAL
=======================================
Motor profissional DEFINITIVO

FOCO v4.3:
✅ Attachables para armaduras VISÍVEIS no corpo
✅ Block Placer DINÂMICO para todos os blocos
✅ Identificadores ÚNICOS e consistentes
✅ Geometria geometry.player.armor.XXX
"""

import json
import zipfile
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import traceback

@dataclass
class Item:
    id: str
    tex: str
    stack: int = 64
    dmg: int = 0
    armor_slot: Optional[str] = None

@dataclass
class Block:
    id: str
    tex: str
    hard: float = 1.5

class Analyzer:
    def __init__(self, jar: str):
        self.jar = Path(jar)
        self.mod = self._get_mod()
        self.items: Dict[str, Item] = {}
        self.blocks: Dict[str, Block] = {}
        self.item_tex: Dict[str, bytes] = {}
        self.block_tex: Dict[str, bytes] = {}
        self.armor_tex: Dict[str, bytes] = {}
        self.block_items: Set[str] = set()  # ✅ NOVO: Items que são blocos
    
    def _get_mod(self) -> str:
        n = self.jar.stem.lower()
        n = re.sub(r'[-_](forge|fabric|neo)', '', n)
        n = re.sub(r'[-_]mc?\d+\.\d+', '', n)
        n = re.sub(r'[-_]\d+\.\d+\.?\d*', '', n)
        return re.sub(r'[^a-z0-9]', '', n) or "mod"
    
    def run(self):
        print(f"📦 Mod: {self.mod}")
        
        # ✅ FASE 1: Coleta BLOCOS
        with zipfile.ZipFile(self.jar) as z:
            for f in z.namelist():
                try:
                    if '/textures/block/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.block_tex[n] = z.read(f)
                        self.blocks[n] = Block(
                            id=n, tex=n,
                            hard=3.0 if 'ore' in n else 1.5
                        )
                    elif '/textures/models/armor/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.armor_tex[n] = z.read(f)
                except: pass
        
        # ✅ FASE 2: Coleta ITEMS
        with zipfile.ZipFile(self.jar) as z:
            for f in z.namelist():
                try:
                    if '/textures/item/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.item_tex[n] = z.read(f)
                        
                        # Detecta armadura
                        armor_slot = None
                        if 'helmet' in n.lower():
                            armor_slot = 'helmet'
                        elif 'chestplate' in n.lower():
                            armor_slot = 'chestplate'
                        elif 'leggings' in n.lower():
                            armor_slot = 'leggings'
                        elif 'boots' in n.lower():
                            armor_slot = 'boots'
                        
                        # ✅ Detecta se é item de bloco
                        is_block = n in self.blocks
                        if is_block:
                            self.block_items.add(n)
                        
                        dmg = 250 if armor_slot or any(x in n for x in ['sword','axe','pick','shovel','hoe']) else 0
                        stack = 1 if dmg > 0 else 64
                        
                        self.items[n] = Item(
                            id=n, tex=n,
                            armor_slot=armor_slot,
                            dmg=dmg, stack=stack
                        )
                except: pass
        
        # ✅ FASE 3: Cria items para blocos SEM item
        for block_name in self.blocks.keys():
            if block_name not in self.items:
                # Cria item automaticamente
                self.items[block_name] = Item(
                    id=block_name,
                    tex=block_name,
                    stack=64, dmg=0
                )
                self.block_items.add(block_name)
                print(f"   ✓ Item criado para bloco: {block_name}")
        
        armors = sum(1 for i in self.items.values() if i.armor_slot)
        print(f"✅ {len(self.items)} items ({armors} armaduras)")
        print(f"✅ {len(self.blocks)} blocos ({len(self.block_items)} com items)")

class Generator:
    def __init__(self, mod: str, out: Path):
        self.mod = mod
        self.out = out
        self.bp = out / "behavior_pack"
        self.rp = out / "resource_pack"
        
        self.bp_h = str(uuid.uuid4())
        self.bp_m = str(uuid.uuid4())
        self.rp_h = str(uuid.uuid4())
        self.rp_m = str(uuid.uuid4())
        
        self.cnt = {'items': 0, 'blocks': 0, 'attachables': 0, 'tex': 0}
    
    def run(self, a: Analyzer):
        print("\n🔨 V4.3 FINAL - Armaduras visíveis + Blocos colocáveis...")
        
        # Estrutura
        for d in [
            self.bp/"items", self.bp/"blocks",
            self.rp/"items", self.rp/"attachables",
            self.rp/"textures"/"items", self.rp/"textures"/"blocks",
            self.rp/"textures"/"models"/"armor", self.rp/"texts"
        ]:
            d.mkdir(parents=True, exist_ok=True)
        
        self._gen_manifests()
        
        if a.item_tex:
            icon = next(iter(a.item_tex.values()))
            (self.bp / "pack_icon.png").write_bytes(icon)
            (self.rp / "pack_icon.png").write_bytes(icon)
        
        # ✅ Items BP (com block_placer dinâmico)
        for n, i in a.items.items():
            is_block_item = n in a.block_items
            self._gen_item_bp(n, i, is_block_item)
            self.cnt['items'] += 1
        
        # Items RP
        for n, i in a.items.items():
            self._gen_item_rp(n, i)
        
        # ✅ NOVO: Attachables para armaduras
        for n, i in a.items.items():
            if i.armor_slot:
                self._gen_attachable(n, i)
                self.cnt['attachables'] += 1
        
        # Blocos BP
        for n, b in a.blocks.items():
            self._gen_block_bp(n, b)
            self.cnt['blocks'] += 1
        
        # Texturas
        self._copy_tex(a)
        
        # Atlas
        self._gen_item_texture_json(a.items)
        if a.blocks:
            self._gen_terrain_texture_json(a.blocks)
            self._gen_blocks_json(a.blocks)
        
        # Traduções
        self._gen_lang(a.items, a.blocks)
        
        # Pack
        self._pack()
        self._summary()
    
    def _gen_manifests(self):
        self._save({
            "format_version": 2,
            "header": {
                "name": f"{self.mod.title()} BP",
                "description": f"Converted {datetime.now().strftime('%Y-%m-%d')}",
                "uuid": self.bp_h, "version": [1,0,0],
                "min_engine_version": [1,20,80]
            },
            "modules": [{"type": "data", "uuid": self.bp_m, "version": [1,0,0]}],
            "dependencies": [{"uuid": self.rp_h, "version": [1,0,0]}]
        }, self.bp / "manifest.json")
        
        self._save({
            "format_version": 2,
            "header": {
                "name": f"{self.mod.title()} RP",
                "description": "Textures",
                "uuid": self.rp_h, "version": [1,0,0],
                "min_engine_version": [1,20,80]
            },
            "modules": [{"type": "resources", "uuid": self.rp_m, "version": [1,0,0]}]
        }, self.rp / "manifest.json")
    
    def _gen_item_bp(self, name: str, item: Item, is_block_item: bool):
        """
        ✅ Item BP com:
        - Block placer DINÂMICO
        - Wearable para armaduras
        - IDs CONSISTENTES
        """
        
        # ✅ ID ÚNICO E CONSISTENTE
        full_id = f"{self.mod}:{item.id}"
        
        comp = {
            "minecraft:icon": item.tex,
            "minecraft:max_stack_size": item.stack
        }
        
        if item.dmg > 0:
            comp["minecraft:durability"] = {"max_durability": item.dmg}
        
        # ✅ ARMADURA
        if item.armor_slot:
            slots = {
                'helmet': 'slot.armor.head',
                'chestplate': 'slot.armor.chest',
                'leggings': 'slot.armor.legs',
                'boots': 'slot.armor.feet'
            }
            comp["minecraft:wearable"] = {"slot": slots[item.armor_slot]}
            comp["minecraft:render_offsets"] = "armor"
            comp["minecraft:armor"] = {"protection": 2}
        
        # ✅ CRÍTICO: Block placer DINÂMICO
        if is_block_item:
            comp["minecraft:block_placer"] = {"block": full_id}
        
        cat = "equipment" if item.armor_slot else "items"
        
        self._save({
            "format_version": "1.20.80",
            "minecraft:item": {
                "description": {"identifier": full_id, "category": cat},
                "components": comp
            }
        }, self.bp / "items" / f"{name}.json")
    
    def _gen_item_rp(self, name: str, item: Item):
        self._save({
            "format_version": "1.20.80",
            "minecraft:item": {
                "description": {"identifier": f"{self.mod}:{item.id}"},
                "components": {"minecraft:icon": item.tex}
            }
        }, self.rp / "items" / f"{name}.json")
    
    def _gen_attachable(self, name: str, item: Item):
        """
        ✅ URGENTE: Attachable para armadura visível
        
        Estrutura padrão Bedrock:
        - identifier: custom:nome
        - geometry: geometry.player.armor.XXX
        - textures: textures/models/armor/material_layer_N
        """
        
        # Material (remove sufixo da armadura)
        material = item.id.replace('_helmet','').replace('_chestplate','')\
                         .replace('_leggings','').replace('_boots','')
        
        # Geometria padrão Bedrock
        geo = f"geometry.player.armor.{item.armor_slot}"
        
        # Layer da textura (leggings usa layer_2, resto usa layer_1)
        layer = "layer_2" if item.armor_slot == 'leggings' else "layer_1"
        tex_path = f"textures/models/armor/{material}_{layer}"
        
        self._save({
            "format_version": "1.10.0",
            "minecraft:attachable": {
                "description": {
                    "identifier": f"{self.mod}:{item.id}",  # ✅ ID CONSISTENTE
                    "materials": {
                        "default": "armor",
                        "enchanted": "armor_enchanted"
                    },
                    "textures": {
                        "default": tex_path
                    },
                    "geometry": {
                        "default": geo
                    },
                    "render_controllers": ["controller.render.armor"]
                }
            }
        }, self.rp / "attachables" / f"{name}.json")
    
    def _gen_block_bp(self, name: str, block: Block):
        cat = {"category": "construction", "group": "itemGroup.name.ore" if 'ore' in name else "itemGroup.name.stone"}
        
        self._save({
            "format_version": "1.20.80",
            "minecraft:block": {
                "description": {
                    "identifier": f"{self.mod}:{block.id}",
                    "menu_category": cat
                },
                "components": {
                    "minecraft:destructible_by_mining": {"seconds_to_destroy": block.hard/1.5},
                    "minecraft:geometry": "minecraft:geometry.full_block",
                    "minecraft:material_instances": {
                        "*": {"texture": block.tex, "render_method": "opaque"}
                    }
                }
            }
        }, self.bp / "blocks" / f"{name}.json")
    
    def _copy_tex(self, a: Analyzer):
        for n, d in a.item_tex.items():
            (self.rp / "textures" / "items" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
        for n, d in a.block_tex.items():
            (self.rp / "textures" / "blocks" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
        for n, d in a.armor_tex.items():
            (self.rp / "textures" / "models" / "armor" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
    
    def _gen_item_texture_json(self, items: Dict[str, Item]):
        self._save({
            "resource_pack_name": self.mod,
            "texture_name": "atlas.items",
            "texture_data": {
                i.tex: {"textures": f"textures/items/{i.tex}"}
                for i in items.values()
            }
        }, self.rp / "textures" / "item_texture.json")
    
    def _gen_terrain_texture_json(self, blocks: Dict[str, Block]):
        self._save({
            "resource_pack_name": self.mod,
            "texture_name": "atlas.terrain",
            "texture_data": {
                b.tex: {"textures": f"textures/blocks/{b.tex}"}
                for b in blocks.values()
            }
        }, self.rp / "textures" / "terrain_texture.json")
    
    def _gen_blocks_json(self, blocks: Dict[str, Block]):
        self._save({
            f"{self.mod}:{n}": {"textures": b.tex, "sound": "stone"}
            for n, b in blocks.items()
        }, self.rp / "blocks.json")
    
    def _gen_lang(self, items: Dict[str, Item], blocks: Dict[str, Block]):
        self._save({"languages": ["en_US", "pt_BR"]}, self.rp / "texts" / "languages.json")
        
        lines = []
        for n in items.keys():
            lines.append(f"item.{self.mod}:{n}.name={n.replace('_',' ').title()}")
        for n in blocks.keys():
            lines.append(f"tile.{self.mod}:{n}.name={n.replace('_',' ').title()}")
        
        lang = "\n".join(lines)
        (self.rp / "texts" / "en_US.lang").write_text(lang, encoding='utf-8')
        (self.rp / "texts" / "pt_BR.lang").write_text(lang, encoding='utf-8')
    
    def _pack(self):
        p = self.out / f"{self.mod}.mcaddon"
        with zipfile.ZipFile(p, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in self.bp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.out))
            for f in self.rp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.out))
        print(f"\n✅ {p.name} ({p.stat().st_size/1024:.1f}KB)")
    
    def _summary(self):
        print(f"   Items: {self.cnt['items']}")
        print(f"   Attachables: {self.cnt['attachables']} ✅")
        print(f"   Blocos: {self.cnt['blocks']}")
        print(f"   Texturas: {self.cnt['tex']}")
        print("\n🎮 ARMADURAS VISÍVEIS + BLOCOS COLOCÁVEIS!")
    
    def _save(self, data: Dict, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    try:
        print("=" * 60)
        print("🚀 TRANSPILER v4.3 FINAL")
        print("=" * 60)
        
        a = Analyzer(jar_path)
        a.run()
        
        out = Path(output_folder)
        out.mkdir(parents=True, exist_ok=True)
        
        g = Generator(a.mod, out)
        g.run(a)
        
        return {
            'success': True,
            'mod_id': a.mod,
            'output_file': str(out / f"{a.mod}.mcaddon"),
            'stats': {
                'items_processed': g.cnt['items'],
                'blocks_processed': g.cnt['blocks'],
                'recipes_converted': 0,
                'assets_extracted': g.cnt['tex']
            }
        }
    except Exception as e:
        print(f"❌ {e}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

class AvaritiaTranspiler:
    def __init__(self, jar_path: str, output_dir: str, mod_name: str = ""):
        self.jar_path = jar_path
        self.output_dir = output_dir
        self.stats = {}
    
    def run(self):
        r = transpile_jar(self.jar_path, self.output_dir)
        if r['success']:
            self.stats = r['stats']
        else:
            raise Exception(r.get('error'))
    
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
    r = transpile_jar(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "output")
    sys.exit(0 if r['success'] else 1)
