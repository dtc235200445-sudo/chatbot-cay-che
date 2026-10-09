import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Danh mục vùng chè nằm trong data/tea_regions.json (dữ liệu do dự án xây dựng, có ghi chú nguồn tọa độ)
REGIONS_FILE = Path(__file__).resolve().parents[2] / "data" / "tea_regions.json"


@dataclass(frozen=True)
class TeaRegion:
    name: str  # Tên hiển thị
    province: str
    latitude: float
    longitude: float
    is_tea_region: bool = True
    area_ha: Optional[float] = None
    altitude_m: Optional[float] = None
    note: str = ""


def load_regions(path: Path = REGIONS_FILE) -> Dict[str, TeaRegion]:
    """Đọc danh mục vùng chè; khóa là tên vùng viết thường."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    regions: Dict[str, TeaRegion] = {}
    for item in raw["regions"]:
        region = TeaRegion(
            name=item["name"],
            province=item["province"],
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            is_tea_region=bool(item.get("is_tea_region", True)),
            area_ha=item.get("area_ha"),
            altitude_m=item.get("altitude_m"),
            note=item.get("note", ""),
        )
        regions[region.name.lower()] = region
    return regions


# Khóa là tên vùng viết thường, dùng để nhận diện trong câu hỏi và tra tọa độ thời tiết.
TEA_REGIONS: Dict[str, TeaRegion] = load_regions()

DEFAULT_REGION = "Thái Nguyên"


def list_regions() -> List[TeaRegion]:
    return [r for r in TEA_REGIONS.values() if r.is_tea_region]


def find_region_in_text(text: str) -> Optional[str]:
    """Trả về tên hiển thị của vùng chè đầu tiên xuất hiện trong văn bản, hoặc None."""
    lowered = text.lower()
    best: Optional[Tuple[int, str]] = None
    for key, region in TEA_REGIONS.items():
        pos = lowered.find(key)
        if pos != -1 and (best is None or pos < best[0]):
            best = (pos, region.name)
    return best[1] if best else None


def resolve_coordinates(region_name: str) -> Optional[Tuple[float, float]]:
    """Tra tọa độ theo tên vùng (khớp chính xác, sau đó khớp một phần)."""
    key = region_name.strip().lower()
    if key in TEA_REGIONS:
        r = TEA_REGIONS[key]
        return r.latitude, r.longitude
    for region_key, r in TEA_REGIONS.items():
        if region_key in key or key in region_key:
            return r.latitude, r.longitude
    return None
