import yaml
from pathlib import Path


def test_standard_template_exists():
    template_path = Path("config/templates/generation/standard.yaml")
    assert template_path.exists(), "standard.yaml must exist"


def test_standard_template_has_required_keys():
    template_path = Path("config/templates/generation/standard.yaml")
    with open(template_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "name" in data
    assert "system_prompt" in data
    assert "output_schema" in data
    assert data["name"] == "standard"


def test_standard_template_system_prompt_non_empty():
    template_path = Path("config/templates/generation/standard.yaml")
    with open(template_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert len(data["system_prompt"].strip()) > 50
