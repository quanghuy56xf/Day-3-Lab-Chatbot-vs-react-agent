"""
Real Estate Tools for the ReAct Agent.
Provides search, detail lookup, and market statistics for Vinhomes Ocean Park properties.
"""
import json
import os
from typing import Dict, Any, List, Optional

# Path to the database file
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "database.json")

_cached_data: Optional[List[Dict[str, Any]]] = None

def _load_data() -> List[Dict[str, Any]]:
    """Load and cache property data from database.json (JSONL format)."""
    global _cached_data
    if _cached_data is not None:
        return _cached_data
    
    properties = []
    with open(DATABASE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                source = record.get("_source", {})
                properties.append(source)
            except json.JSONDecodeError:
                continue
    
    _cached_data = properties
    return properties


def _normalize(text: str) -> str:
    """Normalize text for case-insensitive matching."""
    if not text:
        return ""
    return text.strip().lower()


def _format_price(price: float) -> str:
    """Format price in VND to human-readable string (tỷ/triệu)."""
    if price >= 1_000_000_000:
        billions = price / 1_000_000_000
        return f"{billions:.2f} tỷ"
    elif price >= 1_000_000:
        millions = price / 1_000_000
        return f"{millions:.0f} triệu"
    return f"{price:,.0f} VNĐ"


def search_properties(
    project: str = "",
    property_type: str = "",
    min_price: float = 0,
    max_price: float = 0,
    direction: str = "",
    status: str = "",
    floor_range: str = "",
    limit: int = 10
) -> str:
    """
    Search for properties matching the given criteria.
    
    Args:
        project: Project name (e.g., "The London", "The Paris", "The Zurich", "The Beverly")
        property_type: Apartment type (e.g., "STUDIO", "1PN", "1PN+", "2PN", "2PN+", "3PN")
        min_price: Minimum price in VND (e.g., 2000000000 for 2 billion)
        max_price: Maximum price in VND (e.g., 5000000000 for 5 billion)
        direction: Direction/orientation (e.g., "Tây Nam", "Đông Bắc", "Tây Bắc", "Đông Nam")
        status: Listing status filter (e.g., "Còn bán" or "Đã bán"). Leave empty for all.
        floor_range: Floor level (e.g., "Thấp", "Trung", "Cao")
        limit: Maximum number of results to return (default 10)
    
    Returns:
        A formatted string with the search results.
    """
    data = _load_data()
    results = []
    
    for prop in data:
        # Filter by project
        if project and _normalize(project) not in _normalize(prop.get("project", "")):
            continue
        
        # Filter by type
        if property_type and _normalize(property_type) != _normalize(prop.get("type", "")):
            continue
        
        # Filter by price range
        prop_price = prop.get("price", 0)
        if prop_price <= 0:
            continue
        if min_price and prop_price < min_price:
            continue
        if max_price and prop_price > max_price:
            continue
        
        # Filter by direction
        if direction and _normalize(direction) not in _normalize(prop.get("direction", "")):
            continue
        
        # Filter by status
        if status:
            prop_status = _normalize(prop.get("status", ""))
            status_norm = _normalize(status)
            # "Còn bán" matches anything that is NOT "Đã bán" and NOT "Tạm dừng bán"
            if status_norm in ["còn bán", "đang bán", "available"]:
                if "đã bán" in prop_status or "tạm dừng" in prop_status:
                    continue
            elif status_norm not in prop_status:
                continue
        
        # Filter by floor range
        if floor_range and _normalize(floor_range) not in _normalize(prop.get("floorRange", "")):
            continue
        
        results.append(prop)
    
    if not results:
        return "Không tìm thấy căn hộ nào phù hợp với tiêu chí tìm kiếm."
    
    # Sort by price ascending
    results.sort(key=lambda x: x.get("price", 0))
    
    # Limit results
    total_found = len(results)
    results = results[:limit]
    
    # Format output
    output_lines = [f"Tìm thấy {total_found} căn hộ phù hợp (hiển thị {len(results)} kết quả):"]
    output_lines.append("-" * 60)
    
    for i, prop in enumerate(results, 1):
        price_per_m2 = prop.get("price", 0) / prop.get("area", 1) if prop.get("area", 0) > 0 else 0
        output_lines.append(
            f"{i}. [{prop.get('id', 'N/A')}] {prop.get('title', 'N/A')}\n"
            f"   Mã căn: {prop.get('code', 'N/A')} | Dự án: {prop.get('project', 'N/A')}\n"
            f"   Loại: {prop.get('type', 'N/A')} | Diện tích: {prop.get('area', 'N/A')}m²\n"
            f"   Giá: {_format_price(prop.get('price', 0))} ({_format_price(price_per_m2)}/m²)\n"
            f"   Tầng: {prop.get('floorRange', 'N/A')} | Hướng: {prop.get('direction', 'N/A')}\n"
            f"   Trạng thái: {prop.get('status', 'N/A')}"
        )
    
    return "\n".join(output_lines)


def get_property_details(property_id: str) -> str:
    """
    Get full details of a specific property by its ID.
    
    Args:
        property_id: The unique property ID (e.g., "5PDVUJ", "TNN6YV")
    
    Returns:
        A formatted string with all property details including owner contact.
    """
    data = _load_data()
    
    for prop in data:
        if prop.get("id", "") == property_id or prop.get("code", "") == property_id:
            price_per_m2 = prop.get("price", 0) / prop.get("area", 1) if prop.get("area", 0) > 0 else 0
            
            details = [
                f"=== CHI TIẾT CĂN HỘ ===",
                f"ID: {prop.get('id', 'N/A')}",
                f"Tiêu đề: {prop.get('title', 'N/A')}",
                f"Mã căn: {prop.get('code', 'N/A')}",
                f"Mã kiểm tra: {prop.get('checkCode', 'N/A')}",
                f"Dự án: {prop.get('project', 'N/A')}",
                f"Tòa nhà: {prop.get('buildingBlock', 'N/A')}",
                f"",
                f"--- Thông tin căn hộ ---",
                f"Loại: {prop.get('type', 'N/A')}",
                f"Diện tích: {prop.get('area', 'N/A')}m²",
                f"Tầng: {prop.get('floorRange', 'N/A')}",
                f"Hướng: {prop.get('direction', 'N/A')}",
                f"Nội thất: {prop.get('furniture', 'N/A')}",
                f"",
                f"--- Thông tin giá ---",
                f"Giá bán: {_format_price(prop.get('price', 0))}",
                f"Giá/m²: {_format_price(price_per_m2)}/m²",
                f"Phí môi giới: {_format_price(prop.get('brokerFee', 0))}",
                f"Phân loại giá: {prop.get('priceClassification', 'N/A')}",
                f"",
                f"--- Pháp lý & Thanh toán ---",
                f"Pháp lý: {prop.get('legalStatus', 'N/A')}",
                f"Thanh toán: {prop.get('paymentStatus', 'N/A')}",
                f"Trạng thái: {prop.get('status', 'N/A')}",
                f"",
                f"--- Liên hệ chủ nhà ---",
                f"Chủ nhà: {prop.get('owner', 'N/A')}",
                f"SĐT: {prop.get('ownerPhone', 'N/A')}",
                f"Xem nhà: {prop.get('viewing', 'N/A')}",
                f"",
                f"Địa chỉ: {prop.get('address', prop.get('ward', 'N/A') + ', ' + prop.get('city', 'N/A'))}",
            ]
            
            if prop.get("note"):
                details.append(f"Ghi chú: {prop.get('note')}")
            
            return "\n".join(details)
    
    return f"Không tìm thấy căn hộ với ID: {property_id}"


def calculate_market_stats(project: str = "", property_type: str = "") -> str:
    """
    Calculate market statistics (average price, area, price/m²) for a project and type.
    
    Args:
        project: Project name (e.g., "The London", "The Paris", "The Zurich", "The Beverly"). 
                 Leave empty for all projects.
        property_type: Apartment type (e.g., "STUDIO", "1PN", "2PN", "3PN").
                       Leave empty for all types.
    
    Returns:
        A formatted string with market statistics.
    """
    data = _load_data()
    filtered = []
    
    for prop in data:
        if project and _normalize(project) not in _normalize(prop.get("project", "")):
            continue
        if property_type and _normalize(property_type) != _normalize(prop.get("type", "")):
            continue
        filtered.append(prop)
    
    if not filtered:
        return f"Không có dữ liệu cho dự án '{project}' loại '{property_type}'."
    
    prices = [p.get("price", 0) for p in filtered if p.get("price", 0) > 0]
    areas = [p.get("area", 0) for p in filtered if p.get("area", 0) > 0]
    price_per_m2 = [p.get("price", 0) / p.get("area", 1) for p in filtered 
                     if p.get("price", 0) > 0 and p.get("area", 0) > 0]
    
    # Count by status
    status_counts = {}
    for p in filtered:
        s = p.get("status", "Không rõ").strip()
        status_counts[s] = status_counts.get(s, 0) + 1
    
    # Count by floor range
    floor_counts = {}
    for p in filtered:
        fl = p.get("floorRange", "Không rõ").strip()
        floor_counts[fl] = floor_counts.get(fl, 0) + 1
    
    avg_price = sum(prices) / len(prices) if prices else 0
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    avg_area = sum(areas) / len(areas) if areas else 0
    avg_ppm2 = sum(price_per_m2) / len(price_per_m2) if price_per_m2 else 0
    
    label_project = project if project else "Tất cả dự án"
    label_type = property_type if property_type else "Tất cả loại"
    
    output = [
        f"=== THỐNG KÊ THỊ TRƯỜNG ===",
        f"Dự án: {label_project} | Loại căn: {label_type}",
        f"Tổng số căn: {len(filtered)}",
        f"",
        f"--- Giá bán ---",
        f"Giá trung bình: {_format_price(avg_price)}",
        f"Giá thấp nhất: {_format_price(min_price)}",
        f"Giá cao nhất: {_format_price(max_price)}",
        f"",
        f"--- Diện tích ---",
        f"Diện tích trung bình: {avg_area:.1f}m²",
        f"Giá trung bình/m²: {_format_price(avg_ppm2)}/m²",
        f"",
        f"--- Phân bổ trạng thái ---",
    ]
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        output.append(f"  {status}: {count} căn")
    
    output.append(f"")
    output.append(f"--- Phân bổ tầng ---")
    for floor, count in sorted(floor_counts.items(), key=lambda x: -x[1]):
        output.append(f"  {floor}: {count} căn")
    
    return "\n".join(output)


# --- Tool Registry for the Agent ---
TOOLS = [
    {
        "name": "search_properties",
        "description": (
            "Tìm kiếm căn hộ theo tiêu chí. "
            "Tham số: project (tên dự án: 'The London', 'The Paris', 'The Zurich', 'The Beverly'), "
            "property_type (loại căn: 'STUDIO', '1PN', '1PN+', '2PN', '2PN+', '3PN'), "
            "min_price (giá tối thiểu bằng VND, ví dụ 2000000000), "
            "max_price (giá tối đa bằng VND, ví dụ 5000000000), "
            "direction (hướng: 'Tây Nam', 'Đông Bắc', 'Tây Bắc', 'Đông Nam', 'ĐN-TN', 'TB-ĐB'), "
            "status (trạng thái: 'Còn bán', 'Đã bán', 'Tạm dừng bán'), "
            "floor_range (tầng: 'Thấp', 'Trung', 'Cao'), "
            "limit (số kết quả tối đa, mặc định 10). "
            "Tất cả tham số đều là tùy chọn."
        ),
        "function": search_properties
    },
    {
        "name": "get_property_details",
        "description": (
            "Xem chi tiết đầy đủ một căn hộ cụ thể bao gồm thông tin liên hệ chủ nhà. "
            "Tham số: property_id (ID căn hộ, ví dụ '5PDVUJ' hoặc mã căn 'LD11801')."
        ),
        "function": get_property_details
    },
    {
        "name": "calculate_market_stats",
        "description": (
            "Tính toán thống kê thị trường (giá trung bình, diện tích trung bình, giá/m²) "
            "cho một dự án và loại căn hộ cụ thể. "
            "Tham số: project (tên dự án, để trống nếu muốn xem tất cả), "
            "property_type (loại căn hộ, để trống nếu muốn xem tất cả)."
        ),
        "function": calculate_market_stats
    }
]
