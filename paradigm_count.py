
import ast

FILES = ["generate_data.py", "weather_mis.py"]


def count_file(path):
    with open(path, encoding="utf-8") as file:
        tree = ast.parse(file.read())
    functions = []
    classes = []
    methods = []
    handlers = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(node.name + "." + item.name)
                    if item.name.startswith("on_"):
                        handlers.append(node.name + "." + item.name)
    return functions, classes, methods, handlers


def main():
    total = [0, 0, 0, 0]
    for path in FILES:
        functions, classes, methods, handlers = count_file(path)
        print(path)
        print(f"  procedural functions : {len(functions)}")
        print(f"  classes              : {len(classes)}")
        for name in classes:
            own = [m.split(".")[1] for m in methods if m.startswith(name + ".")]
            print(f"      {name}: {', '.join(own)}")
        print(f"  event handlers       : {len(handlers)} {handlers}")
        for index, group in enumerate((functions, classes, methods, handlers)):
            total[index] = total[index] + len(group)
    print(f"TOTAL: {total[0]} functions, {total[1]} classes, {total[2]} methods,"
          f" {total[3]} event handler(s)")


if __name__ == "__main__":
    main()
