import datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

from pase.DATA_MANAGEMENT.benchmarking import save_simulation_metadata
from pase.user_support_tools import PASE_Logger


class OutputsManager:
    SUBDIRS = {
        "inputs": "1-inputs",
        "data": "2-data",
        "intermediate": "3-interm_results",
        "results": "4-results",
    }

    CACHE_DIR = Path(__file__).parents[3] / 'OUTPUTS' / '_cache'
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
    # Variant setup (hash must be computed before creating dirs)
    # ---------------------------------------------------------------------
    def setup_variant(self,
                      loc: dict,
                      av: dict,
                      pv_module: dict,
                      structure: dict,
                      crop_config: dict,
                      variant: Optional[str] = None,
                      source: Optional[str] = None,
                      ):
        """
        Compute input-hash *before* touching disk.
        Then pick correct variant (reuse or new).
        Then create folders *only if needed*.
        """
        # 0) Parse the source to get only the file name
        source_file = Path(source).parts[-1]

        # 1) Compute hash early, before any disk modifications.
        inputs = {**loc, **av, **pv_module, **structure, **crop_config,
                  'source': source_file}
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

        # 5) Save simulation metadata
        metadata_file = self.variant_root / self.SUBDIRS["inputs"] / "simulation_metadata.yaml"
        save_simulation_metadata(loc=loc, av=av, pv_module=pv_module,
                                 structure=structure, crop_config=crop_config,
                                 source=source_file, output_path=metadata_file)

        # update registry
        self._update_registry(chosen_variant, input_hash)

        return self.variant_root

    # ---------------------------------------------------------------------
    # Path resolution helpers
    # ---------------------------------------------------------------------
    def _path(self, sub: str, filename: str) -> Path:
        return (self.variant_root / self.SUBDIRS[sub] / filename).resolve()

    def _cache_path(self, filename: str) -> Path:
        return (self.CACHE_DIR / filename).resolve()

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
        if path.exists():
            return json.loads(path.read_text())
        else:
            return default

    def save_json_to_cache(self, name: str, data: Any):
        self._cache_path(name).write_text(json.dumps(data, indent=2))

    def load_json_from_cache(self, name: str, default=None):
        path = self._cache_path(name)
        if path.exists():
            return json.loads(path.read_text())
        else:
            return default
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
        fname = f"wd_{key}.json"
        cached = self.load_json_from_cache(fname)
        if cached is not None:
            PASE_Logger('Found cached weather data ; '
                        'loading from cached json file.',
                        level='INFO')

            # Save to <project>/<variant> for traceability
            self.save_json("data", fname, cached)

            return cached  # cached is a dict

        PASE_Logger('No cached data, fetching from PVGIS API ...',
                    level='INFO')

        data = fetch_fn()  # fetch data with the passthrough function fetch_fn

        # Save to <project>/<variant> for traceability
        self.save_json("data", fname, data)

        # Save to cache for efficiency
        self.save_json_to_cache(fname, data)

        return data
