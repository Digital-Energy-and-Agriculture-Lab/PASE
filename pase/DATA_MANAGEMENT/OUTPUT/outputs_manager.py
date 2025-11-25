import datetime
import json
import hashlib
from pathlib import Path
from typing import Any, Optional


class OutputsManager:
    SUBDIRS = {
        "inputs": "1-inputs",
        "data": "2-data",
        "intermediate": "3-interm_results",
        "results": "4-results",
    }

    REGISTRY_FILE = "variants.json"
    LATEST_LINK = "latest"

    def __init__(self, location_name: str,
                 sim_start_year: int,
                 sim_end_year: int):
        self.root = self.set_pase_root()

        self.project = self.get_project_name(location_name,
                                             sim_start_year, sim_end_year)

        self.project_root = self.root / "OUTPUTS" / self.project
        self.project_root.mkdir(parents=True, exist_ok=True)

        # load registry
        self.registry_path = self.project_root / self.REGISTRY_FILE
        if self.registry_path.exists():
            self.registry = json.loads(self.registry_path.read_text())
        else:
            self.registry = {}

        self.variant_root: Optional[Path] = None
        self.variant: Optional[str] = None

    # ---------------------------------------------------------------------
    # Input hashing
    # ---------------------------------------------------------------------
    @staticmethod
    def _hash_inputs(inputs: dict) -> str:
        """Stable, deterministic JSON hashing."""
        payload = json.dumps(inputs, sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    # ---------------------------------------------------------------------
    # Variant discovery utilities
    # ---------------------------------------------------------------------
    def _discover_existing_variants(self):
        """Return dict: variant_name -> stored_input_hash."""
        variants = {}
        for vdir in self.project_root.iterdir():
            if vdir.is_dir():
                hash_file = vdir / self.SUBDIRS["inputs"] / "input_hash.txt"
                if hash_file.exists():
                    variants[vdir.name] = hash_file.read_text().strip()
        return variants

    def _find_or_create_variant_name(self, input_hash: str, user_variant: Optional[str]):
        """
        Variant selection logic:
            1) If user provided variant → use it.
            2) Else if hash exists → reuse corresponding variant.
            3) Else → create new variant_XX.
        """
        # User override always wins
        if user_variant:
            return user_variant

        variants = self._discover_existing_variants()

        # Check for identical hash
        for variant_name, saved_hash in variants.items():
            if saved_hash == input_hash:
                return variant_name

        # New hash → create next incremented variant name
        idx = len(variants) + 1
        return f"variant_{idx:02d}"

      # ---------------------------------------------------------------------
    # Registry update
    # ---------------------------------------------------------------------
    def _update_registry(self, variant_name: str, input_hash: str):
        now = datetime.datetime.now().isoformat()

        self.registry[variant_name] = {
            "hash": input_hash,
            "timestamp": now,
        }

        self.registry_path.write_text(json.dumps(self.registry, indent=2))

    # ---------------------------------------------------------------------
    # Latest symlink update
    # ---------------------------------------------------------------------
    def _update_symlink(self, variant_name: str):
        target = self.project_root / variant_name
        link_path = self.project_root / self.LATEST_LINK

        # Remove existing link or folder
        if link_path.exists() or link_path.is_symlink():
            if link_path.is_dir() and not link_path.is_symlink():
                # Windows fallback: ordinary directory → remove
                for p in link_path.iterdir():
                    p.unlink()  # safe: registry never writes here
                link_path.rmdir()
            else:
                link_path.unlink()

        try:
            # Try creating a symlink
            link_path.symlink_to(target, target_is_directory=True)
        except OSError:
            # Windows fallback: create folder containing a text pointer
            link_path.mkdir()
            (link_path / "TARGET.txt").write_text(str(target))

    # ---------------------------------------------------------------------
    # Variant setup (hash must be computed before creating dirs)
    # ---------------------------------------------------------------------
    def setup_variant(self, inputs: dict, variant: Optional[str] = None):
        """
        Compute input-hash *before* touching disk.
        Then pick correct variant (reuse or new).
        Then create folders *only if needed*.
        """
        # 1) Compute hash early, before any disk modifications.
        input_hash = self._hash_inputs(inputs)

        # 2) Determine variant name based on hash existence.
        chosen_variant = self._find_or_create_variant_name(input_hash, variant)
        self.variant = chosen_variant
        self.variant_root = self.project_root / chosen_variant

        # 3) Only create directories if they do not already exist.
        for sub in self.SUBDIRS.values():
            (self.variant_root / sub).mkdir(parents=True, exist_ok=True)

        # 4) Write input hash (ensures reproducibility)
        hash_file = self.variant_root / self.SUBDIRS["inputs"] / "input_hash.txt"
        hash_file.write_text(input_hash)

        # 5) Write full input JSON
        inputs_file = self.variant_root / self.SUBDIRS["inputs"] / "inputs.json"
        inputs_file.write_text(json.dumps(inputs, indent=2))

        # update registry
        self._update_registry(chosen_variant, input_hash)

        # update latest symlink
        self._update_symlink(chosen_variant)

        return self.variant_root

    # ---------------------------------------------------------------------
    # Path resolution helpers
    # ---------------------------------------------------------------------
    def _path(self, sub: str, filename: str) -> Path:
        return (self.variant_root / self.SUBDIRS[sub] / filename).resolve()

    def set_pase_root(self):
        local_dir = Path(__file__)
        return local_dir.parents[3]

    def get_project_name(self, location_name, sim_start_year, sim_end_year):
        return (location_name
                + '_' + str(sim_start_year)
                + '-' + str(sim_end_year))


    # ---------------------------------------------------------------------
    # Persistence API
    # ---------------------------------------------------------------------
    def save_json(self, sub: str, name: str, data: Any):
        self._path(sub, name).write_text(json.dumps(data, indent=2))

    def load_json(self, sub: str, name: str, default=None):
        path = self._path(sub, name)
        return json.loads(path.read_text()) if path.exists() else default

    def save_bytes(self, sub: str, name: str, blob: bytes):
        self._path(sub, name).write_bytes(blob)

    def load_bytes(self, sub: str, name: str, default=None):
        path = self._path(sub, name)
        return path.read_bytes() if path.exists() else default

    # ---------------------------------------------------------------------
    # Caching example for external data
    # ---------------------------------------------------------------------
    def load_or_fetch_weather(self, key: str, fetch_fn):
        """
        Load or cache weather data from PVGIS API.
        key = "lat_lon_year_resolution" or similar.
        """
        fname = f"{key}.json"
        cached = self.load_json("data", fname)
        if cached is not None:
            return cached

        data = fetch_fn()
        self.save_json("data", fname, data)
        return data
