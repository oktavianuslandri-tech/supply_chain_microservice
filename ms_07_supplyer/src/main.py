from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ms_07_supplyer.src.supplier_repository import (
    get_all_suppliers,
    get_supplier_by_id,
    create_supplier,
    update_supplier,
    delete_supplier,
    get_all_supplier_products,
    create_supplier_product
)

from ms_07_supplyer.src.purchase_order_repository import (
    get_all_purchase_orders,
    get_purchase_order_by_id,
    confirm_purchase_order,
    ship_purchase_order,
    deliver_purchase_order,
    cancel_purchase_order
)

app = FastAPI(title="Supplier Service")


class SupplierCreate(BaseModel):
    code: str
    name: str
    contact: str | None = None
    address: str | None = None


class SupplierProductCreate(BaseModel):
    supplier_id: str
    commodity_id: str
    price: float = Field(gt=0)
    lead_time_days: int = Field(ge=0)


@app.get("/health")
def health_check():
    return {
        "status": "success",
        "service": "Supplier Service",
        "message": "Supplier Service berjalan dengan baik"
    }

@app.get("/suppliers")
def read_suppliers():
    suppliers = get_all_suppliers()

    return {
        "status": "success",
        "data": suppliers
    }

@app.get("/suppliers/{supplier_id}")
def read_supplier_detail(supplier_id: str):
    supplier = get_supplier_by_id(supplier_id)

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail="Supplier tidak ditemukan"
        )

    return {
        "status": "success",
        "data": supplier
    }

@app.post("/suppliers", status_code=201)
def add_supplier(supplier: SupplierCreate):
    try:
        new_supplier = create_supplier(
            supplier.code,
            supplier.name,
            supplier.contact,
            supplier.address
        )

        return {
            "status": "success",
            "message": "Supplier berhasil ditambahkan",
            "data": new_supplier
        }

    except Exception as e:
        if "Duplicate entry" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Kode supplier sudah digunakan"
            )

        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )


@app.put("/suppliers/{supplier_id}")
def edit_supplier(supplier_id: str, supplier: SupplierCreate):
    try:
        updated_supplier = update_supplier(
            supplier_id,
            supplier.code,
            supplier.name,
            supplier.contact,
            supplier.address
        )

        if updated_supplier is None:
            raise HTTPException(
                status_code=404,
                detail="Supplier tidak ditemukan"
            )

        return {
            "status": "success",
            "message": "Supplier berhasil diperbarui",
            "data": updated_supplier
        }

    except HTTPException:
        raise

    except Exception as e:
        if "Duplicate entry" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Kode supplier sudah digunakan"
            )

        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )


@app.delete("/suppliers/{supplier_id}")
def remove_supplier(supplier_id: str):
    try:
        deleted = delete_supplier(supplier_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Supplier tidak ditemukan"
            )

        return {
            "status": "success",
            "message": "Supplier berhasil dinonaktifkan"
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )

@app.get("/supplier-products")
def read_supplier_products(commodity_id: str = None):
    products = get_all_supplier_products(commodity_id)

    return {
        "status": "success",
        "data": products
    }

@app.post("/supplier-products", status_code=201)
def add_supplier_product(product: SupplierProductCreate):
    try:
        new_product = create_supplier_product(
            product.supplier_id,
            product.commodity_id,
            product.price,
            product.lead_time_days
        )

        return {
            "status": "success",
            "message": "Produk supplier berhasil ditambahkan",
            "data": new_product
        }

    except Exception as e:
        if "Duplicate entry" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Komoditas sudah terdaftar pada supplier ini"
            )

        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )
@app.post("/purchase-orders/{po_id}/confirm")
def confirm_po(po_id: str):
    try:
        result = confirm_purchase_order(po_id)

        return {
            "status": "success",
            "message": result["message"],
            "data": result
        }

    except ValueError as e:
        if "tidak ditemukan" in str(e):
            raise HTTPException(
                status_code=404,
                detail=str(e)
            )

        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )
@app.patch("/purchase-orders/{po_id}/ship")
def ship_po(po_id: str):
    try:
        result = ship_purchase_order(po_id)

        return {
            "status": "success",
            "message": result["message"],
            "data": result
        }

    except ValueError as e:
        if "tidak ditemukan" in str(e):
            raise HTTPException(status_code=404, detail=str(e))

        raise HTTPException(status_code=409, detail=str(e))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )

@app.patch("/purchase-orders/{po_id}/deliver")
def deliver_po(po_id: str):
    try:
        result = deliver_purchase_order(po_id)

        return {
            "status": "success",
            "message": result["message"],
            "data": result
        }

    except ValueError as e:
        if "tidak ditemukan" in str(e):
            raise HTTPException(status_code=404, detail=str(e))

        raise HTTPException(status_code=409, detail=str(e))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )


@app.post("/purchase-orders/{po_id}/cancel")
def cancel_po(po_id: str):
    try:
        result = cancel_purchase_order(po_id)

        return {
            "status": "success",
            "message": result["message"],
            "data": result
        }

    except ValueError as e:
        if "tidak ditemukan" in str(e):
            raise HTTPException(status_code=404, detail=str(e))

        raise HTTPException(status_code=409, detail=str(e))

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )

@app.get("/purchase-orders")
def list_purchase_orders():
    try:
        result = get_all_purchase_orders()

        return {
            "status": "success",
            "data": result
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )
@app.get("/purchase-orders/{po_id}")
def get_purchase_order_detail(po_id: str):
    try:
        result = get_purchase_order_by_id(po_id)

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Purchase Order tidak ditemukan"
            )

        return {
            "status": "success",
            "data": result
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan pada database"
        )