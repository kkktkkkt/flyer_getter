"""
Analyzes flyer images using Claude Vision to extract product names and prices.
"""

import base64
import json
from dataclasses import dataclass

import anthropic

SYSTEM_PROMPT = """あなたはスーパーのチラシ画像から商品情報を正確に抽出する専門家です。
チラシ画像を解析し、全ての商品名と価格を抽出してください。"""

EXTRACT_PROMPT = """このスーパーのチラシ画像から、全ての商品名と価格を抽出してください。

以下のJSON形式で返してください（他のテキストは不要）:
{
  "products": [
    {"name": "商品名", "price": 価格の数値, "unit": "単位（例：円、税抜、税込など）", "note": "備考（特売、限定など）"},
    ...
  ]
}

注意事項:
- 価格は数値のみ（¥や円記号は除く）
- 判読できない場合はnullを使用
- 全ての商品を漏れなく抽出
- 同じ商品が複数ある場合はまとめずに全て列挙"""


@dataclass
class Product:
    name: str
    price: float | None
    unit: str
    note: str
    page: int


def analyze_flyer_image(image_bytes: bytes, page_num: int, client: anthropic.Anthropic) -> list[Product]:
    """Send flyer image to Claude and extract product/price data."""
    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": EXTRACT_PROMPT},
                ],
            }
        ],
    )

    text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    data = json.loads(text)
    products = []
    for item in data.get("products", []):
        products.append(
            Product(
                name=item.get("name", ""),
                price=item.get("price"),
                unit=item.get("unit", "円"),
                note=item.get("note", ""),
                page=page_num,
            )
        )
    return products


def analyze_all_pages(image_bytes_list: list[bytes], api_key: str | None = None) -> list[Product]:
    """Analyze multiple flyer pages and return all products."""
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    all_products = []
    for i, image_bytes in enumerate(image_bytes_list, start=1):
        print(f"  ページ {i}/{len(image_bytes_list)} を解析中...")
        products = analyze_flyer_image(image_bytes, page_num=i, client=client)
        all_products.extend(products)
    return all_products
