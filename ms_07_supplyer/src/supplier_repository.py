
import uuid

from ms_07_supplyer.src.database import get_connection


def get_all_suppliers():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT
                    id,
                    code,
                    name,
                    contact,
                    address,
                    is_active
                FROM suppliers
                ORDER BY name ASC
            """

            cursor.execute(query)
            suppliers = cursor.fetchall()

        return suppliers

    finally:
        conn.close()


def get_supplier_by_id(supplier_id):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT
                    id,
                    code,
                    name,
                    contact,
                    address,
                    is_active
                FROM suppliers
                WHERE id = %s
            """

            cursor.execute(query, (supplier_id,))
            supplier = cursor.fetchone()

        return supplier

    finally:
        conn.close()


def create_supplier(code, name, contact, address):
    conn = get_connection()

    try:
        supplier_id = str(uuid.uuid4())

        with conn.cursor() as cursor:
            query = """
                INSERT INTO suppliers (
                    id,
                    code,
                    name,
                    contact,
                    address,
                    is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                query,
                (supplier_id, code, name, contact, address, 1)
            )

        conn.commit()

        return {
            "id": supplier_id,
            "code": code,
            "name": name,
            "contact": contact,
            "address": address,
            "is_active": 1
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def update_supplier(supplier_id, code, name, contact, address):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            query = """
                UPDATE suppliers
                SET
                    code = %s,
                    name = %s,
                    contact = %s,
                    address = %s
                WHERE id = %s
            """

            cursor.execute(
                query,
                (code, name, contact, address, supplier_id)
            )

        conn.commit()

        if cursor.rowcount == 0:
            return None

        return {
            "id": supplier_id,
            "code": code,
            "name": name,
            "contact": contact,
            "address": address
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def delete_supplier(supplier_id):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            query = """
                UPDATE suppliers
                SET is_active = 0
                WHERE id = %s
            """

            cursor.execute(query, (supplier_id,))

        conn.commit()

        return cursor.rowcount > 0

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_all_supplier_products(commodity_id=None):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            query = """
                SELECT
                    id,
                    supplier_id,
                    commodity_id,
                    price,
                    lead_time_days
                FROM supplier_products
            """

            if commodity_id:
                query += " WHERE commodity_id = %s"
                query += " ORDER BY supplier_id ASC"
                cursor.execute(query, (commodity_id,))
            else:
                query += " ORDER BY supplier_id ASC"
                cursor.execute(query)

            products = cursor.fetchall()

        return products

    finally:
        conn.close()


def create_supplier_product(
    supplier_id,
    commodity_id,
    price,
    lead_time_days
):
    conn = get_connection()

    try:
        product_id = str(uuid.uuid4())

        with conn.cursor() as cursor:
            query = """
                INSERT INTO supplier_products (
                    id,
                    supplier_id,
                    commodity_id,
                    price,
                    lead_time_days
                )
                VALUES (%s, %s, %s, %s, %s)
            """

            cursor.execute(
                query,
                (
                    product_id,
                    supplier_id,
                    commodity_id,
                    price,
                    lead_time_days
                )
            )

        conn.commit()

        return {
            "id": product_id,
            "supplier_id": supplier_id,
            "commodity_id": commodity_id,
            "price": price,
            "lead_time_days": lead_time_days
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

