# transpiler_engine.py
"""
Motor Completo de Transpilação: Minecraft Java Edition → Bedrock Edition
Autor: Sistema de Conversão Avaritia
Versão: 1.0.0
"""

import json
import zipfile
import re
import uuid
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import hashlib
from datetime import datetime

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class JavaItem:
    """Representação completa de um Item do Java Edition"""
    class_name: str
    identifier: str = ""
    max_damage: int = 0
    max_stack_size: int = 64
    is_fireproof: bool = False
    armor_value: int = 0
    armor_toughness: float = 0.0
    knockback_resistance: float = 0.0
    attack_damage: float = 0.0
    attack_speed: float = -2.4
    mining_speed: float = 1.0
    mining_level: int = 0
    rarity: str = "common"
    is_enchantable: bool = True
    enchantment_value: int = 0
    is_edible: bool = False
    food_value: int = 0
    saturation: float = 0.0
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    methods: Dict[str, str] = field(default_factory=dict)
    texture_path: str = ""
    model_path: str = ""

@dataclass
class JavaRecipe:
    """Representação de uma Receita do Java Edition"""
    recipe_id: str
    recipe_type: str  # shaped, shapeless, smelting, etc.
    pattern: List[str] = field(default_factory=list)
    key: Dict[str, Dict] = field(default_factory=dict)
    ingredients: List[Dict] = field(default_factory=list)
    result: Dict = field(default_factory=dict)
    group: str = ""
    is_extreme: bool = False  # 9x9 crafting

@dataclass
class JavaBlock:
    """Representação de um Bloco do Java Edition"""
    class_name: str
    identifier: str = ""
    hardness: float = 1.0
    resistance: float = 1.0
    light_emission: int = 0
    requires_tool: bool = False
    material: str = "stone"
    sound_type: str = "stone"
    is_tickable: bool = False
    custom_properties: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# ANALISADOR DE BYTECODE JAVA
# ============================================================================

class JavaBytecodeAnalyzer:
    """Analisa bytecode Java para extrair informações de classes"""
    
    # Padrões de detecção (regex otimizados)
    PATTERNS = {
        'stack_size': rb'stacksTo\((\d+)\)',
        'durability': rb'durability\(([\w.]+)\)',
        'fire_resistant': rb'fireResistant\(\)',
        'attack_damage': rb'new\s+(?:Sword|Axe|)Item\([^,]+,\s*(\d+(?:\.\d+)?)',
        'attack_speed': rb'new\s+(?:Sword|Axe|)Item\([^,]+,[^,]+,\s*(-?\d+(?:\.\d+)?)',
        'mining_speed': rb'getDestroySpeed[^{]+return\s+([\w.]+)',
        'armor_value': rb'new\s+ArmorItem\([^,]+,\s*[^,]+,\s*(\d+)',
        'armor_toughness': rb'new\s+ArmorItem\([^,]+,\s*[^,]+,\s*[^,]+,\s*(\d+(?:\.\d+)?)',
        'rarity': rb'rarity\(Rarity\.(\w+)\)',
        'food': rb'food\(new\s+FoodProperties\.Builder\(\)\.nutrition\((\d+)\)\.saturationMod\(([\d.]+)\)',
        'enchantment_value': rb'getEnchantmentValue[^{]+return\s+(\d+)',
        'max_value': rb'(Integer|Float)\.MAX_VALUE',
        'tool_tier': rb'Tiers\.(\w+)',
    }
    
    # Mapeamento de métodos importantes
    CRITICAL_METHODS = [
        'hurtEnemy', 'getDestroySpeed', 'onLeftClickEntity',
        'inventoryTick', 'useOn', 'use', 'interactLivingEntity',
        'mineBlock', 'canAttackBlock', 'getUseDuration'
    ]
    
    @staticmethod
    def analyze_class(bytecode: bytes, filename: str) -> Optional[JavaItem]:
        """Analisa bytecode e retorna JavaItem"""
        
        # Detecta tipo de classe
        if not (b'extends Item' in bytecode or 
                b'extends SwordItem' in bytecode or
                b'extends ArmorItem' in bytecode or
                b'extends ToolItem' in bytecode):
            return None
        
        item = JavaItem(class_name=filename)
        
        # Extrai identificador do nome da classe
        class_name = Path(filename).stem
        item.identifier = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        
        # Análise de atributos
        for attr_name, pattern in JavaBytecodeAnalyzer.PATTERNS.items():
            matches = re.finditer(pattern, bytecode)
            for match in matches:
                JavaBytecodeAnalyzer._process_match(item, attr_name, match)
        
        # Detecção de métodos customizados
        for method in JavaBytecodeAnalyzer.CRITICAL_METHODS:
            if method.encode() in bytecode:
                item.methods[method] = JavaBytecodeAnalyzer._extract_method_body(
                    bytecode, method
                )
        
        return item
    
    @staticmethod
    def _process_match(item: JavaItem, attr_name: str, match: re.Match):
        """Processa match de regex e atualiza item"""
        try:
            if attr_name == 'stack_size':
                item.max_stack_size = int(match.group(1))
            
            elif attr_name == 'durability':
                durability_str = match.group(1).decode()
                if 'MAX_VALUE' in durability_str:
                    item.max_damage = 2147483647
                else:
                    item.max_damage = int(durability_str)
            
            elif attr_name == 'fire_resistant':
                item.is_fireproof = True
            
            elif attr_name == 'attack_damage':
                item.attack_damage = float(match.group(1))
            
            elif attr_name == 'attack_speed':
                item.attack_speed = float(match.group(1))
            
            elif attr_name == 'mining_speed':
                speed_str = match.group(1).decode()
                if 'MAX_VALUE' in speed_str:
                    item.mining_speed = 999999.0
                else:
                    try:
                        item.mining_speed = float(speed_str)
                    except:
                        pass
            
            elif attr_name == 'armor_value':
                item.armor_value = int(match.group(1))
            
            elif attr_name == 'armor_toughness':
                item.armor_toughness = float(match.group(1))
            
            elif attr_name == 'rarity':
                item.rarity = match.group(1).decode().lower()
            
            elif attr_name == 'food':
                item.is_edible = True
                item.food_value = int(match.group(1))
                item.saturation = float(match.group(2))
            
            elif attr_name == 'enchantment_value':
                item.enchantment_value = int(match.group(1))
            
            elif attr_name == 'tool_tier':
                tier = match.group(1).decode()
                tier_levels = {
                    'WOOD': 0, 'STONE': 1, 'IRON': 2,
                    'DIAMOND': 3, 'NETHERITE': 4, 'GOLD': 0
                }
                item.mining_level = tier_levels.get(tier, 0)
        
        except Exception as e:
            print(f"⚠️  Erro ao processar {attr_name}: {e}")
    
    @staticmethod
    def _extract_method_body(bytecode: bytes, method_name: str) -> str:
        """Extrai corpo do método (simplificado)"""
        # Em produção: usar ASM library ou Javassist
        pattern = rf'{method_name}\([^{{]*\{{([^}}]+)\}}'.encode()
        match = re.search(pattern, bytecode, re.DOTALL)
        
        if match:
            return match.group(1).decode('latin-1', errors='ignore')
        return ""

# ============================================================================
# PARSER DE RECEITAS
# ============================================================================

class RecipeParser:
    """Parse de receitas JSON do Java Edition"""
    
    @staticmethod
    def parse_recipe_file(recipe_data: Dict, recipe_id: str) -> JavaRecipe:
        """Converte JSON de receita Java para JavaRecipe"""
        
        recipe_type = recipe_data.get('type', '').split(':')[-1]
        
        recipe = JavaRecipe(
            recipe_id=recipe_id,
            recipe_type=recipe_type,
            group=recipe_data.get('group', ''),
            result=recipe_data.get('result', {})
        )
        
        # Shaped recipes
        if 'pattern' in recipe_data:
            recipe.pattern = recipe_data['pattern']
            recipe.key = recipe_data.get('key', {})
            
            # Detecta extreme crafting (9x9)
            if len(recipe.pattern) > 3 or any(len(p) > 3 for p in recipe.pattern):
                recipe.is_extreme = True
        
        # Shapeless recipes
        elif 'ingredients' in recipe_data:
            recipe.ingredients = recipe_data['ingredients']
        
        return recipe

# ============================================================================
# CONVERSOR BEDROCK
# ============================================================================

class BedrockConverter:
    """Converte estruturas Java para formato Bedrock"""
    
    # Mapeamento de componentes
    COMPONENT_MAPPING = {
        'common': {},
        'uncommon': {'minecraft:hover_text_color': 'yellow'},
        'rare': {'minecraft:hover_text_color': 'aqua'},
        'epic': {'minecraft:hover_text_color': 'light_purple'},
    }
    
    @staticmethod
    def convert_item(java_item: JavaItem) -> Dict:
        """Converte JavaItem para formato Bedrock completo"""
        
        bedrock = {
            "format_version": "1.20.60",
            "minecraft:item": {
                "description": {
                    "identifier": f"avaritia:{java_item.identifier}",
                    "menu_category": {
                        "category": "equipment" if java_item.attack_damage > 0 else "items"
                    }
                },
                "components": {}
            }
        }
        
        components = bedrock["minecraft:item"]["components"]
        
        # === DURABILIDADE ===
        if java_item.max_damage > 0:
            # Bedrock limita a 32767
            actual_durability = min(java_item.max_damage, 32767)
            
            components["minecraft:durability"] = {
                "max_durability": actual_durability
            }
            
            # Item "indestrutível" (MAX_VALUE do Java)
            if java_item.max_damage >= 2147483647:
                components["minecraft:durability"]["damage_chance"] = {
                    "min": 0,
                    "max": 0
                }
        
        # === STACK SIZE ===
        components["minecraft:max_stack_size"] = java_item.max_stack_size
        
        # === FIREPROOF ===
        if java_item.is_fireproof:
            components["minecraft:ignores_damage"] = True
        
        # === DANO DE ATAQUE ===
        if java_item.attack_damage > 0:
            components["minecraft:damage"] = java_item.attack_damage
        
        # === ARMADURA ===
        if java_item.armor_value > 0:
            components["minecraft:armor"] = {
                "protection": java_item.armor_value
            }
            
            if java_item.armor_toughness > 0:
                components["minecraft:armor"]["texture_type"] = "netherite"
        
        # === FERRAMENTA DE MINERAÇÃO ===
        if java_item.mining_speed > 1.0:
            components["minecraft:digger"] = {
                "use_efficiency": True,
                "destroy_speeds": [
                    {
                        "block": {"tags": "q.any_tag('stone', 'metal', 'wood')"},
                        "speed": int(java_item.mining_speed)
                    }
                ]
            }
        
        # === COMIDA ===
        if java_item.is_edible:
            components["minecraft:food"] = {
                "nutrition": java_item.food_value,
                "saturation_modifier": java_item.saturation,
                "can_always_eat": False
            }
        
        # === ENCANTAMENTO ===
        if java_item.enchantment_value > 0:
            components["minecraft:enchantable"] = {
                "slot": "slot.weapon.mainhand",
                "value": java_item.enchantment_value
            }
        
        # === TAGS DE MÉTODOS ESPECIAIS ===
        tags = []
        
        if 'hurtEnemy' in java_item.methods:
            tags.append('avaritia:custom_attack')
        
        if 'getDestroySpeed' in java_item.methods and java_item.mining_speed > 1000:
            tags.append('avaritia:instant_break')
        
        if 'inventoryTick' in java_item.methods:
            tags.append('avaritia:has_tick')
        
        if tags:
            components["minecraft:tags"] = {"tags": tags}
        
        # === RARITY ===
        if java_item.rarity in BedrockConverter.COMPONENT_MAPPING:
            components.update(BedrockConverter.COMPONENT_MAPPING[java_item.rarity])
        
        return bedrock
    
    @staticmethod
    def convert_recipe(java_recipe: JavaRecipe) -> Dict:
        """Converte receita Java para Bedrock"""
        
        if java_recipe.is_extreme:
            return BedrockConverter._convert_extreme_recipe(java_recipe)
        
        # Receitas shaped normais
        if java_recipe.recipe_type == 'shaped':
            return {
                "format_version": "1.20.60",
                "minecraft:recipe_shaped": {
                    "description": {
                        "identifier": f"avaritia:{java_recipe.recipe_id}"
                    },
                    "tags": ["crafting_table"],
                    "pattern": java_recipe.pattern,
                    "key": BedrockConverter._convert_recipe_key(java_recipe.key),
                    "result": BedrockConverter._convert_recipe_result(java_recipe.result)
                }
            }
        
        # Receitas shapeless
        elif java_recipe.recipe_type == 'shapeless':
            return {
                "format_version": "1.20.60",
                "minecraft:recipe_shapeless": {
                    "description": {
                        "identifier": f"avaritia:{java_recipe.recipe_id}"
                    },
                    "tags": ["crafting_table"],
                    "ingredients": [
                        BedrockConverter._convert_ingredient(ing) 
                        for ing in java_recipe.ingredients
                    ],
                    "result": BedrockConverter._convert_recipe_result(java_recipe.result)
                }
            }
        
        return {}
    
    @staticmethod
    def _convert_extreme_recipe(java_recipe: JavaRecipe) -> Dict:
        """
        Converte receita 9x9 (Extreme Crafting)
        Retorna definição de bloco + script de UI
        """
        return {
            "type": "extreme_crafting",
            "requires_custom_ui": True,
            "block_definition": {
                "format_version": "1.20.60",
                "minecraft:block": {
                    "description": {
                        "identifier": "avaritia:extreme_crafting_table"
                    },
                    "components": {
                        "minecraft:material_instances": {
                            "*": {
                                "texture": "extreme_crafting_table",
                                "render_method": "opaque"
                            }
                        },
                        "minecraft:geometry": "geometry.extreme_crafting_table",
                        "minecraft:on_interact": {
                            "event": "open_extreme_ui"
                        }
                    }
                }
            },
            "recipe_data": asdict(java_recipe)
        }
    
    @staticmethod
    def _convert_recipe_key(key: Dict) -> Dict:
        """Converte key de receita"""
        converted = {}
        for symbol, ingredient in key.items():
            if 'item' in ingredient:
                item_id = ingredient['item'].replace('minecraft:', '').replace('avaritia:', 'avaritia:')
                converted[symbol] = {"item": item_id}
            elif 'tag' in ingredient:
                converted[symbol] = {"tag": ingredient['tag']}
        return converted
    
    @staticmethod
    def _convert_ingredient(ingredient: Dict) -> Dict:
        """Converte ingrediente individual"""
        if 'item' in ingredient:
            return {"item": ingredient['item']}
        elif 'tag' in ingredient:
            return {"tag": ingredient['tag']}
        return ingredient
    
    @staticmethod
    def _convert_recipe_result(result: Dict) -> Dict:
        """Converte resultado da receita"""
        item_id = result.get('item', '').replace('minecraft:', '').replace('avaritia:', 'avaritia:')
        return {
            "item": item_id,
            "count": result.get('count', 1)
        }

# ============================================================================
# GERADOR DE SCRIPTS BEDROCK
# ============================================================================

class ScriptGenerator:
    """Gera scripts JavaScript para comportamentos customizados"""
    
    @staticmethod
    def generate_item_script(java_item: JavaItem) -> Optional[str]:
        """Gera script para item com métodos customizados"""
        
        if not java_item.methods:
            return None
        
        script_parts = []
        
        # Header
        script_parts.append(f"""
// Auto-generated script for {java_item.identifier}
// Generated: {datetime.now().isoformat()}

import {{ world, system, ItemStack }} from "@minecraft/server";

const ITEM_ID = "avaritia:{java_item.identifier}";
""")
        
        # hurtEnemy → Custom Attack
        if 'hurtEnemy' in java_item.methods:
            damage = "999999" if "MAX_VALUE" in java_item.methods['hurtEnemy'] else str(java_item.attack_damage)
            
            script_parts.append(f"""
// Custom attack handler
world.afterEvents.entityHurt.subscribe((event) => {{
    const {{ hurtEntity, damageSource }} = event;
    const attacker = damageSource.damagingEntity;
    
    if (!attacker || attacker.typeId !== "minecraft:player") return;
    
    const inventory = attacker.getComponent("inventory");
    const item = inventory.container.getItem(attacker.selectedSlot);
    
    if (item?.typeId === ITEM_ID) {{
        // Instant kill or massive damage
        hurtEntity.applyDamage({damage}, {{
            cause: "entityAttack",
            damagingEntity: attacker
        }});
        
        // Visual effect
        hurtEntity.dimension.spawnParticle(
            "minecraft:critical_hit_emitter",
            hurtEntity.location
        );
    }}
}});
""")
        
        # getDestroySpeed → Instant Break
        if 'getDestroySpeed' in java_item.methods and java_item.mining_speed > 1000:
            script_parts.append(f"""
// Instant block breaking
system.runInterval(() => {{
    for (const player of world.getAllPlayers()) {{
        const item = player.getComponent("inventory")
            .container.getItem(player.selectedSlot);
        
        if (item?.typeId !== ITEM_ID) continue;
        
        const blockRay = player.getBlockFromViewDirection({{ maxDistance: 6 }});
        
        if (blockRay && player.isSneaking) {{
            const block = blockRay.block;
            const blockType = block.type.id;
            
            // Skip bedrock and other unbreakable blocks
            if (blockType === "minecraft:bedrock") continue;
            
            // Store drops
            try {{
                const drops = block.getItemStack(1);
                block.dimension.spawnItem(drops, block.location);
            }} catch (e) {{
                // Some blocks don't have drops
            }}
            
            // Break instantly
            block.setType("minecraft:air");
            
            // Particle effect
            block.dimension.spawnParticle(
                "minecraft:villager_happy",
                block.location
            );
        }}
    }}
}}, 1);
""")
        
        # inventoryTick → Passive Effects
        if 'inventoryTick' in java_item.methods:
            script_parts.append(f"""
// Passive inventory tick effects
system.runInterval(() => {{
    for (const player of world.getAllPlayers()) {{
        const inventory = player.getComponent("inventory").container;
        
        for (let i = 0; i < inventory.size; i++) {{
            const item = inventory.getItem(i);
            if (item?.typeId === ITEM_ID) {{
                // Add custom effects here
                player.addEffect("regeneration", 40, {{
                    amplifier: 1,
                    showParticles: false
                }});
                break;
            }}
        }}
    }}
}}, 20); // Every second
""")
        
        return "".join(script_parts)
    
    @staticmethod
    def generate_extreme_crafting_script(recipe: JavaRecipe) -> str:
        """Gera script completo para Extreme Crafting UI"""
        
        return f"""
// Extreme Crafting Table UI System
// Recipe: {recipe.recipe_id}

import {{ world, system }} from "@minecraft/server";
import {{ ActionFormData, ModalFormData }} from "@minecraft/server-ui";

const RECIPE_PATTERN = {json.dumps(recipe.pattern, indent=4)};
const RECIPE_KEY = {json.dumps(recipe.key, indent=4)};
const RESULT = {json.dumps(recipe.result, indent=4)};

// Storage for crafting grids (per player)
const craftingGrids = new Map();

// Initialize grid for player
function initGrid(playerId) {{
    if (!craftingGrids.has(playerId)) {{
        craftingGrids.set(playerId, Array(81).fill(null)); // 9x9 = 81 slots
    }}
    return craftingGrids.get(playerId);
}}

// Check if pattern matches
function checkPattern(grid) {{
    const gridSize = 9;
    
    for (let row = 0; row < RECIPE_PATTERN.length; row++) {{
        const patternRow = RECIPE_PATTERN[row];
        
        for (let col = 0; col < patternRow.length; col++) {{
            const symbol = patternRow[col];
            const gridIndex = row * gridSize + col;
            const gridItem = grid[gridIndex];
            
            if (symbol === ' ') {{
                if (gridItem !== null) return false;
            }} else {{
                const requiredItem = RECIPE_KEY[symbol];
                if (!gridItem || gridItem.typeId !== requiredItem.item) {{
                    return false;
                }}
            }}
        }}
    }}
    
    return true;
}}

// Open crafting UI
world.beforeEvents.playerInteractWithBlock.subscribe((event) => {{
    if (event.block.typeId === "avaritia:extreme_crafting_table") {{
        system.run(() => {{
            showCraftingUI(event.player);
        }});
    }}
}});

async function showCraftingUI(player) {{
    const grid = initGrid(player.id);
    
    const form = new ActionFormData()
        .title("§dExtreme Crafting Table")
        .body("9x9 Crafting Grid\\n\\nPlace items to craft...")
        .button("View Grid")
        .button("Craft Item")
        .button("Clear Grid");
    
    const response = await form.show(player);
    
    if (response.canceled) return;
    
    switch(response.selection) {{
        case 0:
            await showGridUI(player, grid);
            break;
        case 1:
            if (checkPattern(grid)) {{
                craftItem(player, grid);
            }} else {{
                player.sendMessage("§cPattern doesn't match any recipe!");
            }}
            break;
        case 2:
            craftingGrids.set(player.id, Array(81).fill(null));
            player.sendMessage("§aGrid cleared!");
            break;
    }}
}}

async function showGridUI(player, grid) {{
    // In production: create custom 9x9 UI with chest interface
    // This is a simplified version
    
    player.sendMessage("§eExtreme Crafting Grid Status:");
    
    for (let row = 0; row < 9; row++) {{
        let rowDisplay = "";
        for (let col = 0; col < 9; col++) {{
            const item = grid[row * 9 + col];
            rowDisplay += item ? "§a■" : "§7□";
        }}
        player.sendMessage(rowDisplay);
    }}
}}

function craftItem(player, grid) {{
    // Consume items
    for (let i = 0; i < grid.length; i++) {{
        if (grid[i]) {{
            grid[i] = null; // Remove from virtual grid
        }}
    }}
    
    // Give result
    const resultItem = new ItemStack(RESULT.item, RESULT.count || 1);
    const inventory = player.getComponent("inventory");
    inventory.container.addItem(resultItem);
    
    player.sendMessage("§aCrafted: " + RESULT.item);
    player.playSound("random.orb");
}}

// Export for other scripts
export {{ showCraftingUI, checkPattern }};
"""

# ============================================================================
# GERENCIADOR DE ASSETS
# ============================================================================

class AssetManager:
    """Gerencia extração e conversão de assets (texturas, modelos, sons)"""
    
    TEXTURE_MAPPING = {
        'assets/*/textures/item': 'resource_pack/textures/items',
        'assets/*/textures/block': 'resource_pack/textures/blocks',
        'assets/*/textures/entity': 'resource_pack/textures/entity',
        'assets/*/models/item': 'resource_pack/models/items',
        'assets/*/models/block': 'resource_pack/models/blocks',
        'assets/*/sounds': 'resource_pack/sounds',
    }
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.texture_map: Dict[str, str] = {}
    
    def extract_assets(self, jar: zipfile.ZipFile):
        """Extrai todos os assets do JAR"""
        
        for file_info in jar.filelist:
            file_path = file_info.filename
            
            # Pula diretórios
            if file_info.is_dir():
                continue
            
            # Processa cada tipo de asset
            for java_path, bedrock_path in self.TEXTURE_MAPPING.items():
                if self._matches_pattern(file_path, java_path):
                    self._extract_and_convert(jar, file_info, bedrock_path)
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Verifica se path corresponde ao pattern"""
        pattern_parts = pattern.split('/')
        path_parts = path.split('/')
        
        if len(pattern_parts) > len(path_parts):
            return False
        
        for i, part in enumerate(pattern_parts):
            if part == '*':
                continue
            if i >= len(path_parts) or part != path_parts[i]:
                return False
        
        return True
    
    def _extract_and_convert(self, jar: zipfile.ZipFile, file_info, bedrock_path: str):
        """Extrai arquivo e converte para formato Bedrock"""
        
        file_path = Path(file_info.filename)
        target_path = self.output_dir / bedrock_path / file_path.name
        
        # Cria diretório
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Extrai arquivo
        content = jar.read(file_info.filename)
        
        # Conversões específicas
        if file_path.suffix == '.png':
            # Texturas PNG são compatíveis
            target_path.write_bytes(content)
            self.texture_map[file_path.stem] = str(target_path.relative_to(self.output_dir))
        
        elif file_path.suffix == '.json' and 'models' in file_info.filename:
            # Modelos precisam ser convertidos
            self._convert_model(content, target_path)
        
        elif file_path.suffix == '.ogg':
            # Sons são compatíveis
            target_path.write_bytes(content)
    
    def _convert_model(self, java_model_data: bytes, target_path: Path):
        """Converte modelo Java para formato Bedrock"""
        try:
            java_model = json.loads(java_model_data)
            
            # Bedrock usa geometria diferente
            bedrock_model = {
                "format_version": "1.12.0",
                "minecraft:geometry": [{
                    "description": {
                        "identifier": f"geometry.{target_path.stem}",
                        "texture_width": 16,
                        "texture_height": 16
                    },
                    "bones": []
                }]
            }
            
            # Conversão simplificada - em produção, use conversor completo
            target_path.write_text(json.dumps(bedrock_model, indent=2))
            
        except json.JSONDecodeError:
            print(f"⚠️  Erro ao converter modelo: {target_path.name}")
    
    def generate_texture_list(self) -> Dict:
        """Gera terrain_texture.json para Bedrock"""
        return {
            "resource_pack_name": "avaritia",
            "texture_name": "atlas.terrain",
            "texture_data": {
                texture_id: {
                    "textures": texture_path
                }
                for texture_id, texture_path in self.texture_map.items()
            }
        }

# ============================================================================
# MOTOR PRINCIPAL
# ============================================================================

class AvaritiaTranspiler:
    """Motor principal de transpilação"""
    
    def __init__(self, jar_path: str, output_dir: str, mod_name: str = "avaritia"):
        self.jar_path = Path(jar_path)
        self.output_dir = Path(output_dir)
        self.mod_name = mod_name
        
        # Estruturas de dados
        self.items: List[JavaItem] = []
        self.recipes: List[JavaRecipe] = []
        self.blocks: List[JavaBlock] = []
        
        # Gerenciadores
        self.asset_manager = AssetManager(self.output_dir)
        self.analyzer = JavaBytecodeAnalyzer()
        
        # Estatísticas
        self.stats = {
            'items_processed': 0,
            'recipes_converted': 0,
            'scripts_generated': 0,
            'assets_extracted': 0,
            'errors': []
        }
    
    def run(self):
        """Executa pipeline completo de transpilação"""
        
        print(f"🚀 Iniciando transpilação: {self.jar_path.name}")
        print("=" * 60)
        
        # Fase 1: Análise do JAR
        print("\n📦 Fase 1: Analisando arquivo JAR...")
        self.parse_jar()
        
        # Fase 2: Conversão
        print("\n🔄 Fase 2: Convertendo para formato Bedrock...")
        self.convert_all()
        
        # Fase 3: Geração de scripts
        print("\n📝 Fase 3: Gerando scripts customizados...")
        self.generate_scripts()
        
        # Fase 4: Estruturação do addon
        print("\n📁 Fase 4: Montando estrutura do addon...")
        self.build_addon_structure()
        
        # Fase 5: Empacotamento final
        print("\n📦 Fase 5: Gerando .mcaddon...")
        self.package_mcaddon()
        
        # Relatório final
        self.print_report()
    
    def parse_jar(self):
        """Fase 1: Parse do arquivo JAR"""
        
        if not self.jar_path.exists():
            raise FileNotFoundError(f"JAR não encontrado: {self.jar_path}")
        
        with zipfile.ZipFile(self.jar_path, 'r') as jar:
            total_files = len(jar.filelist)
            processed = 0
            
            for file_info in jar.filelist:
                processed += 1
                
                if processed % 100 == 0:
                    print(f"   Processando: {processed}/{total_files} arquivos...")
                
                filename = file_info.filename
                
                # Parse de classes (items/blocks)
                if filename.endswith('.class'):
                    if '/item/' in filename.lower():
                        self._parse_item_class(jar, file_info)
                    elif '/block/' in filename.lower():
                        self._parse_block_class(jar, file_info)
                
                # Parse de receitas
                elif 'recipes/' in filename and filename.endswith('.json'):
                    self._parse_recipe(jar, file_info)
                
                # Extração de assets
                elif filename.startswith('assets/'):
                    self.asset_manager.extract_assets(jar)
                    self.stats['assets_extracted'] += 1
        
        print(f"   ✓ {len(self.items)} items encontrados")
        print(f"   ✓ {len(self.recipes)} receitas encontradas")
        print(f"   ✓ {self.stats['assets_extracted']} assets extraídos")
    
    def _parse_item_class(self, jar: zipfile.ZipFile, file_info):
        """Parse de classe de item"""
        try:
            bytecode = jar.read(file_info.filename)
            item = self.analyzer.analyze_class(bytecode, file_info.filename)
            
            if item:
                self.items.append(item)
                self.stats['items_processed'] += 1
        
        except Exception as e:
            self.stats['errors'].append(f"Erro ao parsear {file_info.filename}: {e}")
    
    def _parse_block_class(self, jar: zipfile.ZipFile, file_info):
        """Parse de classe de bloco"""
        # Similar ao parse de items
        pass
    
    def _parse_recipe(self, jar: zipfile.ZipFile, file_info):
        """Parse de arquivo de receita"""
        try:
            recipe_data = json.loads(jar.read(file_info.filename))
            recipe_id = Path(file_info.filename).stem
            
            recipe = RecipeParser.parse_recipe_file(recipe_data, recipe_id)
            self.recipes.append(recipe)
            
        except Exception as e:
            self.stats['errors'].append(f"Erro ao parsear receita {file_info.filename}: {e}")
    
    def convert_all(self):
        """Fase 2: Converte todas as estruturas"""
        
        converter = BedrockConverter()
        
        # Converte items
        for item in self.items:
            bedrock_item = converter.convert_item(item)
            self._save_json(
                bedrock_item,
                self.output_dir / "behavior_pack" / "items" / f"{item.identifier}.json"
            )
        
        # Converte receitas
        for recipe in self.recipes:
            bedrock_recipe = converter.convert_recipe(recipe)
            
            if recipe.is_extreme:
                # Salva definição de bloco
                self._save_json(
                    bedrock_recipe['block_definition'],
                    self.output_dir / "behavior_pack" / "blocks" / "extreme_crafting_table.json"
                )
            else:
                self._save_json(
                    bedrock_recipe,
                    self.output_dir / "behavior_pack" / "recipes" / f"{recipe.recipe_id}.json"
                )
            
            self.stats['recipes_converted'] += 1
    
    def generate_scripts(self):
        """Fase 3: Gera scripts JavaScript"""
        
        script_gen = ScriptGenerator()
        scripts_dir = self.output_dir / "behavior_pack" / "scripts" / "items"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Scripts de items
        for item in self.items:
            if item.methods:
                script = script_gen.generate_item_script(item)
                if script:
                    (scripts_dir / f"{item.identifier}.js").write_text(script)
                    self.stats['scripts_generated'] += 1
        
        # Scripts de extreme crafting
        for recipe in self.recipes:
            if recipe.is_extreme:
                script = script_gen.generate_extreme_crafting_script(recipe)
                extreme_script_path = self.output_dir / "behavior_pack" / "scripts" / "extreme_crafting.js"
                extreme_script_path.write_text(script)
                self.stats['scripts_generated'] += 1
        
        # Gera index.js principal
        self._generate_main_script()
    
    def _generate_main_script(self):
        """Gera script principal que importa todos os módulos"""
        
        main_script = """
// Auto-generated main script
import { world } from "@minecraft/server";

// Import all item scripts
"""
        
        for item in self.items:
            if item.methods:
                main_script += f'import "./items/{item.identifier}.js";\n'
        
        # Adiciona extreme crafting se necessário
        if any(r.is_extreme for r in self.recipes):
            main_script += 'import "./extreme_crafting.js";\n'
        
        main_script += """
// Initialization
world.afterEvents.worldInitialize.subscribe(() => {
    console.log("§aAvaritia Bedrock Addon loaded successfully!");
});
"""
        
        (self.output_dir / "behavior_pack" / "scripts" / "main.js").write_text(main_script)
    
    def build_addon_structure(self):
        """Fase 4: Constrói estrutura completa do addon"""
        
        bp_path = self.output_dir / "behavior_pack"
        rp_path = self.output_dir / "resource_pack"
        
        # Gera manifests
        self._generate_manifest(bp_path, "behavior")
        self._generate_manifest(rp_path, "resource")
        
        # Gera texture list
        texture_list = self.asset_manager.generate_texture_list()
        self._save_json(
            texture_list,
            rp_path / "textures" / "terrain_texture.json"
        )
        
        # Gera item_texture.json
        item_textures = {
            "resource_pack_name": self.mod_name,
            "texture_name": "atlas.items",
            "texture_data": {
                f"{self.mod_name}:{item.identifier}": {
                    "textures": f"textures/items/{item.identifier}"
                }
                for item in self.items
            }
        }
        self._save_json(
            item_textures,
            rp_path / "textures" / "item_texture.json"
        )
        
        # Gera languages (en_US.lang)
        self._generate_language_files(rp_path)
    
    def _generate_manifest(self, pack_path: Path, pack_type: str):
        """Gera manifest.json"""
        
        pack_uuid = str(uuid.uuid4())
        module_uuid = str(uuid.uuid4())
        
        manifest = {
            "format_version": 2,
            "header": {
                "name": f"{self.mod_name.title()} {pack_type.title()} Pack",
                "description": f"Converted from Java Edition Mod\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "uuid": pack_uuid,
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 60]
            },
            "modules": [{
                "type": "data" if pack_type == "behavior" else "resources",
                "uuid": module_uuid,
                "version": [1, 0, 0]
            }]
        }
        
        # Adiciona dependências de scripts para BP
        if pack_type == "behavior":
            manifest["dependencies"] = [
                {
                    "module_name": "@minecraft/server",
                    "version": "1.9.0"
                },
                {
                    "module_name": "@minecraft/server-ui",
                    "version": "1.2.0"
                }
            ]
            
            # Adiciona capabilities
            manifest["capabilities"] = ["script_eval"]
        
        pack_path.mkdir(parents=True, exist_ok=True)
        self._save_json(manifest, pack_path / "manifest.json")
    
    def _generate_language_files(self, rp_path: Path):
        """Gera arquivos de tradução"""
        
        lang_path = rp_path / "texts"
        lang_path.mkdir(parents=True, exist_ok=True)
        
        # languages.json
        languages = {
            "languages": ["en_US"]
        }
        self._save_json(languages, lang_path / "languages.json")
        
        # en_US.lang
        lang_entries = []
        
        for item in self.items:
            item_name = item.identifier.replace('_', ' ').title()
            lang_entries.append(f"item.{self.mod_name}:{item.identifier}.name={item_name}")
        
        (lang_path / "en_US.lang").write_text("\n".join(lang_entries))
    
    def package_mcaddon(self):
        """Fase 5: Empacota tudo em .mcaddon"""
        
        mcaddon_path = self.output_dir / f"{self.mod_name}.mcaddon"
        
        with zipfile.ZipFile(mcaddon_path, 'w', zipfile.ZIP_DEFLATED) as mcaddon:
            # Adiciona behavior pack
            bp_path = self.output_dir / "behavior_pack"
            for file in bp_path.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(self.output_dir)
                    mcaddon.write(file, arcname)
            
            # Adiciona resource pack
            rp_path = self.output_dir / "resource_pack"
            for file in rp_path.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(self.output_dir)
                    mcaddon.write(file, arcname)
        
        print(f"\n✅ Addon gerado: {mcaddon_path}")
        print(f"   Tamanho: {mcaddon_path.stat().st_size / 1024:.2f} KB")
    
    def print_report(self):
        """Imprime relatório final"""
        
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO DE TRANSPILAÇÃO")
        print("=" * 60)
        print(f"Items convertidos:     {self.stats['items_processed']}")
        print(f"Receitas convertidas:  {self.stats['recipes_converted']}")
        print(f"Scripts gerados:       {self.stats['scripts_generated']}")
        print(f"Assets extraídos:      {self.stats['assets_extracted']}")
        
        if self.stats['errors']:
            print(f"\n⚠️  Erros encontrados: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:5]:  # Mostra só os 5 primeiros
                print(f"   - {error}")
            if len(self.stats['errors']) > 5:
                print(f"   ... e mais {len(self.stats['errors']) - 5} erros")
        
        print("\n✨ Transpilação concluída com sucesso!")
        print("=" * 60)
    
    def _save_json(self, data: Dict, path: Path):
        """Salva JSON formatado"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

def main():
    """Função principal"""
    
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python transpiler_engine.py <caminho_para_mod.jar> [output_dir]")
        print("\nExemplo:")
        print("  python transpiler_engine.py mods/Avaritia-1.20.1.jar output/")
        sys.exit(1)
    
    jar_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    # Extrai nome do mod do arquivo
    mod_name = Path(jar_path).stem.lower().split('-')[0]
    
    # Executa transpilador
    transpiler = AvaritiaTranspiler(
        jar_path=jar_path,
        output_dir=output_dir,
        mod_name=mod_name
    )
    
    try:
        transpiler.run()
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
