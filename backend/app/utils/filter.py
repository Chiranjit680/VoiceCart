from .. import database, models, schemas
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status
import json

# TODO fix it: none of the features work
def filter_products(products: List[schemas.ProductSearchOut],
                    categories: Optional[List[str]] = None,
                    dict: Optional[dict] = None
                    ) -> List[schemas.ProductSearchOut]:
    """
    All filtering logic for products.
    """

    results = []
    for product in products:

        flag: bool = True

        for cat in categories or []:
            if cat not in [category.name for category in product.categories]:
                flag = False
                break

        description = product.specs or ""
        # if isinstance(description, str):
        #     try:
        #         description = json.loads(description.lower())
        #     except Exception:
        #         description = {}
        # elif not isinstance(description, dict):
        #     description = {}

        for key, value in (dict or {}).items():
            print(f"Checking {key} with value {value} for product {product.name}")
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
            elif key.endswith("_contains") and key[:-9] in product.model_dump():
                if value not in product.model_dump()[key[:-9]]:
                    flag = False
                    break

            elif key.endswith("_low") and key[:-4] in description.keys():
                if float(description[key[:-4]]) < value:
                    flag = False
                    break
            elif key.endswith("_high") and key[:-5] in description.keys():
                if float(description[key[:-5]]) > value:
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
                