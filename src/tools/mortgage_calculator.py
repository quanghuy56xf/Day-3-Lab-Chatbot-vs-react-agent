"""
Mortgage Calculator Tool - Tính toán vay mua nhà.
Giúp khách hàng ước lượng chi phí trả góp hàng tháng,
tổng lãi phải trả, và lịch trả nợ.
"""


def calculate_mortgage(
    property_price: float = 0,
    down_payment_percent: float = 30,
    loan_term_years: int = 20,
    annual_interest_rate: float = 8.0,
) -> str:
    """
    Tính toán khoản vay mua nhà trả góp.
    
    Args:
        property_price: Giá căn hộ (VND), ví dụ 5000000000 (5 tỷ).
        down_payment_percent: Phần trăm trả trước (%), mặc định 30%.
        loan_term_years: Thời hạn vay (năm), mặc định 20 năm.
        annual_interest_rate: Lãi suất năm (%), mặc định 8%.
    
    Returns:
        Bảng tính chi tiết khoản vay.
    """
    if property_price <= 0:
        return "Lỗi: Vui lòng cung cấp giá căn hộ (VND). Ví dụ: 5000000000 cho căn 5 tỷ."
    
    # Validate inputs
    down_payment_percent = max(0, min(100, down_payment_percent))
    loan_term_years = max(1, min(35, loan_term_years))
    annual_interest_rate = max(0.1, min(20, annual_interest_rate))
    
    # Calculate
    down_payment = property_price * (down_payment_percent / 100)
    loan_amount = property_price - down_payment
    
    if loan_amount <= 0:
        return f"Với mức trả trước {down_payment_percent}%, bạn đã thanh toán toàn bộ căn hộ. Không cần vay."
    
    monthly_rate = annual_interest_rate / 100 / 12
    total_months = loan_term_years * 12
    
    # Monthly payment formula (PMT)
    if monthly_rate > 0:
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** total_months) / \
                          ((1 + monthly_rate) ** total_months - 1)
    else:
        monthly_payment = loan_amount / total_months
    
    total_payment = monthly_payment * total_months
    total_interest = total_payment - loan_amount
    
    # Format helpers
    def fmt(n):
        if n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.2f} tỷ"
        elif n >= 1_000_000:
            return f"{n / 1_000_000:.1f} triệu"
        else:
            return f"{n:,.0f}"
    
    # Payment schedule for first 3 years
    schedule_lines = []
    balance = loan_amount
    for year in range(1, min(4, loan_term_years + 1)):
        interest_year = 0
        principal_year = 0
        for m in range(12):
            interest_month = balance * monthly_rate
            principal_month = monthly_payment - interest_month
            interest_year += interest_month
            principal_year += principal_month
            balance -= principal_month
        schedule_lines.append(
            f"  Năm {year}: Gốc {fmt(principal_year)} | Lãi {fmt(interest_year)} | Dư nợ {fmt(max(0, balance))}"
        )
    
    output = [
        f"=== BẢNG TÍNH VAY MUA NHÀ ===",
        f"",
        f"--- Thông tin căn hộ ---",
        f"Giá căn hộ: {fmt(property_price)} VND",
        f"Trả trước ({down_payment_percent}%): {fmt(down_payment)} VND",
        f"Số tiền vay: {fmt(loan_amount)} VND",
        f"",
        f"--- Điều kiện vay ---",
        f"Thời hạn: {loan_term_years} năm ({total_months} tháng)",
        f"Lãi suất: {annual_interest_rate}%/năm",
        f"",
        f"--- Kết quả ---",
        f"Trả hàng tháng: {fmt(monthly_payment)} VND/tháng",
        f"Tổng tiền phải trả: {fmt(total_payment)} VND",
        f"Tổng lãi phải trả: {fmt(total_interest)} VND",
        f"Tỷ lệ lãi/gốc: {total_interest / loan_amount * 100:.1f}%",
        f"",
        f"--- Lịch trả nợ (3 năm đầu) ---",
    ]
    output.extend(schedule_lines)
    
    if loan_term_years > 3:
        output.append(f"  ...")
        # Calculate final year
        balance_final = loan_amount
        for year in range(1, loan_term_years + 1):
            interest_year = 0
            principal_year = 0
            for m in range(12):
                interest_month = balance_final * monthly_rate
                principal_month = monthly_payment - interest_month
                interest_year += interest_month
                principal_year += principal_month
                balance_final -= principal_month
            if year == loan_term_years:
                output.append(
                    f"  Năm {year}: Gốc {fmt(principal_year)} | Lãi {fmt(interest_year)} | Dư nợ {fmt(max(0, balance_final))}"
                )
    
    output.extend([
        f"",
        f"Lưu ý: Lãi suất thực tế có thể thay đổi theo chính sách ngân hàng.",
        f"Lãi suất ưu đãi thường áp dụng 1-3 năm đầu (6-7%/năm),",
        f"sau đó chuyển sang lãi suất thả nổi (8-12%/năm).",
    ])
    
    return "\n".join(output)


# --- Tool Registry ---
TOOLS = [
    {
        "name": "calculate_mortgage",
        "description": (
            "Tính toán khoản vay mua nhà trả góp. "
            "Tham số: property_price (giá căn hộ bằng VND, ví dụ 5000000000 cho căn 5 tỷ), "
            "down_payment_percent (phần trăm trả trước, mặc định 30%), "
            "loan_term_years (thời hạn vay bằng năm, mặc định 20), "
            "annual_interest_rate (lãi suất năm %, mặc định 8.0). "
            "Sử dụng khi khách hàng hỏi về trả góp, vay ngân hàng, tính tiền hàng tháng."
        ),
        "function": calculate_mortgage,
    },
]
