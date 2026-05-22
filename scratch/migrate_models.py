import os

# 1. Create files for Domains
domains = ["hardware", "cabling", "power"]
for d in domains:
    os.makedirs(f"app/domains/{d}", exist_ok=True)
    open(f"app/domains/{d}/__init__.py", "w").close()


# 2. Combine models into domain/models.py
def combine_files(files, target):
    content = ""
    imports = set()
    code = []

    for f in files:
        if not os.path.exists(f):
            continue
        with open(f, "r") as fp:
            lines = fp.readlines()

        for line in lines:
            if line.startswith("import ") or line.startswith("from "):
                # Skip internal model imports, we'll fix them later
                if "app.models" not in line and "app.domains" not in line:
                    imports.add(line.strip())
            else:
                code.append(line)

    with open(target, "w") as fw:
        for imp in sorted(imports):
            fw.write(imp + "\n")
        fw.write("from app.core.database import Base\n")
        fw.write("from typing import TYPE_CHECKING\n\n")

        # Add TYPE_CHECKING blocks for cross-domain relationships
        fw.write("if TYPE_CHECKING:\n")
        if "hardware" in target:
            fw.write("    from app.domains.power.models import UsvUnit\n")
            fw.write("    from app.domains.cabling.models import Cable, Interface\n")
        elif "cabling" in target:
            fw.write("    from app.domains.hardware.models import Device\n")
        elif "power" in target:
            fw.write("    from app.domains.hardware.models import Rack\n")
        fw.write("\n")

        fw.write("".join(code))


combine_files(
    ["app/models/rack.py", "app/models/device.py"], "app/domains/hardware/models.py"
)
combine_files(
    ["app/models/cable.py", "app/models/interface.py"], "app/domains/cabling/models.py"
)
combine_files(["app/models/usv.py"], "app/domains/power/models.py")
