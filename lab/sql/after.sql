CREATE TEMP TABLE order_line (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quantity integer NOT NULL CHECK (quantity > 0)
);
