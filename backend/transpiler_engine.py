#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT TRANSPILER ENGINE v4.2 FINAL PRODUCTION
==================================================
Motor profissional com armaduras funcionais

FEATURES v4.2:
✅ Armaduras com minecraft:wearable e render_offsets
✅ Texturas de armadura (layer_1/layer_2)
✅ Traduções corretas (en_US.lang)
✅ Blocos colocáveis (minecraft:block_placer)
✅ menu_category para todos os items/blocos
✅ blocks.json completo
"""

import json
import zipfile
import re
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import traceback

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class Item:
    id: str
    tex: str
    stack: int = 64
    dmg: int = 0
    tool: bool = False
    armor_slot: Optional[str] = None  # ✅ NOVO: helmet, chestplate, leggings, boots
    is_block_item: bool = False

@dataclass
class Block:
    id: str
    tex: str
    hard: float = 1.5
    resist: float = 6.0
    is_ore: bool = False

# ============================================================================
# ANALISADOR DE JAR
# ============================================================================

class Analyzer:
    def __init__(self, jar: str):
        self.jar = Path(jar)
        self.mod = self._get_mod()
        self.items: Dict[str, Item] = {}
        self.blocks: Dict[str, Block] = {}
        self.item_tex: Dict[str, bytes] = {}
        self.block_tex: Dict[str, bytes] = {}
        self.armor_tex: Dict[str, bytes] = {}  # ✅ NOVO: Texturas de armadura
    
    def _get_mod(self) -> str:
        n = self.jar.stem.lower()
        n = re.sub(r'[-_](forge|fabric|neo)', '', n)
        n = re.sub(r'[-_]mc?\d+\.\d+', '', n)
        n = re.sub(r'[-_]\d+\.\d+\.?\d*', '', n)
        return re.sub(r'[^a-z0-9]', '', n) or "mod"
    
    def run(self):
        print(f"📦 Mod: {self.mod}")
        
        # Coleta blocos primeiro
        block_names = set()
        
        with zipfile.ZipFile(self.jar) as z:
            for f in z.namelist():
                try:
                    # Blocos
                    if '/textures/block/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.block_tex[n] = z.read(f)
                        block_names.add(n)
                        
                        is_ore = 'ore' in n.lower()
                        hard = 3.0 if is_ore else 1.5
                        
                        self.blocks[n] = Block(
                            id=n, tex=n,
                            hard=hard, resist=hard*2,
                            is_ore=is_ore
                        )
                    
                    # ✅ NOVO: Texturas de armadura
                    elif '/textures/models/armor/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.armor_tex[n] = z.read(f)
                
                except: pass
        
        # Coleta items
        with zipfile.ZipFile(self.jar) as z:
            for f in z.namelist():
                try:
                    if '/textures/item/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.item_tex[n] = z.read(f)
                        
                        # ✅ Detecta tipo de armadura
                        armor_slot = None
                        if 'helmet' in n.lower():
                            armor_slot = 'helmet'
                        elif 'chestplate' in n.lower():
                            armor_slot = 'chestplate'
                        elif 'leggings' in n.lower():
                            armor_slot = 'leggings'
                        elif 'boots' in n.lower():
                            armor_slot = 'boots'
                        
                        is_tool = any(x in n for x in ['sword','axe','pick','shovel','hoe'])
                        is_armor = armor_slot is not None
                        is_block_item = n in block_names
                        
                        self.items[n] = Item(
                            id=n, tex=n,
                            tool=is_tool,
                            armor_slot=armor_slot,
                            is_block_item=is_block_item,
                            dmg=250 if (is_tool or is_armor) else 0,
                            stack=1 if (is_tool or is_armor) else 64
                        )
                
                except: pass
        
        print(f"✅ {len(self.items)} items ({sum(1 for i in self.items.values() if i.armor_slot)} armaduras)")
        print(f"✅ {len(self.blocks)} blocos")
        print(f"✅ {len(self.armor_tex)} texturas de armadura")

# ============================================================================
# GERADOR DE ADDON
# ============================================================================

class Generator:
    def __init__(self, mod: str, out: Path):
        self.mod = mod
        self.out = out
        self.bp = out / "behavior_pack"
        self.rp = out / "resource_pack"
        
        # UUIDs únicos
        self.bp_h = str(uuid.uuid4())
        self.bp_m = str(uuid.uuid4())
        self.rp_h = str(uuid.uuid4())
        self.rp_m = str(uuid.uuid4())
        
        assert len({self.bp_h, self.bp_m, self.rp_h, self.rp_m}) == 4
        
        self.cnt = {'items': 0, 'armors': 0, 'blocks': 0, 'tex': 0}
    
    def run(self, a: Analyzer):
        print("\n🔨 Gerando addon v4.2 FINAL...")
        
        # Estrutura completa
        for d in [
            self.bp/"items", self.bp/"blocks",
            self.rp/"items", 
            self.rp/"textures"/"items", 
            self.rp/"textures"/"blocks",
            self.rp/"textures"/"models"/"armor",  # ✅ NOVO
            self.rp/"texts"
        ]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Manifests
        self._gen_manifests()
        
        # Icon
        if a.item_tex:
            icon = next(iter(a.item_tex.values()))
            (self.bp / "pack_icon.png").write_bytes(icon)
            (self.rp / "pack_icon.png").write_bytes(icon)
        
        # ✅ Items BP com categorias e componentes especiais
        for n, i in a.items.items():
            self._gen_item_bp(n, i)
            self.cnt['items'] += 1
            if i.armor_slot:
                self.cnt['armors'] += 1
        
        # Items RP
        for n, i in a.items.items():
            self._gen_item_rp(n, i)
        
        # ✅ Blocos BP com menu_category
        for n, b in a.blocks.items():
            self._gen_block_bp(n, b)
            self.cnt['blocks'] += 1
        
        # ✅ Texturas
        self._copy_textures(a)
        
        # ✅ Atlas
        self._gen_item_texture_json(a.items)
        
        if a.blocks:
            self._gen_terrain_texture_json(a.blocks)
            self._gen_blocks_json(a.blocks)
        
        # ✅ Traduções
        self._gen_translations(a.items, a.blocks)
        
        # Pack
        self._create_mcaddon()
        
        # Resumo
        self._print_summary()
    
    def _gen_manifests(self):
        """Gera manifests"""
        self._save({
            "format_version": 2,
            "header": {
                "name": f"{self.mod.title()} BP",
                "description": f"Converted {datetime.now().strftime('%Y-%m-%d')}",
                "uuid": self.bp_h,
                "version": [1,0,0],
                "min_engine_version": [1,20,80]
            },
            "modules": [{"type": "data", "uuid": self.bp_m, "version": [1,0,0]}],
            "dependencies": [{"uuid": self.rp_h, "version": [1,0,0]}]
        }, self.bp / "manifest.json")
        
        self._save({
            "format_version": 2,
            "header": {
                "name": f"{self.mod.title()} RP",
                "description": "Textures and Models",
                "uuid": self.rp_h,
                "version": [1,0,0],
                "min_engine_version": [1,20,80]
            },
            "modules": [{"type": "resources", "uuid": self.rp_m, "version": [1,0,0]}]
        }, self.rp / "manifest.json")
    
    def _gen_item_bp(self, name: str, item: Item):
        """
        ✅ Gera item BP com componentes especiais
        - Armaduras: minecraft:wearable + render_offsets
        - Blocos: minecraft:block_placer
        - Todos: category correto
        """
        
        components = {
            "minecraft:icon": item.tex,
            "minecraft:max_stack_size": item.stack
        }
        
        # Durabilidade
        if item.dmg > 0:
            components["minecraft:durability"] = {"max_durability": item.dmg}
        
        # ✅ ARMADURA: Componentes especiais
        if item.armor_slot:
            # Slot mapping
            slot_map = {
                'helmet': 'slot.armor.head',
                'chestplate': 'slot.armor.chest',
                'leggings': 'slot.armor.legs',
                'boots': 'slot.armor.feet'
            }
            
            components["minecraft:wearable"] = {
                "slot": slot_map[item.armor_slot]
            }
            
            components["minecraft:render_offsets"] = "armor"
            
            # Proteção básica
            components["minecraft:armor"] = {
                "protection": 2
            }
        
        # ✅ BLOCO: Block placer
        if item.is_block_item:
            components["minecraft:block_placer"] = {
                "block": f"{self.mod}:{item.id}"
            }
        
        # ✅ Category no description
        category = "equipment" if (item.tool or item.armor_slot) else "items"
        
        self._save({
            "format_version": "1.20.80",
            "minecraft:item": {
                "description": {
                    "identifier": f"{self.mod}:{item.id}",
                    "category": category  # ✅ OBRIGATÓRIO
                },
                "components": components
            }
        }, self.bp / "items" / f"{name}.json")
    
    def _gen_item_rp(self, name: str, item: Item):
        """Gera item RP"""
        self._save({
            "format_version": "1.20.80",
            "minecraft:item": {
                "description": {"identifier": f"{self.mod}:{item.id}"},
                "components": {"minecraft:icon": item.tex}
            }
        }, self.rp / "items" / f"{name}.json")
    
    def _gen_block_bp(self, name: str, block: Block):
        """
        ✅ Gera bloco BP com menu_category
        """
        
        # ✅ menu_category com group
        menu_cat = {
            "category": "construction",
            "group": "itemGroup.name.ore" if block.is_ore else "itemGroup.name.stone"
        }
        
        self._save({
            "format_version": "1.20.80",
            "minecraft:block": {
                "description": {
                    "identifier": f"{self.mod}:{block.id}",
                    "menu_category": menu_cat  # ✅ OBRIGATÓRIO
                },
                "components": {
                    "minecraft:destructible_by_mining": {
                        "seconds_to_destroy": block.hard / 1.5
                    },
                    "minecraft:destructible_by_explosion": {
                        "explosion_resistance": block.resist
                    },
                    "minecraft:geometry": "minecraft:geometry.full_block",
                    "minecraft:material_instances": {
                        "*": {
                            "texture": block.tex,
                            "render_method": "opaque"
                        }
                    }
                }
            }
        }, self.bp / "blocks" / f"{name}.json")
    
    def _copy_textures(self, a: Analyzer):
        """Copia todas as texturas"""
        
        # Items
        for n, d in a.item_tex.items():
            (self.rp / "textures" / "items" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
        
        # Blocos
        for n, d in a.block_tex.items():
            (self.rp / "textures" / "blocks" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
        
        # ✅ NOVO: Armaduras (layer_1/layer_2)
        for n, d in a.armor_tex.items():
            (self.rp / "textures" / "models" / "armor" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
    
    def _gen_item_texture_json(self, items: Dict[str, Item]):
        """Gera atlas de items"""
        self._save({
            "resource_pack_name": self.mod,
            "texture_name": "atlas.items",
            "texture_data": {
                i.tex: {"textures": f"textures/items/{i.tex}"}
                for i in items.values()
            }
        }, self.rp / "textures" / "item_texture.json")
    
    def _gen_terrain_texture_json(self, blocks: Dict[str, Block]):
        """Gera atlas de blocos"""
        self._save({
            "resource_pack_name": self.mod,
            "texture_name": "atlas.terrain",
            "texture_data": {
                b.tex: {"textures": f"textures/blocks/{b.tex}"}
                for b in blocks.values()
            }
        }, self.rp / "textures" / "terrain_texture.json")
    
    def _gen_blocks_json(self, blocks: Dict[str, Block]):
        """✅ Gera blocks.json NA RAIZ do RP"""
        self._save({
            f"{self.mod}:{n}": {
                "textures": b.tex,
                "sound": "stone"
            }
            for n, b in blocks.items()
        }, self.rp / "blocks.json")
        
        print(f"   ✓ blocks.json ({len(blocks)} blocos)")
    
    def _gen_translations(self, items: Dict[str, Item], blocks: Dict[str, Block]):
        """
        ✅ Gera traduções corretas
        
        Formato:
        - item.custom:nome.name=Nome Formatado
        - tile.custom:nome.name=Nome Formatado
        """
        
        # languages.json
        self._save(
            {"languages": ["en_US", "pt_BR"]},
            self.rp / "texts" / "languages.json"
        )
        
        entries = []
        
        # ✅ Items
        for name in items.keys():
            pretty = name.replace('_', ' ').title()
            entries.append(f"item.{self.mod}:{name}.name={pretty}")
        
        # ✅ Blocos
        for name in blocks.keys():
            pretty = name.replace('_', ' ').title()
            entries.append(f"tile.{self.mod}:{name}.name={pretty}")
        
        lang = "\n".join(entries)
        (self.rp / "texts" / "en_US.lang").write_text(lang, encoding='utf-8')
        (self.rp / "texts" / "pt_BR.lang").write_text(lang, encoding='utf-8')
        
        print(f"   ✓ Traduções ({len(entries)} entradas)")
    
    def _create_mcaddon(self):
        """Empacota"""
        pack = self.out / f"{self.mod}.mcaddon"
        with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in self.bp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.out))
            for f in self.rp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.out))
        
        print(f"\n✅ {pack.name} ({pack.stat().st_size/1024:.1f}KB)")
    
    def _print_summary(self):
        """Resumo final"""
        print(f"   Items: {self.cnt['items']} ({self.cnt['armors']} armaduras)")
        print(f"   Blocos: {self.cnt['blocks']}")
        print(f"   Texturas: {self.cnt['tex']}")
        print("\n🎮 COMPLETO! Armaduras, blocos e traduções OK!")
    
    def _save(self, data: Dict, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    try:
        print("=" * 60)
        print("🚀 TRANSPILER v4.2 FINAL PRODUCTION")
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

# ============================================================================
# COMPATIBILIDADE
# ============================================================================

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
