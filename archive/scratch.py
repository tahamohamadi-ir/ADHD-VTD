import sqlglot
from sqlglot import exp

sql = "SELECT * FROM a JOIN b ON a.id = b.id"
tree = sqlglot.parse_one(sql, read="sqlite")
for select in tree.find_all(exp.Select):
    print("Select args keys:", list(select.args.keys()))
    from_node = select.args.get("from")
    if from_node:
        print("from_node type:", type(from_node))
        print("from_node this type:", type(from_node.this))
