CREATE TEMP TABLE order_line (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quantity integer CHECK (quantity > 0)
);
