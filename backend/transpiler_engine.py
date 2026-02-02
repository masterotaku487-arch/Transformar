#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MINECRAFT TRANSPILER ENGINE v4.1 FINAL
=======================================
Motor profissional com texturas 100% funcionais

AJUSTES v4.1:
✅ UUID dependencies = UUID header RP (verificado)
✅ item_texture.json com estrutura exata
✅ category no description dos items
✅ Sem .png em NENHUM caminho
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
    id: str
    tex: str
    stack: int = 64
    dmg: int = 0
    tool: bool = False

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
    
    def _get_mod(self) -> str:
        n = self.jar.stem.lower()
        n = re.sub(r'[-_](forge|fabric|neo)', '', n)
        n = re.sub(r'[-_]mc?\d+\.\d+', '', n)
        n = re.sub(r'[-_]\d+\.\d+\.?\d*', '', n)
        return re.sub(r'[^a-z0-9]', '', n) or "mod"
    
    def run(self):
        print(f"📦 Mod: {self.mod}")
        with zipfile.ZipFile(self.jar) as z:
            for f in z.namelist():
                try:
                    if '/textures/item/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.item_tex[n] = z.read(f)
                        is_tool = any(x in n for x in ['sword','axe','pick','shovel','hoe'])
                        is_armor = any(x in n for x in ['helmet','chest','legging','boot'])
                        self.items[n] = Item(
                            id=n, tex=n,
                            tool=is_tool or is_armor,
                            dmg=250 if (is_tool or is_armor) else 0,
                            stack=1 if (is_tool or is_armor) else 64
                        )
                    elif '/textures/block/' in f and f.endswith('.png'):
                        n = Path(f).stem
                        self.block_tex[n] = z.read(f)
                        self.blocks[n] = Block(id=n, tex=n)
                except: pass
        print(f"✅ {len(self.items)} items, {len(self.blocks)} blocos")

class Generator:
    def __init__(self, mod: str, out: Path):
        self.mod = mod
        self.out = out
        self.bp = out / "behavior_pack"
        self.rp = out / "resource_pack"
        
        # 4 UUIDs únicos
        self.bp_h = str(uuid.uuid4())
        self.bp_m = str(uuid.uuid4())
        self.rp_h = str(uuid.uuid4())
        self.rp_m = str(uuid.uuid4())
        
        # ✅ VERIFICAÇÃO: Garante que são diferentes
        assert len({self.bp_h, self.bp_m, self.rp_h, self.rp_m}) == 4, "UUIDs duplicados!"
        
        self.cnt = {'bp': 0, 'rp': 0, 'blk': 0, 'tex': 0}
    
    def run(self, a: Analyzer):
        print("\n🔨 Gerando addon v4.1...")
        
        # Estrutura
        for d in [self.bp/"items", self.bp/"blocks",
                  self.rp/"items",
                  self.rp/"textures"/"items",
                  self.rp/"textures"/"blocks",
                  self.rp/"texts"]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Manifests
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
            # ✅ AJUSTE 1: UUID dependencies = UUID header RP
            "dependencies": [{"uuid": self.rp_h, "version": [1,0,0]}]
        }, self.bp / "manifest.json")
        
        self._save({
            "format_version": 2,
            "header": {
                "name": f"{self.mod.title()} RP",
                "description": "Textures",
                "uuid": self.rp_h,  # ✅ Mesmo UUID usado em dependencies
                "version": [1,0,0],
                "min_engine_version": [1,20,80]
            },
            "modules": [{"type": "resources", "uuid": self.rp_m, "version": [1,0,0]}]
        }, self.rp / "manifest.json")
        
        print(f"   ✓ UUIDs: BP header={self.bp_h[:8]}... RP header={self.rp_h[:8]}...")
        print(f"   ✓ Dependencies: BP → RP header ({self.rp_h[:8]}...)")
        
        # Icon
        if a.item_tex:
            icon = next(iter(a.item_tex.values()))
            (self.bp / "pack_icon.png").write_bytes(icon)
            (self.rp / "pack_icon.png").write_bytes(icon)
        
        # ✅ Items BP com CATEGORIA no description
        for n, i in a.items.items():
            self._save({
                "format_version": "1.20.80",
                "minecraft:item": {
                    "description": {
                        "identifier": f"{self.mod}:{i.id}",
                        # ✅ AJUSTE 3: category DENTRO de description
                        "category": "equipment" if i.tool else "items"
                    },
                    "components": {
                        "minecraft:icon": i.tex,
                        "minecraft:max_stack_size": i.stack,
                        **({} if i.dmg == 0 else {"minecraft:durability": {"max_durability": i.dmg}})
                    }
                }
            }, self.bp / "items" / f"{n}.json")
            self.cnt['bp'] += 1
        
        # Items RP
        for n, i in a.items.items():
            self._save({
                "format_version": "1.20.80",
                "minecraft:item": {
                    "description": {"identifier": f"{self.mod}:{i.id}"},
                    "components": {"minecraft:icon": i.tex}
                }
            }, self.rp / "items" / f"{n}.json")
            self.cnt['rp'] += 1
        
        # Blocos
        for n, b in a.blocks.items():
            self._save({
                "format_version": "1.20.80",
                "minecraft:block": {
                    "description": {"identifier": f"{self.mod}:{b.id}"},
                    "components": {
                        "minecraft:destructible_by_mining": {"seconds_to_destroy": b.hard/1.5},
                        "minecraft:geometry": "geometry.cube",
                        "minecraft:material_instances": {
                            "*": {"texture": b.tex, "render_method": "opaque"}
                        }
                    }
                }
            }, self.bp / "blocks" / f"{n}.json")
            self.cnt['blk'] += 1
        
        # Texturas
        for n, d in a.item_tex.items():
            (self.rp / "textures" / "items" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
        for n, d in a.block_tex.items():
            (self.rp / "textures" / "blocks" / f"{n}.png").write_bytes(d)
            self.cnt['tex'] += 1
        
        # ✅ AJUSTE 2: item_texture.json com estrutura EXATA
        # ✅ AJUSTE 4: SEM .png no caminho
        self._save({
            "resource_pack_name": self.mod,
            "texture_name": "atlas.items",
            "texture_data": {
                i.tex: {
                    "textures": f"textures/items/{i.tex}"  # ✅ SEM .png
                }
                for i in a.items.values()
            }
        }, self.rp / "textures" / "item_texture.json")
        print(f"   ✓ item_texture.json ({len(a.items)} entradas)")
        
        # terrain_texture.json
        if a.blocks:
            self._save({
                "resource_pack_name": self.mod,
                "texture_name": "atlas.terrain",
                "texture_data": {
                    b.tex: {
                        "textures": f"textures/blocks/{b.tex}"  # ✅ SEM .png
                    }
                    for b in a.blocks.values()
                }
            }, self.rp / "textures" / "terrain_texture.json")
            
            # blocks.json
            self._save({
                f"{self.mod}:{n}": {"textures": b.tex, "sound": "stone"}
                for n, b in a.blocks.items()
            }, self.rp / "blocks.json")
            print(f"   ✓ terrain_texture.json e blocks.json ({len(a.blocks)} blocos)")
        
        # Lang
        self._save({"languages": ["en_US"]}, self.rp / "texts" / "languages.json")
        entries = [f"item.{self.mod}:{n}.name={n.replace('_',' ').title()}" for n in a.items]
        entries += [f"tile.{self.mod}:{n}.name={n.replace('_',' ').title()}" for n in a.blocks]
        (self.rp / "texts" / "en_US.lang").write_text("\n".join(entries), encoding='utf-8')
        
        # Pack
        pack = self.out / f"{self.mod}.mcaddon"
        with zipfile.ZipFile(pack, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in self.bp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.out))
            for f in self.rp.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(self.out))
        
        print(f"\n✅ {pack.name} ({pack.stat().st_size/1024:.1f}KB)")
        print(f"   Items BP: {self.cnt['bp']}, Items RP: {self.cnt['rp']}")
        print(f"   Blocos: {self.cnt['blk']}, Texturas: {self.cnt['tex']}")
        print("\n🎮 Texturas devem 'colar' nos items agora!")
    
    def _save(self, data: Dict, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def transpile_jar(jar_path: str, output_folder: str) -> Dict[str, Any]:
    try:
        print("=" * 60)
        print("🚀 TRANSPILER v4.1 FINAL")
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
                'items_processed': g.cnt['bp'],
                'blocks_processed': g.cnt['blk'],
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
