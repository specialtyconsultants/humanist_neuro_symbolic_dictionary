"""Importing this package registers all domain packs via their @register decorators."""
from importlib import import_module
for _name in ("patient_advocacy", "gov_procurement", "agri_microfinance"):
    import_module(f"domains.{_name}.domain")
