from .. import db, models, schemas
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status
import json

def filter_products(products: List[schemas.ProductSearchOut],
                    categories: Optional[List[str]] = None,
                    dict: Optional[dict] = None
                    ) -> List[schemas.ProductSearchOut]:
    """
    All filtering logic for products.
    """

    results = []
    for product in products:
        if any(cat not in product.categories for cat in categories or []):
            continue

        description = product.description or ""
        description = json.dumps(description.lower())

        flag: bool = True

        for key, value in (dict or {}).items():
            if key.endswith("_low") and key[:-4] in product.model_dump():
                if product.model_dump()[key[:-4]] < value:
                    flag = False
                    break
            elif key.endswith("_high") and key[:-5] in product.model_dump():
                if product.model_dump()[key[:-5]] > value:
                    flag = False
                    break
            elif key.endswith("_exact") and key[:-7] in product.model_dump():
                if product.model_dump()[key[:-7]] != value:
                    flag = False
                    break
            elif key.endswith("_low") and key[:-4] in description.keys():
                if description[key[:-4]] < value:
                    flag = False
                    break
            elif key.endswith("_high") and key[:-5] in description.keys():
                if description[key[:-5]] > value:
                    flag = False
                    break
            elif key.endswith("_exact") and key[:-7] in description.keys():
                if description[key[:-7]] != value:
                    flag = False
                    break
            elif key.endswith("_contains") and key[:-9] in description.keys():
                if value not in description[key[:-9]]:
                    flag = False
                    break

        if flag:
            results.append(product)
    return results
                