from typing import Optional, Dict, Any, List
from aiocache import Cache
from .config import Config


class S3Cache:
    """
    Singleton async cache manager for S3 file existence,
    using compressed tree structure and path dictionary.

    Features:
    - Tree-based key storage using numeric path compression
    - Efficient deletion by prefix (subtree)
    - Works with SimpleMemoryCache (no Redis required)
    """

    _instance: Optional["S3Cache"] = None
    _tree_key = "__s3_tree_index__"
    _path_map_key = "__s3_path_map__"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.cache = Cache(Config().s3_cache)
            setattr(cls._instance, "_path_map", {})
            setattr(cls._instance, "_path_map_inv", {})
        return cls._instance

    async def set(self, path: str):
        """
        Adds a compressed path to the cache tree.
        """
        packed = await self._pack(path)
        tree = await self._get_tree()
        parts = packed.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = True
        await self._save_tree(tree)

    async def exists(self, path: str) -> bool:
        """
        Checks if a packed path exists in the cache tree.
        """
        packed = await self._pack(path)
        tree = await self._get_tree()
        print(tree)
        print(self._path_map)
        parts = packed.split("/")
        node = tree
        for part in parts:
            if part not in node:
                return False
            node = node[part]
        return node is True

    async def delete(self, path: str):
        """
        Deletes a single path from the tree.
        """
        packed = await self._pack(path)
        tree = await self._get_tree()
        parts = packed.split("/")
        if self._remove_from_tree(tree, parts):
            await self._save_tree(tree)

    async def delete_by_prefix(self, prefix: str):
        """
        Deletes an entire subtree by prefix.
        """
        packed = await self._pack(prefix)
        tree = await self._get_tree()
        parts = packed.split("/")
        if self._delete_subtree(tree, parts):
            await self._save_tree(tree)

    async def _get_tree(self) -> Dict[str, Any]:
        return await self.cache.get(self._tree_key) or {}

    async def _save_tree(self, tree: Dict[str, Any]):
        await self.cache.set(self._tree_key, tree)

    async def _load_path_map(self):
        self._path_map = await self.cache.get(self._path_map_key) or {}
        self._path_map_inv = {v: k for k, v in self._path_map.items()}

    async def _save_path_map(self):
        await self.cache.set(self._path_map_key, self._path_map)

    async def _pack(self, path: str) -> str:
        """
        Converts full path into a compressed path with numeric segments.
        Example: 'uploads/images/img.jpg' → '1/2/3'
        """
        if not self._path_map:
            await self._load_path_map()

        parts = path.strip("/").split("/")
        packed_parts = []
        updated = False

        for part in parts:
            if part not in self._path_map_inv:
                new_id = str(len(self._path_map) + 1)
                self._path_map[new_id] = part
                self._path_map_inv[part] = new_id
                updated = True
            packed_parts.append(self._path_map_inv[part])

        if updated:
            await self._save_path_map()

        return "/".join(packed_parts)

    def _remove_from_tree(self, node: Dict[str, Any], parts: List[str]) -> bool:
        if len(parts) == 1:
            return node.pop(parts[0], None) is not None
        if parts[0] in node and isinstance(node[parts[0]], dict):
            removed = self._remove_from_tree(node[parts[0]], parts[1:])
            if removed and not node[parts[0]]:
                node.pop(parts[0])
            return removed
        return False

    def _delete_subtree(self, node: Dict[str, Any], parts: List[str]) -> bool:
        if len(parts) == 1:
            return node.pop(parts[0], None) is not None
        if parts[0] in node and isinstance(node[parts[0]], dict):
            deleted = self._delete_subtree(node[parts[0]], parts[1:])
            if deleted and not node[parts[0]]:
                node.pop(parts[0])
            return deleted
        return False
