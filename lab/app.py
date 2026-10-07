"""A deliberately thin synthetic write boundary, not a PostgreSQL driver."""
SQL = 'INSERT INTO order_line (quantity) VALUES (%s) RETURNING id'

def add_line(cursor, quantity):
    cursor.execute(SQL, (quantity,))
    return cursor.fetchone()[0]
