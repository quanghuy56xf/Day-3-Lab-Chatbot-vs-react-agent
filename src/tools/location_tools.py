"""
Location & Amenity Tool - Thông tin tiện ích xung quanh.
Cung cấp dữ liệu về trường học, bệnh viện, siêu thị, 
công viên, và giao thông gần Vinhomes Ocean Park 1.
"""


# Pre-built amenity database for Vinhomes Ocean Park 1
AMENITIES_DB = {
    "education": {
        "category_name": "🎓 Giáo dục",
        "items": [
            {"name": "Vinschool Ocean Park", "type": "Liên cấp (MN-TH-THCS-THPT)", "distance": "Nội khu", "note": "Hệ thống Vinschool chuẩn quốc tế"},
            {"name": "VinUni (Đại học VinUni)", "type": "Đại học quốc tế", "distance": "2 km", "note": "Đại học tư thục hàng đầu Việt Nam"},
            {"name": "Trường MN Vinschool", "type": "Mầm non", "distance": "Nội khu", "note": "Nhiều cơ sở trong khu đô thị"},
            {"name": "BIS Hà Nội (British International School)", "type": "Quốc tế", "distance": "15 km", "note": "Trường quốc tế Anh"},
        ]
    },
    "healthcare": {
        "category_name": "🏥 Y tế",
        "items": [
            {"name": "Vinmec Ocean Park", "type": "Bệnh viện đa khoa quốc tế", "distance": "Nội khu", "note": "Đầy đủ chuyên khoa, cấp cứu 24/7"},
            {"name": "Bệnh viện Đa khoa Gia Lâm", "type": "Bệnh viện công", "distance": "5 km", "note": "Bệnh viện huyện"},
            {"name": "Phòng khám VinMec", "type": "Phòng khám", "distance": "Nội khu", "note": "Khám ngoại trú, nhi khoa"},
        ]
    },
    "shopping": {
        "category_name": "🛒 Mua sắm",
        "items": [
            {"name": "Vincom Mega Mall Ocean Park", "type": "TTTM lớn", "distance": "Nội khu", "note": "CGV, nhà hàng, thời trang, siêu thị"},
            {"name": "VinMart / WinMart", "type": "Siêu thị tiện lợi", "distance": "Nội khu", "note": "Nhiều điểm trong khu đô thị"},
            {"name": "AEON Mall Long Biên", "type": "TTTM", "distance": "12 km", "note": "Trung tâm mua sắm Nhật Bản"},
        ]
    },
    "recreation": {
        "category_name": "🎡 Giải trí & Thể thao",
        "items": [
            {"name": "VinWonders Water Park", "type": "Công viên nước", "distance": "Nội khu", "note": "Công viên nước lớn nhất Hà Nội"},
            {"name": "Hồ nước mặn nhân tạo", "type": "Bãi biển nhân tạo", "distance": "Nội khu", "note": "24.5 ha, bãi cát trắng"},
            {"name": "Quảng trường Grand Park", "type": "Công viên", "distance": "Nội khu", "note": "Công viên trung tâm 36 ha"},
            {"name": "Sân golf Vinpearl", "type": "Sân golf", "distance": "Nội khu", "note": "Sân golf 18 hố chuẩn quốc tế"},
            {"name": "Gym & Bể bơi Vinhomes", "type": "CSVC thể thao", "distance": "Nội khu", "note": "Phòng gym, bể bơi, sân tennis"},
        ]
    },
    "transport": {
        "category_name": "🚗 Giao thông",
        "items": [
            {"name": "Cao tốc Hà Nội - Hải Phòng", "type": "Cao tốc", "distance": "1 km", "note": "Kết nối nhanh tới sân bay Cát Bi, Hải Phòng"},
            {"name": "Quốc lộ 5", "type": "Quốc lộ", "distance": "2 km", "note": "Trục giao thông chính Hà Nội - Hải Dương"},
            {"name": "Sân bay Nội Bài", "type": "Sân bay quốc tế", "distance": "35 km", "note": "~45 phút qua cầu Nhật Tân"},
            {"name": "Ga Hà Nội (trung tâm)", "type": "Trung tâm TP", "distance": "20 km", "note": "~30-40 phút qua cao tốc"},
            {"name": "Xe bus nội khu", "type": "Xe bus", "distance": "Nội khu", "note": "Tuyến bus miễn phí trong khu đô thị"},
        ]
    },
    "project_info": {
        "category_name": "🏢 Thông tin phân khu",
        "items": [
            {"name": "The London", "type": "Masteri Waterfront", "distance": "—", "note": "Phân khúc cao cấp, view hồ, bàn giao 2024"},
            {"name": "The Paris", "type": "Masteri Waterfront", "distance": "—", "note": "Phân khúc cao cấp, kiến trúc Pháp"},
            {"name": "The Zurich", "type": "Masteri Waterfront", "distance": "—", "note": "Phân khúc mới nhất, bàn giao 2025-2026"},
            {"name": "The Beverly", "type": "Grand Park", "distance": "—", "note": "Phân khu biệt thự, townhouse, shophouse"},
        ]
    },
}


def search_amenities(category: str = "", keyword: str = "") -> str:
    """
    Tìm kiếm tiện ích xung quanh Vinhomes Ocean Park 1.
    
    Args:
        category: Loại tiện ích. Một trong: 
            'education' (giáo dục/trường học), 
            'healthcare' (y tế/bệnh viện), 
            'shopping' (mua sắm/siêu thị), 
            'recreation' (giải trí/thể thao/công viên), 
            'transport' (giao thông/đi lại),
            'project_info' (thông tin phân khu).
            Để trống để xem tất cả.
        keyword: Từ khóa tìm kiếm (ví dụ: 'trường', 'bệnh viện', 'golf').
    
    Returns:
        Danh sách tiện ích phù hợp.
    """
    category = category.strip().lower() if category else ""
    keyword = keyword.strip().lower() if keyword else ""
    
    # Map Vietnamese keywords to categories
    category_aliases = {
        "giáo dục": "education", "trường": "education", "trường học": "education",
        "học": "education", "vinschool": "education", "đại học": "education",
        "y tế": "healthcare", "bệnh viện": "healthcare", "khám": "healthcare",
        "sức khỏe": "healthcare", "vinmec": "healthcare",
        "mua sắm": "shopping", "siêu thị": "shopping", "chợ": "shopping",
        "vincom": "shopping", "aeon": "shopping",
        "giải trí": "recreation", "thể thao": "recreation", "công viên": "recreation",
        "bể bơi": "recreation", "gym": "recreation", "golf": "recreation",
        "giao thông": "transport", "đi lại": "transport", "xe bus": "transport",
        "cao tốc": "transport", "sân bay": "transport",
        "phân khu": "project_info", "dự án": "project_info",
    }
    
    # Resolve category
    if category in category_aliases:
        category = category_aliases[category]
    
    # Determine which categories to search
    if category and category in AMENITIES_DB:
        categories_to_search = {category: AMENITIES_DB[category]}
    elif category:
        # Try to find by alias in keyword
        for alias, cat_key in category_aliases.items():
            if category in alias or alias in category:
                categories_to_search = {cat_key: AMENITIES_DB[cat_key]}
                break
        else:
            categories_to_search = AMENITIES_DB
    else:
        categories_to_search = AMENITIES_DB
    
    # Search and filter
    results = []
    for cat_key, cat_data in categories_to_search.items():
        matching_items = []
        for item in cat_data["items"]:
            if keyword:
                searchable = f"{item['name']} {item['type']} {item['note']}".lower()
                if keyword not in searchable:
                    continue
            matching_items.append(item)
        
        if matching_items:
            results.append((cat_data["category_name"], matching_items))
    
    if not results:
        return f"Không tìm thấy tiện ích phù hợp với tiêu chí: category='{category}', keyword='{keyword}'"
    
    # Format output
    output = [f"=== TIỆN ÍCH XUNG QUANH VINHOMES OCEAN PARK 1 ===", ""]
    
    for cat_name, items in results:
        output.append(f"--- {cat_name} ---")
        for item in items:
            output.append(f"* Tên: {item['name']}")
            output.append(f"  Loại: {item['type']} | Khoảng cách: {item['distance']}")
            output.append(f"  Ghi chú: {item['note']}")
            output.append("")
    
    total_items = sum(len(items) for _, items in results)
    output.append(f"Tổng: {total_items} tiện ích tìm thấy.")
    
    return "\n".join(output)


# --- Tool Registry ---
TOOLS = [
    {
        "name": "search_amenities",
        "description": (
            "Tìm kiếm tiện ích xung quanh Vinhomes Ocean Park 1. "
            "Tham số: category (loại tiện ích: 'education', 'healthcare', 'shopping', "
            "'recreation', 'transport', 'project_info'), "
            "keyword (từ khóa tìm kiếm, ví dụ 'trường', 'bệnh viện', 'golf'). "
            "Sử dụng khi khách hàng hỏi về tiện ích xung quanh, trường học, "
            "bệnh viện, siêu thị, giao thông, công viên gần khu đô thị."
        ),
        "function": search_amenities,
    },
]
