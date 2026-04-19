"""Tests for JavaSemanticChunker and ChunkManifest (Issue #1090)."""

import io
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agents.java_semantic_chunker import (
    ChunkInfo,
    ChunkManifest,
    JavaSemanticChunker,
    _detect_component_type,
    _estimate_tokens,
    _extract_class_info_regex,
    _extract_imports_regex,
    MAX_CHUNK_TOKENS,
)


SIMPLE_ITEM_CLASS = """\
package com.example.mymod.items;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.CreativeModeTab;

public class MySword extends Item {
    public MySword(Properties props) {
        super(props);
    }

    public void doSomething() {
        System.out.println("hello");
    }
}
"""

SIMPLE_BLOCK_CLASS = """\
package com.example.mymod.blocks;

import net.minecraft.world.level.block.Block;

public class MyOreBlock extends Block {
    public MyOreBlock(Properties props) {
        super(props);
    }
}
"""

ENTITY_CLASS = """\
package com.example.mymod.entities;

import net.minecraft.world.entity.LivingEntity;

public class MyMob extends LivingEntity {
}
"""


def _make_jar(sources: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, code in sources.items():
            zf.writestr(name, code)
    return buf.getvalue()


class TestEstimateTokens:
    def test_empty_string(self):
        assert _estimate_tokens("") == 1

    def test_short_string(self):
        assert _estimate_tokens("abcd") == 1

    def test_long_string(self):
        assert _estimate_tokens("a" * 400) == 100

    def test_typical_java_class(self):
        tokens = _estimate_tokens(SIMPLE_ITEM_CLASS)
        assert tokens > 0


class TestDetectComponentType:
    def test_item_class(self):
        assert _detect_component_type("MySword", "Item", [], []) == "items"

    def test_block_class(self):
        assert _detect_component_type("MyOreBlock", "Block", [], []) == "blocks"

    def test_entity_class(self):
        assert _detect_component_type("MyMob", "LivingEntity", [], []) == "entities"

    def test_recipe_class(self):
        assert _detect_component_type("MyRecipe", "ShapedRecipe", [], []) == "recipes"

    def test_event_class(self):
        assert _detect_component_type("MyEvent", "", [], ["SubscribeEvent"]) == "events"

    def test_gui_class(self):
        assert _detect_component_type("MyScreen", "Screen", [], []) == "gui"

    def test_unknown_class(self):
        assert _detect_component_type("SomeHelper", "", [], []) == "other"


class TestExtractImportsRegex:
    def test_basic_imports(self):
        code = "import net.minecraft.world.item.Item;\nimport java.util.List;"
        imports = _extract_imports_regex(code)
        assert "net.minecraft.world.item.Item" in imports
        assert "java.util.List" in imports

    def test_static_import(self):
        code = "import static net.minecraft.Mod.LOGGER;"
        imports = _extract_imports_regex(code)
        assert "net.minecraft.Mod.LOGGER" in imports

    def test_no_imports(self):
        assert _extract_imports_regex("class Foo {}") == []


class TestExtractClassInfoRegex:
    def test_simple_class(self):
        infos = _extract_class_info_regex("public class Foo {}")
        assert len(infos) >= 1
        assert infos[0][0] == "Foo"

    def test_extends(self):
        infos = _extract_class_info_regex("public class MySword extends Item {}")
        assert infos[0][1] == "Item"

    def test_implements(self):
        infos = _extract_class_info_regex(
            "public class MyClass implements Runnable, Serializable {}"
        )
        assert "Runnable" in infos[0][2]
        assert "Serializable" in infos[0][2]

    def test_no_class(self):
        infos = _extract_class_info_regex("int x = 1;")
        assert infos == []


class TestJavaSemanticChunker:
    def setup_method(self):
        self.chunker = JavaSemanticChunker()

    def test_build_manifest_single_class(self):
        sources = [("com/example/MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(
            sources, mod_id="mymod", mod_name="MyMod", loader="forge", loader_version="1.20.1"
        )
        assert isinstance(manifest, ChunkManifest)
        assert manifest.mod_id == "mymod"
        assert manifest.mod_name == "MyMod"
        assert manifest.total_chunks >= 1
        assert len(manifest.chunks) == manifest.total_chunks

    def test_chunk_has_context_header(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(
            sources, mod_id="mymod", mod_name="MyMod", loader="forge", loader_version="1.20.1"
        )
        for chunk in manifest.chunks:
            assert chunk.context_header != ""
            assert "MyMod" in chunk.context_header or "mymod" in chunk.context_header

    def test_chunk_component_type_item(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        assert any(c.component_type == "items" for c in manifest.chunks)

    def test_chunk_component_type_block(self):
        sources = [("MyOreBlock.java", SIMPLE_BLOCK_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        assert any(c.component_type == "blocks" for c in manifest.chunks)

    def test_chunk_component_type_entity(self):
        sources = [("MyMob.java", ENTITY_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        assert any(c.component_type == "entities" for c in manifest.chunks)

    def test_multiple_files(self):
        sources = [
            ("MySword.java", SIMPLE_ITEM_CLASS),
            ("MyOreBlock.java", SIMPLE_BLOCK_CLASS),
            ("MyMob.java", ENTITY_CLASS),
        ]
        manifest = self.chunker.build_manifest(sources)
        assert manifest.total_chunks >= 3

    def test_chunk_index_sequential(self):
        sources = [
            ("MySword.java", SIMPLE_ITEM_CLASS),
            ("MyOreBlock.java", SIMPLE_BLOCK_CLASS),
        ]
        manifest = self.chunker.build_manifest(sources)
        for i, chunk in enumerate(manifest.chunks):
            assert chunk.chunk_index == i

    def test_chunk_has_token_estimate(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        for chunk in manifest.chunks:
            assert chunk.token_estimate > 0

    def test_chunk_has_dependencies(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        all_deps = [d for c in manifest.chunks for d in c.dependencies]
        assert len(all_deps) > 0

    def test_large_class_split_by_methods(self):
        many_methods = "\n".join(
            f'    public void method{i}() {{\n        // method body for method number {i} with some padding text to ensure we hit the token limit properly\n        int x{i} = {i}; String s{i} = "value_{i}_padding_padding_padding";\n    }}\n'
            for i in range(300)
        )
        big_class = f"public class BigClass extends Block {{\n{many_methods}}}"
        sources = [("BigClass.java", big_class)]
        manifest = self.chunker.build_manifest(sources)
        oversized_tokens = _estimate_tokens(big_class)
        assert oversized_tokens > MAX_CHUNK_TOKENS, "Test class must exceed token limit"
        for chunk in manifest.chunks:
            assert chunk.token_estimate <= MAX_CHUNK_TOKENS + 100

    def test_empty_sources(self):
        manifest = self.chunker.build_manifest([], mod_id="empty")
        assert manifest.total_chunks == 0
        assert manifest.chunks == []

    def test_topological_order_dep_before_dependent(self):
        base_class = """\
package com.example;
public class BaseItem extends net.minecraft.world.item.Item {}
"""
        derived_class = """\
package com.example;
import com.example.BaseItem;
public class DerivedItem extends BaseItem {}
"""
        sources = [
            ("DerivedItem.java", derived_class),
            ("BaseItem.java", base_class),
        ]
        manifest = self.chunker.build_manifest(sources)
        names = [c.class_name for c in manifest.chunks]
        if "BaseItem" in names and "DerivedItem" in names:
            assert names.index("BaseItem") < names.index("DerivedItem")

    def test_manifest_fields(self):
        sources = [("Foo.java", "public class Foo {}")]
        manifest = self.chunker.build_manifest(
            sources, mod_id="m", mod_name="M", loader="fabric", loader_version="1.20.1"
        )
        assert manifest.loader == "fabric"
        assert manifest.loader_version == "1.20.1"

    def test_context_header_contains_loader(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(sources, loader="forge", loader_version="1.20.1")
        for chunk in manifest.chunks:
            assert "forge" in chunk.context_header

    def test_context_header_contains_component_type(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        for chunk in manifest.chunks:
            assert chunk.component_type in chunk.context_header

    def test_build_manifest_from_jar(self, tmp_path):
        jar_bytes = _make_jar(
            {
                "com/example/MySword.java": SIMPLE_ITEM_CLASS,
                "com/example/MyOreBlock.java": SIMPLE_BLOCK_CLASS,
            }
        )
        jar_path = tmp_path / "test_mod.jar"
        jar_path.write_bytes(jar_bytes)

        manifest = self.chunker.build_manifest_from_jar(
            str(jar_path), mod_id="testmod", mod_name="TestMod", loader="forge"
        )
        assert manifest.total_chunks >= 2

    def test_build_manifest_from_nonexistent_jar(self):
        manifest = self.chunker.build_manifest_from_jar("/nonexistent/path/mod.jar")
        assert manifest.total_chunks == 0

    def test_chunk_content_not_empty(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        for chunk in manifest.chunks:
            assert chunk.content.strip() != ""

    def test_chunk_line_numbers_valid(self):
        sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
        manifest = self.chunker.build_manifest(sources)
        for chunk in manifest.chunks:
            assert chunk.start_line >= 0
            assert chunk.end_line >= chunk.start_line

    def test_regex_fallback_no_tree_sitter(self):
        with patch("agents.java_semantic_chunker.TREE_SITTER_AVAILABLE", False):
            chunker = JavaSemanticChunker()
            sources = [("MySword.java", SIMPLE_ITEM_CLASS)]
            manifest = chunker.build_manifest(sources)
            assert manifest.total_chunks >= 1


class TestJavaAnalyzerAgentIntegration:
    """Integration: JavaAnalyzerAgent.generate_chunk_manifest() delegates to chunker."""

    def test_generate_chunk_manifest_method_exists(self):
        from agents.java_analyzer import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()
        assert hasattr(agent, "generate_chunk_manifest")
        assert callable(agent.generate_chunk_manifest)

    def test_generate_chunk_manifest_returns_manifest(self, tmp_path):
        from agents.java_analyzer import JavaAnalyzerAgent

        jar_bytes = _make_jar({"com/example/MySword.java": SIMPLE_ITEM_CLASS})
        jar_path = tmp_path / "mymod.jar"
        jar_path.write_bytes(jar_bytes)

        agent = JavaAnalyzerAgent()
        manifest = agent.generate_chunk_manifest(
            str(jar_path),
            mod_id="mymod",
            mod_name="MyMod",
            loader="forge",
            loader_version="1.20.1",
        )
        assert isinstance(manifest, ChunkManifest)
        assert manifest.total_chunks >= 1

    def test_generate_chunk_manifest_nonexistent_jar(self):
        from agents.java_analyzer import JavaAnalyzerAgent

        agent = JavaAnalyzerAgent()
        manifest = agent.generate_chunk_manifest("/no/such/file.jar")
        assert isinstance(manifest, ChunkManifest)
        assert manifest.total_chunks == 0
