import re

def clean_name(raw_name: str):
    """'핑거루트추출분말(기능성원료인정제2012-36호)' -> '핑거루트추출분말'"""
    if not raw_name:
        return ""

    return re.sub(r"\(.*?\)", "", raw_name).strip()

def format_korean_number(num: int) -> str:
    """
    30000 → 3만
    250000000 → 2억 5000만
    2100000000 → 21억
    """
    if num < 10000:
        return str(num)

    result = []

    # 억 단위
    if num >= 100000000:
        eok = num // 100000000
        result.append(f"{eok}억")
        num = num % 100000000

    # 만 단위
    if num >= 10000:
        man = num // 10000
        result.append(f"{man}만")
        num = num % 10000

    # 나머지
    if num > 0:
        result.append(str(num))

    return " ".join(result)

def clean_amount(value: str) -> str | None:
    """
    식약처 API 권장량 문자열 정제 + 한국식 숫자 변환
    예:
        "2,400 (mg)" → "2400mg"
        "1g/일" → "1g"
        "1,000 (IU)" → "1000IU"
        "400㎍" → "400ug"
        "30000mg" → "3만mg"
        "250000000IU" → "2억 5000만IU"
    """

    if not value or value.strip() == "":
        return None

    v = value.strip()

    # 1) 콤마 제거
    v = v.replace(",", "")

    # 2) 괄호 제거: 250 (mg) → 250mg
    v = v.replace("(", "").replace(")", "")

    # 3) "/일" "/1일" "/day" 패턴 제거
    v = re.sub(r"/\s*일", "", v)
    v = re.sub(r"/\s*1일", "", v)
    v = re.sub(r"/\s*day", "", v, flags=re.IGNORECASE)

    # 4) 한글 단위 정리: ㎍ → ug
    v = v.replace("㎍", "ug")

    # 5) 공백 제거
    v = v.strip()

    # 6) 숫자가 하나도 없으면 None
    if not re.search(r"\d", v):
        return None

    # 7) 숫자 + 단위 분리
    match = re.match(r"(\d+)(.*)", v)
    if not match:
        return None  # 예외적으로 매칭 안 되면 None 반환

    num = int(match.group(1))
    unit = match.group(2).strip()  # mg, g, IU 등 단위

    # 8) 한국식 단위 변환
    formatted_num = format_korean_number(num)

    # 단위가 있으면 붙여서 반환
    return f"{formatted_num}{unit}" if unit else formatted_num

def clean_text(value: str):
    """
    (1)(2) 숫자 라벨은 줄바꿈으로 변환,
    (국문)(영문)(기타기능) 등 라벨 제거,
    영어 문장 제거.
    """
    if not value:
        return ""

    v = value.strip()

    # 1) (국문), (영문), (기타기능), (생리활성기능 등급) 제거
    v = re.sub(r"\((국문|영문|기타기능|생리활성기능.*?|.*?등급.*?)\)", "", v)

    # 2) 영어 문장 제거 (영문이 포함된 전체 문장 제거)
    v = re.sub(r"[A-Za-z].*", "", v)

    # 3) (1), (2) 스타일 → 줄바꿈
    v = re.sub(r"\(\s*\d+\s*\)", "\n", v)

    # 4) ①②③ → 줄바꿈
    v = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]", "\n", v)

    # 5) 여러 줄바꿈 → 하나의 줄바꿈
    v = re.sub(r"\n+", "\n", v)

    # 6) 문장 단위 리스트로 분리
    parts = [p.strip() for p in v.split("\n") if p.strip()]

    return parts