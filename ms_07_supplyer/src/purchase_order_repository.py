
import uuid
import json
from ms_07_supplyer.src.database import get_connection


def process_po_requested(event):
    """
    Memproses event po.requested dari Warehouse
    dan membuat Purchase Order secara otomatis.
    """

    # 1. Mengambil data event
    event_id = event["event_id"]
    event_type = event["event_type"]
    payload = event["payload"]

    # 2. Memastikan jenis event benar
    if event_type != "po.requested":
        raise ValueError("Jenis event tidak didukung")

    # 3. Memastikan data utama tersedia
    required_fields = [
        "purchase_request_id",
        "supplier_id",
        "items"
    ]

    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Data {field} tidak ditemukan")

    purchase_request_id = payload["purchase_request_id"]
    supplier_id = payload["supplier_id"]
    items = payload["items"]

    # 4. Memastikan daftar barang benar
    if not isinstance(items, list) or not items:
        raise ValueError("Items harus berupa daftar dan tidak boleh kosong")

    # 5. Memvalidasi setiap barang
    for item in items:

        if not isinstance(item, dict):
            raise ValueError("Setiap item harus berupa objek")

        required_item_fields = [
            "warehouse_id",
            "product_id",
            "quantity"
        ]

        for field in required_item_fields:
            if field not in item:
                raise ValueError(f"Data {field} tidak ditemukan")

        if (
            not isinstance(item["quantity"], int)
            or isinstance(item["quantity"], bool)
            or item["quantity"] <= 0
        ):
            raise ValueError("Quantity harus berupa bilangan bulat positif")

    # 6. Memastikan semua barang berasal dari warehouse yang sama
    warehouse_id = items[0]["warehouse_id"]

    for item in items:
        if item["warehouse_id"] != warehouse_id:
            raise ValueError(
                "Semua item harus berasal dari warehouse yang sama"
            )

    # 7. Menghubungkan ke database
    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # 8. Memeriksa apakah event sudah pernah diproses
            cursor.execute(
                """
                SELECT id
                FROM processed_events
                WHERE event_id = %s
                """,
                (event_id,)
            )

            existing_event = cursor.fetchone()

            if existing_event:
                return {
                    "message": "Event sudah pernah diproses",
                    "event_id": event_id
                }

            # 9. Membuat identitas Purchase Order
            po_id = str(uuid.uuid4())
            po_number = f"PO-{uuid.uuid4().hex[:8].upper()}"

            order_items = []
            total = 0

            # 10. Mengambil harga setiap barang dari katalog Supplier
            for item in items:

                commodity_id = item["product_id"]
                quantity = item["quantity"]

                cursor.execute(
                    """
                    SELECT price
                    FROM supplier_products
                    WHERE supplier_id = %s
                    AND commodity_id = %s
                    """,
                    (supplier_id, commodity_id)
                )

                product = cursor.fetchone()

                if not product:
                    raise ValueError(
                        f"Produk {commodity_id} tidak ditemukan "
                        "dalam katalog Supplier"
                    )

                unit_price = product["price"]
                subtotal = unit_price * quantity

                total += subtotal

                order_items.append({
                    "commodity_id": commodity_id,
                    "quantity": quantity,
                    "unit_price": unit_price
                })

            # 11. Menyimpan data utama Purchase Order
            cursor.execute(
                """
                INSERT INTO purchase_orders (
                    id,
                    po_number,
                    supplier_id,
                    warehouse_id,
                    purchase_request_id,
                    status,
                    total
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    po_id,
                    po_number,
                    supplier_id,
                    warehouse_id,
                    purchase_request_id,
                    "CREATED",
                    total
                )
            )

            # 12. Menyimpan detail barang Purchase Order
            for item in order_items:

                cursor.execute(
                    """
                    INSERT INTO purchase_order_items (
                        id,
                        purchase_order_id,
                        commodity_id,
                        quantity,
                        unit_price
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()),
                        po_id,
                        item["commodity_id"],
                        item["quantity"],
                        item["unit_price"]
                    )
                )

            # 13. Mencatat event yang sudah diproses
            cursor.execute(
                """
                INSERT INTO processed_events (
                    id,
                    event_id,
                    event_type
                )
                VALUES (%s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    event_id,
                    event_type
                )
            )

        # 14. Menyimpan seluruh perubahan database
        conn.commit()

        return {
            "message": "Purchase Order berhasil dibuat",
            "purchase_order_id": po_id,
            "po_number": po_number,
            "supplier_id": supplier_id,
            "purchase_request_id": purchase_request_id,
            "status": "CREATED",
            "total": str(total)
        }

    except Exception:
        # Membatalkan seluruh perubahan jika terjadi kesalahan
        conn.rollback()
        raise

    finally:
        conn.close()


def confirm_purchase_order(po_id):
    """
    Mengonfirmasi Purchase Order yang masih berstatus CREATED.
    Perubahan status dan pencatatan event dilakukan dalam satu transaksi.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # 1. Mencari PO dan mengunci baris selama transaksi
            cursor.execute(
                """
                SELECT
                    id,
                    po_number,
                    supplier_id,
                    purchase_request_id,
                    status
                FROM purchase_orders
                WHERE id = %s
                FOR UPDATE
                """,
                (po_id,)
            )

            po = cursor.fetchone()

            # 2. Memastikan PO ditemukan
            if not po:
                raise ValueError("Purchase Order tidak ditemukan")

            # 3. Memastikan status masih CREATED
            if po["status"] != "CREATED":
                raise ValueError(
                    f"PO tidak dapat dikonfirmasi karena status saat ini "
                    f"{po['status']}"
                )

            # 4. Mengubah status menjadi CONFIRMED
            cursor.execute(
                """
                UPDATE purchase_orders
                SET status = %s
                WHERE id = %s
                """,
                ("CONFIRMED", po_id)
            )

            # 5. Menyiapkan payload event
            payload = {
                "po_id": po["id"],
                "po_number": po["po_number"],
                "purchase_request_id": po["purchase_request_id"],
                "supplier_id": po["supplier_id"],
                "status": "CONFIRMED"
            }

            # 6. Menyimpan event ke outbox
            cursor.execute(
                """
                INSERT INTO outbox_events (
                    id,
                    aggregate_type,
                    aggregate_id,
                    event_type,
                    payload
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    "purchase_order",
                    po_id,
                    "po.confirmed",
                    json.dumps(payload)
                )
            )

        # 7. Menyimpan perubahan database
        conn.commit()

        return {
            "message": "Purchase Order berhasil dikonfirmasi",
            "purchase_order_id": po_id,
            "po_number": po["po_number"],
            "status": "CONFIRMED"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def ship_purchase_order(po_id):
    """
    Mengubah status Purchase Order dari CONFIRMED menjadi SHIPPED.
    Perubahan status dan pencatatan event dilakukan dalam satu transaksi.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # 1. Mencari PO dan mengunci baris selama transaksi
            cursor.execute(
                """
                SELECT
                    id,
                    po_number,
                    supplier_id,
                    purchase_request_id,
                    status
                FROM purchase_orders
                WHERE id = %s
                FOR UPDATE
                """,
                (po_id,)
            )

            po = cursor.fetchone()

            # 2. Memastikan PO ditemukan
            if not po:
                raise ValueError("Purchase Order tidak ditemukan")

            # 3. Memastikan status PO adalah CONFIRMED
            if po["status"] != "CONFIRMED":
                raise ValueError(
                    f"PO tidak dapat dikirim karena status saat ini "
                    f"{po['status']}"
                )

            # 4. Mengubah status menjadi SHIPPED
            cursor.execute(
                """
                UPDATE purchase_orders
                SET status = %s
                WHERE id = %s
                """,
                ("SHIPPED", po_id)
            )

            # 5. Menyiapkan payload event
            payload = {
                "po_id": po["id"],
                "po_number": po["po_number"],
                "purchase_request_id": po["purchase_request_id"],
                "supplier_id": po["supplier_id"],
                "status": "SHIPPED"
            }

            # 6. Menyimpan event ke outbox
            cursor.execute(
                """
                INSERT INTO outbox_events (
                    id,
                    aggregate_type,
                    aggregate_id,
                    event_type,
                    payload
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    "purchase_order",
                    po_id,
                    "po.shipped",
                    json.dumps(payload)
                )
            )

        # 7. Menyimpan perubahan database
        conn.commit()

        return {
            "message": "Purchase Order berhasil dikirim",
            "purchase_order_id": po_id,
            "po_number": po["po_number"],
            "status": "SHIPPED"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def deliver_purchase_order(po_id):
    """
    Mengubah status Purchase Order dari SHIPPED menjadi DELIVERED.
    Perubahan status dan pencatatan event dilakukan dalam satu transaksi.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # 1. Mencari PO dan mengunci baris selama transaksi
            cursor.execute(
                """
                SELECT
                    id,
                    po_number,
                    supplier_id,
                    purchase_request_id,
                    status
                FROM purchase_orders
                WHERE id = %s
                FOR UPDATE
                """,
                (po_id,)
            )

            po = cursor.fetchone()

            # 2. Memastikan PO ditemukan
            if not po:
                raise ValueError("Purchase Order tidak ditemukan")

            # 3. Memastikan status PO adalah SHIPPED
            if po["status"] != "SHIPPED":
                raise ValueError(
                    f"PO tidak dapat ditandai delivered karena "
                    f"status saat ini {po['status']}"
                )

            # 4. Mengubah status menjadi DELIVERED
            cursor.execute(
                """
                UPDATE purchase_orders
                SET status = %s
                WHERE id = %s
                """,
                ("DELIVERED", po_id)
            )

            # 5. Menyiapkan payload event
            payload = {
                "po_id": po["id"],
                "po_number": po["po_number"],
                "purchase_request_id": po["purchase_request_id"],
                "supplier_id": po["supplier_id"],
                "status": "DELIVERED"
            }

            # 6. Menyimpan event ke outbox
            cursor.execute(
                """
                INSERT INTO outbox_events (
                    id,
                    aggregate_type,
                    aggregate_id,
                    event_type,
                    payload
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    "purchase_order",
                    po_id,
                    "po.delivered",
                    json.dumps(payload)
                )
            )

        # 7. Menyimpan perubahan database
        conn.commit()

        return {
            "message": "Purchase Order berhasil ditandai delivered",
            "purchase_order_id": po_id,
            "po_number": po["po_number"],
            "status": "DELIVERED"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def cancel_purchase_order(po_id):
    """
    Mengubah status Purchase Order dari CREATED menjadi CANCELLED.
    Perubahan status dan pencatatan event dilakukan dalam satu transaksi.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # 1. Mencari PO dan mengunci baris selama transaksi
            cursor.execute(
                """
                SELECT
                    id,
                    po_number,
                    supplier_id,
                    purchase_request_id,
                    status
                FROM purchase_orders
                WHERE id = %s
                FOR UPDATE
                """,
                (po_id,)
            )

            po = cursor.fetchone()

            # 2. Memastikan PO ditemukan
            if not po:
                raise ValueError("Purchase Order tidak ditemukan")

            # 3. Memastikan status PO adalah CREATED
            if po["status"] != "CREATED":
                raise ValueError(
                    f"PO tidak dapat dibatalkan karena "
                    f"status saat ini {po['status']}"
                )

            # 4. Mengubah status menjadi CANCELLED
            cursor.execute(
                """
                UPDATE purchase_orders
                SET status = %s
                WHERE id = %s
                """,
                ("CANCELLED", po_id)
            )

            # 5. Menyiapkan payload event
            payload = {
                "po_id": po["id"],
                "po_number": po["po_number"],
                "purchase_request_id": po["purchase_request_id"],
                "supplier_id": po["supplier_id"],
                "status": "CANCELLED"
            }

            # 6. Menyimpan event ke outbox
            cursor.execute(
                """
                INSERT INTO outbox_events (
                    id,
                    aggregate_type,
                    aggregate_id,
                    event_type,
                    payload
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    "purchase_order",
                    po_id,
                    "po.cancelled",
                    json.dumps(payload)
                )
            )

        # 7. Menyimpan perubahan database
        conn.commit()

        return {
            "message": "Purchase Order berhasil dibatalkan",
            "purchase_order_id": po_id,
            "po_number": po["po_number"],
            "status": "CANCELLED"
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_all_purchase_orders():
    """
    Mengambil seluruh daftar Purchase Order
    beserta nama supplier.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    po.id,
                    po.po_number,
                    po.supplier_id,
                    s.name AS supplier_name,
                    po.warehouse_id,
                    po.purchase_request_id,
                    po.status,
                    po.total,
                    po.created_at
                FROM purchase_orders AS po
                JOIN suppliers AS s
                    ON po.supplier_id = s.id
                ORDER BY po.created_at DESC
                """
            )

            purchase_orders = cursor.fetchall()

        return purchase_orders

    finally:
        conn.close()


def get_purchase_order_by_id(po_id):
    """
    Mengambil detail satu Purchase Order berdasarkan ID,
    termasuk informasi supplier dan daftar barang.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # 1. Mengambil informasi utama Purchase Order
            cursor.execute(
                """
                SELECT
                    po.id,
                    po.po_number,
                    po.supplier_id,
                    s.name AS supplier_name,
                    po.warehouse_id,
                    po.purchase_request_id,
                    po.status,
                    po.total,
                    po.created_at
                FROM purchase_orders AS po
                JOIN suppliers AS s
                    ON po.supplier_id = s.id
                WHERE po.id = %s
                """,
                (po_id,)
            )

            purchase_order = cursor.fetchone()

            # 2. Memastikan Purchase Order ditemukan
            if not purchase_order:
                return None

            # 3. Mengambil daftar barang dalam Purchase Order
            cursor.execute(
                """
                SELECT
                    id,
                    commodity_id,
                    quantity,
                    unit_price
                FROM purchase_order_items
                WHERE purchase_order_id = %s
                """,
                (po_id,)
            )

            items = cursor.fetchall()

            # 4. Menggabungkan informasi PO dan daftar barang
            purchase_order["items"] = items

        return purchase_order

    finally:
        conn.close()
