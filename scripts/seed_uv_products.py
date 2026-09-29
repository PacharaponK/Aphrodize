"""Add two source-reviewed sunscreen examples to an empty or existing catalog."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from backend.api.v1.routes.products import require_publishable
from backend.core.db.models import Product
from backend.core.db.session import SessionLocal

PRODUCTS = [
    {
        "name": "AM Facial Moisturising Lotion SPF 50",
        "spf": 50,
        "target_skin_types": ["normal", "dry"],
        "source_url": "https://www.cerave.co.th/skincare/facial-moisturising-lotion-spf-50",
        "ingredients_label": (
            "AQUA/WATER, GLYCERIN, ISOPROPYL PALMITATE, BIS-ETHYLHEXYLOXYPHENOL "
            "METHOXYPHENYL TRIAZINE, ETHYLHEXYL SALICYLATE, NIACINAMIDE, PENTYLENE "
            "GLYCOL, BUTYL METHOXYDIBENZOYLMETHANE, ETHYLHEXYL TRIAZONE, PROPANEDIOL, "
            "ZEA MAYS STARCH/CORN STARCH, POTASSIUM CETYL PHOSPHATE, DIISOPROPYL "
            "SEBACATE, ORYZA SATIVA CERA/RICE BRAN WAX, STEARIC ACID, CERAMIDE NP, "
            "CERAMIDE AP, CERAMIDE EOP, CARBOMER, GLYCERYL STEARATE, CETEARYL ALCOHOL, "
            "TRIETHANOLAMINE, BEHENTRIMONIUM METHOSULFATE, TRIETHYL CITRATE, SODIUM "
            "HYALURONATE, SODIUM POLYACRYLATE, SODIUM LAUROYL LACTYLATE, MYRISTIC ACID, "
            "CHOLESTEROL, PALMITIC ACID, TOCOPHEROL, CAPRYLYL GLYCOL, TRISODIUM "
            "ETHYLENEDIAMINE DISUCCINATE, XANTHAN GUM, PHYTOSPHINGOSINE, ACRYLATES/C10-30 "
            "ALKYL ACRYLATE CROSSPOLYMER, BUTYROSPERMUM PARKII BUTTER/SHEA BUTTER, "
            "BENZOIC ACID, PEG-100 STEARATE"
        ),
    },
    {
        "name": "AM Facial Moisturising Lotion SPF 30",
        "spf": 30,
        "target_skin_types": ["all"],
        "source_url": "https://www.cerave.co.th/skincare/facial-moisturising-lotion-spf-30",
        "ingredients_label": (
            "Active: Homosalate 10%, Meradimate 5%, Octinoxate 5%, Octocrylene 2%, "
            "Zinc Oxide 6.3%. Inactive: Water, Niacinamide, Glycerin, Cetearyl Alcohol, "
            "Behentrimonium Methosulfate, Dimethicone, BHT, Ceramide NP, Ceramide AP, "
            "Ceramide EOP, Carbomer, Triethoxycaprylylsilane, Methylparaben, Sodium "
            "Lauroyl Lactylate, Cholesterol, Aluminum Starch Octenylsuccinate, Disodium "
            "EDTA, Propylparaben, Hydroxyethylcellulose, Hydrolyzed Hyaluronic Acid, "
            "Phytosphingosine, Xanthan Gum"
        ),
    },
]


async def main():
    async with SessionLocal() as session:
        for specification in PRODUCTS:
            if await session.scalar(
                select(Product.id).where(Product.source_url == specification["source_url"])
            ):
                continue
            ingredients = (
                specification["ingredients_label"].replace("Active: ", "").replace("Inactive: ", "")
            )
            product = Product(
                brand="CeraVe",
                category="sunscreen",
                variant="สำหรับผิวหน้า",
                price_satang=None,
                ingredients_inci=[part.strip() for part in ingredients.split(",")],
                warnings_label="ตรวจฉลากบนบรรจุภัณฑ์ก่อนใช้; สูตรอาจเปลี่ยนแปลง",
                concerns=[],
                broad_spectrum=True,
                water_resistant_minutes=None,
                status="published",
                reviewed_at=datetime.now(UTC),
                **specification,
            )
            require_publishable(product)
            session.add(product)
            print(f"Added reviewed product: {product.name}")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
